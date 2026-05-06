"""工作台对话编排服务 - Pydantic AI Agent

使用 Pydantic AI 的 agent.iter() 驱动对话循环，替代手写 agent loop。
通过 asyncio.Queue 桥接 MCP 审批回调和 SSE 流式响应。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent

from ..agents import (
    WorkbenchDeps,
    approval_manager,
    build_model,
    case_agent,
    contract_agent,
    general_agent,
    research_agent,
    set_event_queue,
    triage_agent,
)

logger = logging.getLogger(__name__)

# ─── 常量 ────────────────────────────────────────────────────────────────────

AGENT_MAP: dict[str, Agent] = {
    "triage": triage_agent,
    "case": case_agent,
    "contract": contract_agent,
    "research": research_agent,
    "general": general_agent,
}


# ─── 主服务 ───────────────────────────────────────────────────────────────────


class WorkbenchChatService:
    """工作台对话编排服务"""

    def __init__(self) -> None:
        self.approval_manager = approval_manager

    def resolve_approval(self, approval_id: str, approved: bool) -> bool:
        """前端调用此方法来响应审批请求"""
        return self.approval_manager.resolve(approval_id, approved)

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

        model_name = llm_model or session.llm_model or ""

        # 模型切换同步
        if llm_model and llm_model != session.llm_model:
            await WorkbenchSession.objects.filter(id=session_id).aupdate(llm_model=llm_model)
            session.llm_model = llm_model

        # 保存用户消息
        await WorkbenchMessage.objects.acreate(
            session_id=session_id,
            role=WorkbenchMessage.Role.USER,
            content=user_message,
        )

        yield {"type": "meta", "session_id": str(session.session_id), "model": model_name}

        # 选择 Agent
        agent = AGENT_MAP.get(agent_type, triage_agent)

        # 构建依赖
        event_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        deps = WorkbenchDeps(
            session_id=session_id,
            user_id=session.user_id,
            llm_model=model_name,
        )

        # 设置审批事件队列（MCP process_tool_call 回调会用到）
        set_event_queue(event_queue)

        # 构建模型
        model = build_model(model_name) if model_name else None

        # 流式运行 Agent
        full_response: list[str] = []
        try:
            async for event in self._run_agent(
                agent=agent,
                user_message=user_message,
                model=model,
                deps=deps,
                event_queue=event_queue,
            ):
                if event["type"] == "delta":
                    full_response.append(event.get("content", ""))
                yield event
        except Exception:
            logger.exception("Agent 运行失败")
            yield {"type": "error", "message": "Agent 运行失败，请稍后重试"}
        finally:
            set_event_queue(None)

        # 保存助手消息
        content = "".join(full_response)
        if content:
            duration_ms = (time.perf_counter() - start_time) * 1000
            await WorkbenchMessage.objects.acreate(
                session_id=session_id,
                role=WorkbenchMessage.Role.ASSISTANT,
                content=content,
                llm_model=model_name,
                metadata={
                    "duration_ms": round(duration_ms, 2),
                    "agent_type": agent_type or "triage",
                },
            )

        # 更新会话标题（如果是第一条消息）
        if not session.title:
            title = user_message[:50]
            await WorkbenchSession.objects.filter(id=session_id).aupdate(title=title)

        yield {"type": "done", "session_id": str(session.session_id)}

    # ── Agent 运行（并发事件流） ──────────────────────────────────────────

    async def _run_agent(
        self,
        agent: Agent,
        user_message: str,
        model: Any,
        deps: WorkbenchDeps,
        event_queue: asyncio.Queue[dict[str, Any] | None],
    ) -> AsyncIterator[dict[str, Any]]:
        """运行 Agent 并流式输出 SSE 事件

        使用 asyncio.Queue 桥接：
        - Agent 任务：运行 agent.iter()，将工具事件推入队列
        - 主循环：从队列消费事件，yield 给 SSE 响应
        """
        # Agent 任务：推事件到队列
        async def agent_task() -> None:
            try:
                async with agent.iter(
                    user_message,
                    deps=deps,
                    model=model,
                ) as run:
                    async for node in run:
                        if Agent.is_model_request_node(node):
                            # 流式收集文本和工具事件
                            async with node.stream(run.ctx) as stream:
                                async for event in stream:
                                    if isinstance(event, FunctionToolCallEvent):
                                        # 工具调用（执行前）
                                        args = event.part.args
                                        if isinstance(args, str):
                                            try:
                                                args = json.loads(args)
                                            except (json.JSONDecodeError, TypeError):
                                                pass
                                        await event_queue.put(
                                            {
                                                "type": "tool_call",
                                                "tool_call_id": event.part.tool_call_id or "",
                                                "name": event.part.tool_name,
                                                "arguments": args,
                                            }
                                        )
                                    elif isinstance(event, FunctionToolResultEvent):
                                        # 工具结果
                                        result_content = event.content
                                        if hasattr(result_content, "content"):
                                            result_content = result_content.content
                                        result_str = str(result_content) if result_content else ""
                                        await event_queue.put(
                                            {
                                                "type": "tool_result",
                                                "tool_call_id": event.result.tool_call_id,
                                                "name": event.result.tool_name,
                                                "result": result_str[:2000],
                                            }
                                        )

                        elif Agent.is_call_tools_node(node):
                            # 工具执行节点：等待完成
                            async with node.stream(run.ctx) as stream:
                                async for _event in stream:
                                    pass

                        elif Agent.is_end_node(node):
                            # Agent 结束，发送最终文本
                            if run.result and run.result.output:
                                output = run.result.output
                                if isinstance(output, str) and output:
                                    await event_queue.put(
                                        {"type": "delta", "content": output}
                                    )
            except Exception:
                logger.exception("Agent 任务异常")
                await event_queue.put({"type": "error", "message": "Agent 运行异常"})
            finally:
                # 发送结束哨兵
                await event_queue.put(None)

        # 启动 Agent 任务
        task = asyncio.create_task(agent_task())

        # 主循环：从队列消费事件
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield event
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
