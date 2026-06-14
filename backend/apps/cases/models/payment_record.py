"""案件收支记录模型"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .case import Case
from .log import CaseLog


class PaymentDirection(models.TextChoices):
    """收支方向"""

    INCOME = "income", _("收入")
    EXPENSE = "expense", _("支出")


class PaymentMethod(models.TextChoices):
    """支付方式"""

    BANK_TRANSFER = "bank_transfer", _("银行转账")
    COURT_ENFORCEMENT = "court_enforcement", _("法院执行")
    CASH = "cash", _("现金")
    ONLINE_PAYMENT = "online_payment", _("在线支付")
    CHECK = "check", _("支票")
    OTHER = "other", _("其他")


class PaymentPurpose(models.TextChoices):
    """款项用途（预设枚举，支持自定义扩展）"""

    # 收入类
    COUNTERPARTY_PAYMENT = "counterparty_payment", _("相对方主动支付")
    ENFORCEMENT_RECOVERY = "enforcement_recovery", _("执行回款")
    COURT_FEE_REFUND = "court_fee_refund", _("法院退还诉讼费")
    SETTLEMENT = "settlement", _("和解款")

    # 支出 — 法院费用
    COURT_FEE = "court_fee", _("诉讼费")
    PRESERVATION_FEE = "preservation_fee", _("诉讼保全费")
    PROPERTY_PRESERVATION_FEE = "property_preservation_fee", _("财产保全费")
    ANNOUNCEMENT_FEE = "announcement_fee", _("公告费")
    EXECUTION_FEE = "execution_fee", _("执行费")
    APPRAISAL_FEE = "appraisal_fee", _("鉴定费")

    # 支出 — 律师费用
    ATTORNEY_FEE = "attorney_fee", _("律师费")
    TRAVEL_FEE = "travel_fee", _("差旅费")
    INVESTIGATION_FEE = "investigation_fee", _("调查费")

    # 支出 — 保险费用
    PROPERTY_INSURANCE_FEE = "property_insurance_fee", _("财产保险费")
    GUARANTEE_FEE = "guarantee_fee", _("保函费")

    # 支出 — 其他
    NOTARY_FEE = "notary_fee", _("公证费")
    ASSESSMENT_FEE = "assessment_fee", _("评估费")
    EXPRESS_FEE = "express_fee", _("快递费")
    OTHER_EXPENSE = "other_expense", _("其他费用")


class CasePaymentRecord(models.Model):
    """案件收支记录 — 关联案件和日志的收入/支出条目"""

    id: int
    case: Case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name="payment_records",
        verbose_name=_("关联案件"),
    )
    case_log: CaseLog | None = models.ForeignKey(
        CaseLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_records",
        verbose_name=_("关联日志"),
    )
    direction: str = models.CharField(
        max_length=16,
        choices=PaymentDirection.choices,
        verbose_name=_("收支方向"),
    )
    amount: Decimal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_("金额"),
    )
    purpose: str = models.CharField(
        max_length=64,
        choices=PaymentPurpose.choices,
        verbose_name=_("款项用途"),
    )
    payment_method: str = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
        verbose_name=_("支付方式"),
    )
    date: date = models.DateField(
        default=timezone.now,
        verbose_name=_("收支日期"),
    )
    note: str = models.TextField(
        blank=True,
        default="",
        verbose_name=_("备注"),
    )
    created_at: datetime = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("创建时间"),
    )
    updated_at: datetime = models.DateTimeField(
        auto_now=True,
        verbose_name=_("更新时间"),
    )

    class Meta:
        app_label = "cases"
        verbose_name = _("案件收支记录")
        verbose_name_plural = _("案件收支记录")
        ordering: ClassVar = ["-date", "-created_at"]
        indexes: ClassVar = [
            models.Index(fields=["case"]),
            models.Index(fields=["case_log"]),
            models.Index(fields=["direction"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self) -> str:
        direction_label = "收入" if self.direction == PaymentDirection.INCOME else "支出"
        return f"{self.date} {direction_label} ¥{self.amount} — {self.get_purpose_display()}"
