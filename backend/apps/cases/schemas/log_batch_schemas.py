"""批量日志创建相关 Schema"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import ClassVar

from ninja import ModelSchema, Schema

from apps.cases.models import CaseLogBatch

from .base import ModelSchema as BaseModelSchema
from .base import Schema as BaseSchema
from .log_schemas import CaseLogOut


class LogBatchPreviewItem(BaseSchema):
    case_id: int
    case_name: str
    content_preview: str
    expense_amount: Decimal | None = None
    has_expense_split: bool = False
    income_amount: Decimal | None = None
    has_income_split: bool = False


class LogBatchPreviewOut(BaseSchema):
    total_count: int
    logs: list[LogBatchPreviewItem]
    expense_per_case: Decimal | None = None
    has_expense_split: bool = False
    income_per_case: Decimal | None = None
    has_income_split: bool = False
    original_content: str


class LogBatchCreateIn(BaseSchema):
    case_ids: list[int]
    content: str
    reminder_type: str | None = None
    reminder_time: datetime | None = None
    has_expense_split: bool = False
    expense_amount: Decimal | None = None
    expense_category_id: int | None = None
    expense_split_count: int | None = None
    expense_record_date: date | None = None
    expense_payment_method: str | None = None
    expense_description: str | None = None
    has_income_split: bool = False
    income_amount: Decimal | None = None
    income_category_id: int | None = None
    income_split_count: int | None = None
    income_record_date: date | None = None
    income_payment_method: str | None = None
    income_description: str | None = None


class LogBatchOut(ModelSchema, BaseSchema):
    expense_category_name: str | None = None
    income_category_name: str | None = None
    actor_name: str | None = None
    created_logs: list[CaseLogOut] | None = None

    class Meta:
        model = CaseLogBatch
        fields: ClassVar = [
            "id",
            "original_content",
            "case_ids",
            "reminder_type",
            "reminder_time",
            "has_expense_split",
            "expense_amount",
            "expense_split_count",
            "expense_per_case",
            "expense_record_date",
            "has_income_split",
            "income_amount",
            "income_split_count",
            "income_per_case",
            "income_record_date",
            "total_cases",
            "success_count",
            "fail_count",
            "error_message",
            "created_at",
        ]

    @staticmethod
    def resolve_expense_category_name(obj: CaseLogBatch) -> str | None:
        if hasattr(obj, "expense_category") and obj.expense_category:
            return obj.expense_category.name
        return None

    @staticmethod
    def resolve_income_category_name(obj: CaseLogBatch) -> str | None:
        if hasattr(obj, "income_category") and obj.income_category:
            return obj.income_category.name
        return None

    @staticmethod
    def resolve_actor_name(obj: CaseLogBatch) -> str | None:
        if hasattr(obj, "actor") and obj.actor:
            return getattr(obj.actor, "real_name", None) or getattr(obj.actor, "username", None)
        return None


class LogBatchListOut(BaseSchema):
    id: int
    original_content: str
    total_cases: int
    success_count: int
    fail_count: int
    has_expense_split: bool
    expense_amount: Decimal | None = None
    expense_category_name: str | None = None
    has_income_split: bool = False
    income_amount: Decimal | None = None
    income_category_name: str | None = None
    actor_name: str | None = None
    created_at: datetime


__all__ = [
    "LogBatchPreviewItem",
    "LogBatchPreviewOut",
    "LogBatchCreateIn",
    "LogBatchOut",
    "LogBatchListOut",
]
