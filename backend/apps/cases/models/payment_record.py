"""案件收支记录模型"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

if TYPE_CHECKING:
    from django.db.models.fields.related_descriptors import RelatedManager


class PaymentMethod(models.TextChoices):
    """支付方式"""

    BANK_TRANSFER = "bank_transfer", _("银行转账")
    COURT_ENFORCEMENT = "court_enforcement", _("法院执行")
    CASH = "cash", _("现金")
    ONLINE_PAYMENT = "online_payment", _("线上支付")
    CHECK = "check", _("支票")
    OTHER = "other", _("其他")


class SourceType(models.TextChoices):
    """来源类型"""

    MANUAL = "manual", _("手动录入")
    CONTRACT_PAYMENT = "contract_payment", _("合同收款记录")
    CLIENT_PAYMENT = "client_payment", _("客户回款记录")
    LOG_BATCH_SPLIT = "log_batch_split", _("批量日志分摊")


class CasePaymentRecord(models.Model):
    """案件收支记录"""

    id: int
    case = models.ForeignKey(
        "cases.Case",
        on_delete=models.CASCADE,
        related_name="payment_records",
        verbose_name=_("案件"),
    )
    category = models.ForeignKey(
        "PaymentRecordCategory",
        on_delete=models.PROTECT,
        related_name="payment_records",
        verbose_name=_("款项用途"),
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_("金额"),
    )
    record_date = models.DateField(verbose_name=_("发生日期"))
    is_income = models.BooleanField(
        default=True,
        verbose_name=_("是否收入"),
        help_text=_("True=收入/回款, False=支出/费用"),
    )
    payment_method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        blank=True,
        null=True,
        verbose_name=_("支付方式"),
    )
    payer_payee_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("付款方/收款方"),
        help_text=_("收入时填写付款方名称，支出时填写收款方名称"),
    )
    case_number = models.ForeignKey(
        "CaseNumber",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_records",
        verbose_name=_("关联案号"),
    )
    source_type = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
        verbose_name=_("来源类型"),
    )
    source_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("来源ID"),
        help_text=_("关联的原始记录ID，如合同收款ID"),
    )
    is_split = models.BooleanField(
        default=False,
        verbose_name=_("是否分摊记录"),
        help_text=_("标记是否从批量操作分摊而来"),
    )
    split_parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="split_children",
        verbose_name=_("分摊来源记录"),
    )
    split_count = models.IntegerField(
        default=1,
        verbose_name=_("分摊份数"),
        help_text=_("如99个案件分摊，则为99"),
    )
    has_receipt = models.BooleanField(
        default=False,
        verbose_name=_("是否有凭证"),
    )
    receipt_note = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name=_("凭证说明"),
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name=_("说明/备注"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_records",
        verbose_name=_("操作人"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("更新时间"))

    history = HistoricalRecords()

    if TYPE_CHECKING:
        split_children: RelatedManager[CasePaymentRecord]

    class Meta:
        verbose_name = _("案件收支记录")
        verbose_name_plural = _("案件收支记录")
        ordering = ["-record_date", "-created_at"]
        indexes: ClassVar = [
            models.Index(fields=["case", "-record_date"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_income"]),
            models.Index(fields=["source_type"]),
            models.Index(fields=["is_split"]),
        ]

    def __str__(self) -> str:
        direction = _("收") if self.is_income else _("支")
        return f"{self.case.name} - {direction}¥{self.amount} ({self.category.name})"

    @property
    def actual_amount(self) -> Decimal:
        """实际金额（分摊记录乘以份数）"""
        if self.is_split and self.split_count > 1:
            return self.amount * Decimal(str(self.split_count))
        return self.amount
