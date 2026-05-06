"""工作台对话编排服务 - LLM + MCP 工具调用

Phase 1: 结构化 Agent Loop (NextStep) + 工具错误自纠正
Phase 2: Human-in-the-Loop 审批门控
Phase 3: 上下文管理 (Token 计数 + 滑动窗口 + 摘要压缩)
Phase 4: 多 Agent 协作 (Handoff 模式 + 工具权限隔离)
"""

from __future__ import annotations

import asyncio
import enum
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import openai

from apps.core.llm.config import LLMConfig

from .mcp_client import WorkbenchMCPClient

logger = logging.getLogger(__name__)

# ─── 常量 ────────────────────────────────────────────────────────────────────

MAX_TOOL_ROUNDS = 10
MAX_CONTEXT_TOKENS = 8000  # 为 tool results 和回复预留空间
SUMMARY_THRESHOLD = 15  # 超过 N 条旧消息时触发摘要压缩

SYSTEM_PROMPT = """你是法穿AI Copilot，一个法律事务助手。你可以通过调用工具来完成各种法律事务操作，包括：
- 案件管理（创建、查询、修改案件）
- 客户管理（创建、查询客户信息）
- 合同管理（查询、下载合同）
- 提醒管理（创建、查询提醒）
- 财务统计
- 法律检索
- 企业信息查询
- 等等

当你需要执行操作或查询信息时，请使用工具调用。请用中文回复。

重要提示：
- 如果工具调用返回错误，请分析错误原因并尝试修正参数重新调用
- 如果多次失败，请告知用户具体原因和建议
- 对于高风险操作（如删除、发送），系统会要求用户确认后再执行"""

# 需要用户审批的高风险工具
HIGH_RISK_TOOLS = frozenset(
    {
        "delete_case",
        "delete_client",
        "delete_contract",
        "send_document",
        "file_lawsuit",
        "submit_court_document",
    }
)


# ─── 枚举 ────────────────────────────────────────────────────────────────────


class NextStep(enum.Enum):
    """Agent Loop 每轮结束后的下一步决策"""

    FINAL_OUTPUT = "final_output"  # LLM 返回最终文本，循环结束
    TOOL_CALL = "tool_call"  # 需要执行工具，继续循环
    ERROR = "error"  # 不可恢复错误，终止
    MAX_TURNS = "max_turns"  # 超过最大轮次，优雅终止


class AgentType(enum.Enum):
    """Agent 类型（Phase 4: 多 Agent 协作）"""

    TRIAGE = "triage"
    CASE = "case"
    CONTRACT = "contract"
    RESEARCH = "research"
    GENERAL = "general"


# ─── Agent 定义 ───────────────────────────────────────────────────────────────

AGENT_CONFIGS: dict[AgentType, dict[str, Any]] = {
    AgentType.TRIAGE: {
        "name": "分诊助手",
        "system_prompt": SYSTEM_PROMPT,
        "tools_filter": None,  # 可见所有工具
        "handoffs": [AgentType.CASE, AgentType.CONTRACT, AgentType.RESEARCH, AgentType.GENERAL],
    },
    AgentType.CASE: {
        "name": "案件管理助手",
        "system_prompt": SYSTEM_PROMPT + "\n\n你专门负责案件管理相关操作，包括创建、查询、修改案件信息。",
        "tools_filter": lambda name: any(kw in name for kw in ["case", "案件", "litigation", "court", "hearing"]),
        "handoffs": [AgentType.GENERAL],
    },
    AgentType.CONTRACT: {
        "name": "合同管理助手",
        "system_prompt": SYSTEM_PROMPT + "\n\n你专门负责合同管理相关操作，包括查询、下载、生成合同。",
        "tools_filter": lambda name: any(kw in name for kw in ["contract", "合同", "agreement"]),
        "handoffs": [AgentType.GENERAL],
    },
    AgentType.RESEARCH: {
        "name": "法律检索助手",
        "system_prompt": SYSTEM_PROMPT + "\n\n你专门负责法律检索和企业信息查询。",
        "tools_filter": lambda name: any(
            kw in name for kw in ["search", "检索", "research", "查询", "enterprise", "company"]
        ),
        "handoffs": [AgentType.GENERAL],
    },
    AgentType.GENERAL: {
        "name": "通用助手",
        "system_prompt": SYSTEM_PROMPT,
        "tools_filter": None,
        "handoffs": [],
    },
}


# ─── Token 计数 ───────────────────────────────────────────────────────────────


def _count_tokens_approx(text: str) -> int:
    """粗略估算 token 数（中英混合约 1.5 字符/token）"""
    return max(1, len(text) // 2)


def _count_message_tokens(messages: list[dict[str, Any]]) -> int:
    """估算消息列表的总 token 数"""
    total = 0
    for msg in messages:
        content = msg.get("content") or ""
        total += _count_message_tokens_single(content)
        # tool_calls 也占 token
        if "tool_calls" in msg:
            for tc in msg["tool_calls"]:
                total += _count_message_tokens_single(json.dumps(tc, ensure_ascii=False))
    return total


def _count_message_tokens_single(content: str) -> int:
    """单条消息的 token 估算"""
    if not content:
        return 0
    return _count_tokens_approx(content) + 4  # role 等开销


# ─── 主服务 ───────────────────────────────────────────────────────────────────


class WorkbenchChatService:
    """工作台对话编排服务"""

    def __init__(self) -> None:
        self.mcp_client = WorkbenchMCPClient()
        # Phase 2: 审批等待机制
        self._approval_events: dict[str, asyncio.Event] = {}
        self._approval_results: dict[str, bool] = {}

    # ── 审批 API（Phase 2） ──────────────────────────────────────────────

    def resolve_approval(self, approval_id: str, approved: bool) -> bool:
        """前端调用此方法来响应审批请求"""
        if approval_id not in self._approval_events:
            return False
        self._approval_results[approval_id] = approved
        self._approval_events[approval_id].set()
        return True

    # ── 后端配置 ─────────────────────────────────────────────────────────

    @staticmethod
    async def _get_backend_config(backend_name: str) -> tuple[str, str]:
        """获取指定后端的 API Key 和 Base URL"""
        if backend_name == "ollama":
            return "", LLMConfig.get_ollama_base_url()
        if backend_name == "openai_compatible":
            return (
                await LLMConfig.get_openai_compatible_api_key_async(),
                await LLMConfig.get_openai_compatible_base_url_async(),
            )
        # 默认 siliconflow
        return await LLMConfig.get_api_key_async(), await LLMConfig.get_base_url_async()

    # ── 主入口 ───────────────────────────────────────────────────────────

    async def stream_chat(
        self,
        session_id: int,
        user_message: str,
        llm_model: str = "",
        agent_type: str = "",
    ) -> AsyncIterator[dict[str, Any]]:
        """流式对话主入口

        Args:
            session_id: 会话 ID
            user_message: 用户消息
            llm_model: 指定模型（可选，覆盖会话默认）
            agent_type: Agent 类型（可选，默认 triage）

        Yields:
            SSE 事件字典
        """
        from ..models import WorkbenchMessage, WorkbenchSession

        start_time = time.perf_counter()

        # 获取会话
        try:
            session = await WorkbenchSession.objects.aget(id=session_id)
        except WorkbenchSession.DoesNotExist:
            yield {"type": "error", "message": "会话不存在"}
            return

        model = llm_model or session.llm_model or LLMConfig.get_default_model()

        # Phase 1.3: 模型切换同步 - 更新 session 的 llm_model
        if llm_model and llm_model != session.llm_model:
            await WorkbenchSession.objects.filter(id=session_id).aupdate(llm_model=llm_model)
            session.llm_model = llm_model

        # 保存用户消息
        await WorkbenchMessage.objects.acreate(
            session_id=session_id,
            role=WorkbenchMessage.Role.USER,
            content=user_message,
        )

        yield {"type": "meta", "session_id": str(session.session_id), "model": model}

        # Phase 4: 解析 Agent 类型
        try:
            agent = AgentType(agent_type) if agent_type else AgentType.TRIAGE
        except ValueError:
            agent = AgentType.TRIAGE

        # 获取历史消息
        history = await self._get_history(session_id)

        # Phase 3: 上下文管理 - 摘要压缩
        history = await self._compress_history(session_id, history)

        # Phase 4: 按 Agent 类型过滤工具
        all_tools = await self._get_tools()
        agent_config = AGENT_CONFIGS[agent]
        tools = self._filter_tools(all_tools, agent_config.get("tools_filter"))

        # 构建上下文
        messages = self._build_context(history, agent_config["system_prompt"])

        # Phase 3: Token 预算裁剪
        messages = self._trim_context(messages, MAX_CONTEXT_TOKENS)

        # 调用 LLM（支持多轮工具调用）
        full_response: list[str] = []
        try:
            async for event in self._call_llm_with_tools(
                session_id=session_id,
                messages=messages,
                model=model,
                tools=tools,
                agent=agent,
            ):
                if event["type"] == "delta":
                    full_response.append(event.get("content", ""))
                yield event
        except Exception as e:
            logger.exception("LLM 调用失败")
            yield {"type": "error", "message": str(e)}
            return

        # 保存助手消息
        content = "".join(full_response)
        if content:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await WorkbenchMessage.objects.acreate(
                session_id=session_id,
                role=WorkbenchMessage.Role.ASSISTANT,
                content=content,
                llm_model=model,
                metadata={
                    "duration_ms": round(duration_ms, 2),
                    "agent_type": agent.value,
                },
            )

        # 更新会话标题（如果是第一条消息）
        if not session.title:
            title = user_message[:50]
            await WorkbenchSession.objects.filter(id=session_id).aupdate(title=title)

        yield {"type": "done", "session_id": str(session.session_id)}

    # ── Agent Loop（Phase 1: 结构化） ────────────────────────────────────

    async def _call_llm_with_tools(
        self,
        session_id: int,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]],
        agent: AgentType = AgentType.TRIAGE,
    ) -> AsyncIterator[dict[str, Any]]:
        """调用 LLM，支持多轮工具调用（结构化 Agent Loop）"""
        # 根据模型名称解析后端配置
        backend_name = LLMConfig.resolve_backend_for_model(model)
        api_key, base_url = await self._get_backend_config(backend_name)

        # Ollama 不需要 API Key
        if backend_name != "ollama" and not api_key:
            yield {"type": "error", "message": "LLM API Key 未配置"}
            return

        client = openai.AsyncOpenAI(
            api_key=api_key or "ollama",
            base_url=base_url,
        )

        current_messages = list(messages)
        round_count = 0

        while round_count < MAX_TOOL_ROUNDS:
            round_count += 1

            # 调用 LLM
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": current_messages,
                "temperature": 0.7,
                "stream": True,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            try:
                stream = await client.chat.completions.create(**kwargs)
            except Exception as e:
                logger.exception("LLM API 调用失败")
                yield {"type": "error", "message": f"LLM 调用失败: {e}"}
                return

            # 收集完整响应
            full_content: list[str] = []
            tool_calls_data: dict[int, dict[str, Any]] = {}
            has_tool_calls = False

            async for chunk in stream:
                choices = chunk.choices or []
                if not choices:
                    continue

                delta = choices[0].delta
                if delta is None:
                    continue

                # 处理文本内容
                if delta.content:
                    full_content.append(delta.content)
                    yield {"type": "delta", "content": delta.content}

                # 处理工具调用
                if delta.tool_calls:
                    has_tool_calls = True
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_data:
                            tool_calls_data[idx] = {
                                "id": tc.id or "",
                                "name": "",
                                "arguments": "",
                            }
                        if tc.id:
                            tool_calls_data[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                tool_calls_data[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls_data[idx]["arguments"] += tc.function.arguments

            # Phase 1: 结构化 NextStep 判断
            next_step = self._determine_next_step(has_tool_calls, full_content, round_count)

            if next_step == NextStep.FINAL_OUTPUT:
                return

            if next_step == NextStep.MAX_TURNS:
                yield {"type": "delta", "content": "\n\n[已达到最大工具调用轮次]"}
                logger.warning("工具调用达到最大轮次 %d", MAX_TOOL_ROUNDS)
                return

            if next_step == NextStep.ERROR:
                return

            # NextStep.TOOL_CALL: 执行工具调用
            # 构建 assistant 消息（含 tool_calls）
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": "".join(full_content) or None,
            }
            assistant_tool_calls = []
            for idx in sorted(tool_calls_data.keys()):
                tc = tool_calls_data[idx]
                assistant_tool_calls.append(
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                        },
                    }
                )
            assistant_message["tool_calls"] = assistant_tool_calls
            current_messages.append(assistant_message)

            # 逐个执行工具调用
            for idx in sorted(tool_calls_data.keys()):
                tc = tool_calls_data[idx]
                tool_name = tc["name"]
                tool_args_str = tc["arguments"]
                tool_call_id = tc["id"] or f"call_{uuid.uuid4().hex[:8]}"

                # 解析参数
                try:
                    tool_args = json.loads(tool_args_str) if tool_args_str else {}
                except json.JSONDecodeError:
                    tool_args = {}

                # Phase 4: Handoff 检测 - 如果是 handoff_to_xxx 工具
                if tool_name.startswith("handoff_to_"):
                    target_name = tool_name.replace("handoff_to_", "")
                    try:
                        target_agent = AgentType(target_name)
                        yield {
                            "type": "handoff",
                            "from_agent": agent.value,
                            "to_agent": target_agent.value,
                            "agent_name": AGENT_CONFIGS[target_agent]["name"],
                        }
                        # 更新工具列表为目标 Agent 的工具
                        target_config = AGENT_CONFIGS[target_agent]
                        fresh_tools = await self._get_tools()
                        tools = self._filter_tools(fresh_tools, target_config.get("tools_filter"))
                        # 替换 system prompt
                        for i, msg in enumerate(current_messages):
                            if msg.get("role") == "system":
                                current_messages[i] = {
                                    "role": "system",
                                    "content": target_config["system_prompt"],
                                }
                                break
                        # 添加 handoff 结果
                        current_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": json.dumps(
                                    {"status": "ok", "message": f"已切换到{target_config['name']}"},
                                    ensure_ascii=False,
                                ),
                            }
                        )
                        continue
                    except ValueError:
                        pass

                # Phase 2: 审批门控检查
                if tool_name in HIGH_RISK_TOOLS:
                    approval_id = uuid.uuid4().hex[:12]
                    yield {
                        "type": "approval_request",
                        "approval_id": approval_id,
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "message": f"即将执行高风险操作：{tool_name}，请确认是否继续",
                    }

                    # 等待前端审批
                    approved = await self._wait_for_approval(approval_id, timeout=300)
                    if not approved:
                        # 用户拒绝 - 将拒绝结果返回给 LLM
                        yield {
                            "type": "tool_call",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "arguments": tool_args,
                        }
                        deny_msg = json.dumps(
                            {"error": "用户拒绝执行此操作", "user_denied": True},
                            ensure_ascii=False,
                        )
                        yield {
                            "type": "tool_result",
                            "tool_call_id": tool_call_id,
                            "name": tool_name,
                            "result": deny_msg[:2000],
                        }
                        current_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": deny_msg,
                            }
                        )
                        # 保存到数据库
                        await self._save_tool_message(
                            session_id,
                            tool_call_id,
                            tool_name,
                            tool_args,
                            {"error": "用户拒绝执行此操作", "user_denied": True},
                        )
                        continue

                yield {
                    "type": "tool_call",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "arguments": tool_args,
                }

                # 调用 MCP 工具
                try:
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                except Exception as e:
                    # Phase 1: 工具错误自纠正 - 错误作为 tool result 返回给 LLM
                    logger.exception("MCP 工具调用失败: %s", tool_name)
                    result = {"error": str(e), "tool_name": tool_name}
                    result_str = json.dumps(result, ensure_ascii=False)

                # 保存工具调用消息到数据库
                await self._save_tool_message(
                    session_id,
                    tool_call_id,
                    tool_name,
                    tool_args,
                    result,
                )

                yield {
                    "type": "tool_result",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "result": result_str[:2000],
                }

                # Phase 1: 工具结果（包括错误）都返回给 LLM，让 LLM 自我纠正
                current_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_str,
                    }
                )

    # ── NextStep 判断（Phase 1） ─────────────────────────────────────────

    @staticmethod
    def _determine_next_step(
        has_tool_calls: bool,
        content: list[str],
        round_count: int,
    ) -> NextStep:
        """判断 Agent Loop 下一步"""
        if round_count >= MAX_TOOL_ROUNDS:
            return NextStep.MAX_TURNS

        if not has_tool_calls:
            return NextStep.FINAL_OUTPUT

        return NextStep.TOOL_CALL

    # ── 审批等待（Phase 2） ──────────────────────────────────────────────

    async def _wait_for_approval(self, approval_id: str, timeout: float = 300) -> bool:
        """等待前端审批响应"""
        event = asyncio.Event()
        self._approval_events[approval_id] = event
        self._approval_results[approval_id] = False

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return self._approval_results.get(approval_id, False)
        except TimeoutError:
            logger.warning("审批超时: %s", approval_id)
            return False
        finally:
            self._approval_events.pop(approval_id, None)
            self._approval_results.pop(approval_id, None)

    # ── 工具管理（Phase 4: 权限隔离） ────────────────────────────────────

    async def _get_tools(self) -> list[dict[str, Any]]:
        """获取 MCP 工具列表"""
        try:
            return await self.mcp_client.list_tools()
        except Exception:
            logger.exception("获取 MCP 工具列表失败")
            return []

    @staticmethod
    def _filter_tools(
        tools: list[dict[str, Any]],
        tools_filter: Any = None,
    ) -> list[dict[str, Any]]:
        """按 Agent 类型过滤工具（Phase 4: 工具权限隔离）"""
        if tools_filter is None:
            return tools
        return [t for t in tools if tools_filter(t.get("function", {}).get("name", ""))]

    # ── 历史消息管理 ─────────────────────────────────────────────────────

    async def _get_history(self, session_id: int, limit: int = 20) -> list:
        """获取历史消息（滑动窗口）"""
        from ..models import WorkbenchMessage

        messages = []
        async for msg in WorkbenchMessage.objects.filter(session_id=session_id).order_by("-created_at")[:limit]:
            messages.append(msg)
        messages.reverse()
        return messages

    # ── 上下文管理（Phase 3） ─────────────────────────────────────────────

    async def _compress_history(
        self,
        session_id: int,
        history: list,
    ) -> list:
        """Phase 3: 摘要压缩 - 当历史消息过多时，用摘要替换旧消息"""
        if len(history) <= SUMMARY_THRESHOLD:
            return history

        # 分离旧消息和新消息
        old_messages = history[: len(history) - SUMMARY_THRESHOLD]
        new_messages = history[len(history) - SUMMARY_THRESHOLD :]

        # 检查是否已有摘要
        from ..models import WorkbenchMessage

        summary_msg = await WorkbenchMessage.objects.filter(
            session_id=session_id,
            role=WorkbenchMessage.Role.SYSTEM,
            metadata__contains={"type": "summary"},
        ).afirst()

        if summary_msg:
            # 已有摘要，只返回摘要 + 新消息
            return [summary_msg] + new_messages

        # 生成摘要（简化实现：取旧消息的关键信息）
        summary_parts = []
        for msg in old_messages:
            if msg.role == "user":
                summary_parts.append(f"用户: {msg.content[:100]}")
            elif msg.role == "assistant" and msg.content:
                summary_parts.append(f"AI: {msg.content[:100]}")
            elif msg.role == "tool" and msg.tool_name:
                summary_parts.append(f"工具[{msg.tool_name}]: 已执行")

        summary_text = "以下是对之前对话的摘要：\n" + "\n".join(summary_parts[-20:])

        # 保存摘要到数据库
        summary_msg = await WorkbenchMessage.objects.acreate(
            session_id=session_id,
            role=WorkbenchMessage.Role.SYSTEM,
            content=summary_text,
            metadata={"type": "summary", "summarized_count": len(old_messages)},
        )

        return [summary_msg] + new_messages

    def _trim_context(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int,
    ) -> list[dict[str, Any]]:
        """Phase 3: Token 预算裁剪 - 保证总 token 不超限"""
        total_tokens = _count_message_tokens(messages)
        if total_tokens <= max_tokens:
            return messages

        # 保留 system prompt 和最后几条消息
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        system_tokens = _count_message_tokens(system_msgs)
        budget = max_tokens - system_tokens

        # 从最新消息向前保留
        trimmed: list[dict[str, Any]] = []
        used_tokens = 0
        for msg in reversed(other_msgs):
            msg_tokens = _count_message_tokens_single(msg.get("content") or "")
            if "tool_calls" in msg:
                msg_tokens += _count_message_tokens_single(json.dumps(msg["tool_calls"], ensure_ascii=False))
            if used_tokens + msg_tokens > budget:
                break
            trimmed.append(msg)
            used_tokens += msg_tokens

        trimmed.reverse()
        return system_msgs + trimmed

    # ── 工具消息保存 ─────────────────────────────────────────────────────

    @staticmethod
    async def _save_tool_message(
        session_id: int,
        tool_call_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        result: Any,
    ) -> None:
        """保存工具调用消息到数据库"""
        from ..models import WorkbenchMessage

        result_str = json.dumps(result, ensure_ascii=False, default=str)
        await WorkbenchMessage.objects.acreate(
            session_id=session_id,
            role=WorkbenchMessage.Role.TOOL,
            content=result_str[:10000],
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_input=tool_args,
            tool_output={"raw": result_str[:10000]},
        )

    # ── 上下文构建 ───────────────────────────────────────────────────────

    def _build_context(
        self,
        history: list,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> list[dict[str, Any]]:
        """构建发送给 LLM 的上下文"""
        context: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        for msg in history:
            if msg.role == "tool":
                context.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": msg.content,
                    }
                )
            elif msg.role == "assistant" and msg.tool_name:
                context.append(
                    {
                        "role": "assistant",
                        "content": msg.content or None,
                    }
                )
            elif msg.role == "system":
                # 系统消息（如摘要）插入到 system prompt 之后
                context.insert(1, {"role": "system", "content": msg.content})
            else:
                context.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return context
