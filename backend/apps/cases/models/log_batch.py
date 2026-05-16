"""批量创建案件日志的模板/记录"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager


class CaseLogBatch(models.Model):
    """批量日志记录（用于追踪和溯源）"""

    id: int
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="log_batches",
        verbose_name=_("操作人"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    original_content = models.TextField(verbose_name=_("原始日志内容"))
    case_ids = models.JSONField(
        default=list,
        verbose_name=_("案件ID列表"),
        help_text=_("参与批量创建的案件ID列表"),
    )
    reminder_type = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=_("提醒类型"),
    )
    reminder_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("提醒时间"),
    )
    has_expense_split = models.BooleanField(
        default=False,
        verbose_name=_("包含费用分摊"),
    )
    expense_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("费用总金额"),
    )
    expense_category = models.ForeignKey(
        "PaymentRecordCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expense_log_batches",
        verbose_name=_("费用类型"),
    )
    expense_split_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("费用分摊份数"),
        help_text=_("费用分摊到的案件数量，可小于case_ids数量"),
    )
    expense_per_case = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("每案件分摊金额"),
    )
    expense_record_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("费用发生日期"),
    )
    has_income_split = models.BooleanField(
        default=False,
        verbose_name=_("包含收入分摊"),
    )
    income_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("收入总金额"),
    )
    income_category = models.ForeignKey(
        "PaymentRecordCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="income_log_batches",
        verbose_name=_("收入类型"),
    )
    income_split_count = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("收入分摊份数"),
        help_text=_("收入分摊到的案件数量，可小于case_ids数量"),
    )
    income_per_case = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("每案件收入金额"),
    )
    income_record_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_("收入发生日期"),
    )
    total_cases = models.IntegerField(
        default=0,
        verbose_name=_("总案件数"),
    )
    success_count = models.IntegerField(
        default=0,
        verbose_name=_("成功数"),
    )
    fail_count = models.IntegerField(
        default=0,
        verbose_name=_("失败数"),
    )
    error_message = models.TextField(
        blank=True,
        default="",
        verbose_name=_("错误信息"),
    )

    if TYPE_CHECKING:
        logs: RelatedManager["CaseLog"]
        payment_records: RelatedManager["CasePaymentRecord"]

    class Meta:
        verbose_name = _("批量日志记录")
        verbose_name_plural = _("批量日志记录")
        ordering = ["-created_at"]
        indexes: ClassVar = [
            models.Index(fields=["actor", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"批量日志 #{self.id} - {self.total_cases}个案件"
