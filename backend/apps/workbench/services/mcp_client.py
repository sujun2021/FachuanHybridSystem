"""工作台 MCP 客户端 - 连接本地 MCP Server"""

from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator
from typing import Any

from mcp import ClientSession, types
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)

# MCP Server 入口 - 使用项目根目录下的 mcp_server 模块
_BACKEND_DIR = str(Path(__file__).resolve().parents[3])


class WorkbenchMCPClient:
    """工作台 MCP 客户端 - 通过 stdio 连接本地 MCP Server"""

    def __init__(self, python_path: str | None = None) -> None:
        self._python_path = python_path or sys.executable
        self._tools_cache: list[dict[str, Any]] | None = None

    @asynccontextmanager
    async def _open_session(self) -> AsyncIterator[ClientSession]:
        """打开 MCP 会话（stdio 传输）"""
        server_params = StdioServerParameters(
            command=self._python_path,
            args=["-m", "mcp_server"],
            cwd=_BACKEND_DIR,
        )
        async with stdio_client(server_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session

    async def list_tools(self) -> list[dict[str, Any]]:
        """获取 MCP 服务器提供的工具列表（OpenAI function-calling 格式）"""
        if self._tools_cache is not None:
            return self._tools_cache

        async with self._open_session() as session:
            result = await session.list_tools()

        tools: list[dict[str, Any]] = []
        for item in result.tools:
            name = str(getattr(item, "name", "") or "").strip()
            if not name:
                continue
            description = str(getattr(item, "description", "") or "").strip()
            input_schema = getattr(item, "inputSchema", None)
            if input_schema is None:
                input_schema = getattr(item, "input_schema", None)
            if not isinstance(input_schema, dict):
                input_schema = {"type": "object", "properties": {}}

            # 转换为 OpenAI function-calling 格式
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": description,
                        "parameters": input_schema,
                    },
                }
            )

        self._tools_cache = tools
        logger.info("从 MCP Server 获取到 %d 个工具", len(tools))
        return tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """调用 MCP 工具"""
        async with self._open_session() as session:
            result = await session.call_tool(name=tool_name, arguments=arguments)

        # 提取结果
        if result.isError:
            error_text = self._extract_text(result.content)
            logger.error("MCP 工具调用失败: %s - %s", tool_name, error_text)
            return {"error": error_text}

        return self._extract_payload(result)

    @staticmethod
    def _extract_text(content: list[Any]) -> str:
        """从 MCP 内容列表提取文本"""
        parts: list[str] = []
        for item in content:
            if getattr(item, "type", None) == "text":
                parts.append(str(getattr(item, "text", "") or ""))
        return "\n".join(parts)

    @staticmethod
    def _extract_payload(result: types.CallToolResult) -> Any:
        """提取 MCP 工具调用结果"""
        if result.structuredContent is not None:
            return result.structuredContent

        parsed_json: list[Any] = []
        plain_text: list[str] = []
        for item in result.content:
            if getattr(item, "type", None) != "text":
                continue
            text = str(getattr(item, "text", "") or "").strip()
            if not text:
                continue
            try:
                parsed_json.append(json.loads(text))
            except (TypeError, ValueError):
                plain_text.append(text)

        if len(parsed_json) == 1:
            return parsed_json[0]
        if parsed_json:
            return parsed_json
        if len(plain_text) == 1:
            return plain_text[0]
        if plain_text:
            return plain_text
        return None

    def clear_cache(self) -> None:
        """清除工具缓存"""
        self._tools_cache = None
