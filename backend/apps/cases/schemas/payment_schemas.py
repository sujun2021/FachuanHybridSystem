"""案件收支记录相关 Schema"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar

from ninja import ModelSchema, Schema

from apps.cases.models import CasePaymentRecord, PaymentMethod, PaymentRecordCategory, SourceType

from .base import ModelSchema as BaseModelSchema
from .base import Schema as BaseSchema


class PaymentRecordCategoryOut(ModelSchema, BaseSchema):
    class Meta:
        model = PaymentRecordCategory
        fields: ClassVar = ["id", "name", "is_income", "is_system", "sort_order", "created_at"]


class PaymentRecordCategoryCreate(BaseSchema):
    name: str
    is_income: bool = True


class PaymentRecordIn(BaseSchema):
    case_id: int
    category_id: int
    amount: Decimal
    record_date: date
    is_income: bool = True
    payment_method: str | None = None
    payer_payee_name: str | None = ""
    case_number_id: int | None = None
    source_type: str | None = None
    source_id: int | None = None
    is_split: bool = False
    split_count: int = 1
    has_receipt: bool = False
    receipt_note: str | None = ""
    description: str | None = ""


class PaymentRecordOut(ModelSchema, BaseSchema):
    category_detail: PaymentRecordCategoryOut | None = None
    category_name: str | None = None
    is_income_display: str | None = None
    payment_method_display: str | None = None
    source_type_display: str | None = None
    case_name: str | None = None
    actor_name: str | None = None

    class Meta:
        model = CasePaymentRecord
        fields: ClassVar = [
            "id",
            "case",
            "category",
            "amount",
            "record_date",
            "is_income",
            "payment_method",
            "payer_payee_name",
            "case_number",
            "source_type",
            "source_id",
            "is_split",
            "split_count",
            "has_receipt",
            "receipt_note",
            "description",
            "created_at",
            "updated_at",
        ]

    @staticmethod
    def resolve_category_name(obj: CasePaymentRecord) -> str | None:
        if hasattr(obj, "category") and obj.category:
            return obj.category.name
        return None

    @staticmethod
    def resolve_is_income_display(obj: CasePaymentRecord) -> str | None:
        return _("收入") if obj.is_income else _("支出")

    @staticmethod
    def resolve_payment_method_display(obj: CasePaymentRecord) -> str | None:
        if obj.payment_method:
            return obj.get_payment_method_display()
        return None

    @staticmethod
    def resolve_source_type_display(obj: CasePaymentRecord) -> str | None:
        if obj.source_type:
            return obj.get_source_type_display()
        return None

    @staticmethod
    def resolve_case_name(obj: CasePaymentRecord) -> str | None:
        if hasattr(obj, "case") and obj.case:
            return obj.case.name
        return None

    @staticmethod
    def resolve_actor_name(obj: CasePaymentRecord) -> str | None:
        if hasattr(obj, "actor") and obj.actor:
            return getattr(obj.actor, "real_name", None) or getattr(obj.actor, "username", None)
        return None


class PaymentRecordUpdate(BaseSchema):
    category_id: int | None = None
    amount: Decimal | None = None
    record_date: date | None = None
    is_income: bool | None = None
    payment_method: str | None = None
    payer_payee_name: str | None = None
    case_number_id: int | None = None
    has_receipt: bool | None = None
    receipt_note: str | None = None
    description: str | None = None


class PaymentSummaryOut(BaseSchema):
    case_id: int
    case_name: str
    total_income: Decimal
    total_expense: Decimal
    net_amount: Decimal
    income_count: int
    expense_count: int
    income_records: list[PaymentRecordOut]
    expense_records: list[PaymentRecordOut]


class PaymentStatisticsOut(BaseSchema):
    total_income: Decimal = Decimal("0")
    total_expense: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")
    income_count: int = 0
    expense_count: int = 0
    by_category: list[dict]


__all__ = [
    "PaymentRecordCategoryOut",
    "PaymentRecordCategoryCreate",
    "PaymentRecordIn",
    "PaymentRecordOut",
    "PaymentRecordUpdate",
    "PaymentSummaryOut",
    "PaymentStatisticsOut",
]
