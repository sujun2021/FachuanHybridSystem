"""收件箱消息查询服务。"""

from __future__ import annotations

from typing import Any

from apps.message_hub.models import InboxMessage


def get_base_queryset() -> Any:
    """获取收件箱消息基础查询集（含 source 和 credential 关联）。"""
    return InboxMessage.objects.select_related("source", "source__credential").order_by("-received_at")


def get_message_or_none(pk: int) -> InboxMessage | None:
    """按 ID 获取单条消息，不存在返回 None。"""
    return get_base_queryset().filter(pk=pk).first()
