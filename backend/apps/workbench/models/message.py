"""工作台对话消息模型"""

from __future__ import annotations

from typing import ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _


class WorkbenchMessage(models.Model):
    """工作台对话消息"""

    class Role(models.TextChoices):
        SYSTEM = "system", _("系统")
        USER = "user", _("用户")
        ASSISTANT = "assistant", _("助手")
        TOOL = "tool", _("工具")

    id: int
    session = models.ForeignKey(
        "workbench.WorkbenchSession",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(_("角色"), max_length=20, choices=Role.choices)
    content = models.TextField(_("内容"), blank=True, default="")
    llm_model = models.CharField(
        _("LLM 模型"),
        max_length=255,
        blank=True,
        default="",
        help_text="该消息使用的 LLM 模型 ID",
    )
    tool_call_id = models.CharField(
        _("工具调用 ID"),
        max_length=255,
        blank=True,
        default="",
        help_text="工具调用的唯一标识",
    )
    tool_name = models.CharField(
        _("工具名称"),
        max_length=255,
        blank=True,
        default="",
        help_text="工具名称（如果是工具调用）",
    )
    tool_input = models.JSONField(_("工具输入"), default=dict, blank=True, help_text="工具输入参数")
    tool_output = models.JSONField(_("工具输出"), default=dict, blank=True, help_text="工具输出结果")
    metadata = models.JSONField(_("元数据"), default=dict, blank=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        db_table = "workbench_message"
        verbose_name = _("工作台消息")
        verbose_name_plural = _("工作台消息")
        ordering = ["created_at"]
        indexes: ClassVar = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        content_preview = self.content[:50] if self.content else f"[{self.tool_name}]"
        return f"[{self.role}] {content_preview}"
