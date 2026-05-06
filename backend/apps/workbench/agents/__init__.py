"""工作台 Agent 定义 - 基于 Pydantic AI"""

from .approval import HIGH_RISK_TOOLS, approval_manager
from .definitions import (
    case_agent,
    contract_agent,
    general_agent,
    mcp_server,
    research_agent,
    set_event_queue,
    triage_agent,
)
from .deps import WorkbenchDeps

__all__ = [
    "HIGH_RISK_TOOLS",
    "WorkbenchDeps",
    "approval_manager",
    "case_agent",
    "contract_agent",
    "general_agent",
    "mcp_server",
    "research_agent",
    "set_event_queue",
    "triage_agent",
]
