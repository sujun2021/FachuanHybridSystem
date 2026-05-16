"""收支记录 API"""

from typing import Any

from django.http import HttpRequest
from ninja import Router

from apps.cases.schemas import (
    PaymentRecordCategoryCreate,
    PaymentRecordCategoryOut,
    PaymentRecordIn,
    PaymentRecordOut,
    PaymentRecordUpdate,
    PaymentSummaryOut,
)
from apps.cases.services import PaymentRecordService
from apps.core.api import AuthBearer, request_user

router = Router(tags=["收支记录"])


@router.get("/case/{case_id}/payments", response=list[PaymentRecordOut])
def list_case_payments(request: HttpRequest, case_id: int) -> list[PaymentRecordOut]:
    """获取案件的所有收支记录"""
    user = request_user(request)
    records = PaymentRecordService.get_case_payment_records(case_id, user)
    return records


@router.get("/case/{case_id}/payments/summary", response=PaymentSummaryOut)
def get_payment_summary(request: HttpRequest, case_id: int) -> dict[str, Any]:
    """获取案件收支汇总"""
    summary = PaymentRecordService.get_payment_summary(case_id)
    records = PaymentRecordService.get_case_payment_records(case_id)
    income_records = [r for r in records if r.is_income]
    expense_records = [r for r in records if not r.is_income]
    return {
        **summary,
        "income_records": income_records,
        "expense_records": expense_records,
    }


@router.post("/payments", response=PaymentRecordOut)
def create_payment(request: HttpRequest, data: PaymentRecordIn) -> PaymentRecordOut:
    """创建收支记录"""
    user = request_user(request)
    record = PaymentRecordService.create_payment_record(data.model_dump(), user)
    return record


@router.put("/payments/{record_id}", response=PaymentRecordOut)
def update_payment(request: HttpRequest, record_id: int, data: PaymentRecordUpdate) -> PaymentRecordOut:
    """更新收支记录"""
    user = request_user(request)
    record = PaymentRecordService.update_payment_record(record_id, data.model_dump(exclude_none=True), user)
    return record


@router.delete("/payments/{record_id}")
def delete_payment(request: HttpRequest, record_id: int) -> dict[str, bool]:
    """删除收支记录"""
    user = request_user(request)
    return PaymentRecordService.delete_payment_record(record_id, user)


@router.get("/payment-categories", response=list[PaymentRecordCategoryOut])
def list_categories(request: HttpRequest, is_income: bool | None = None) -> list[PaymentRecordCategoryOut]:
    """获取款项用途列表"""
    categories = PaymentRecordService.list_categories(is_income)
    return categories


@router.post("/payment-categories", response=PaymentRecordCategoryOut)
def create_category(request: HttpRequest, data: PaymentRecordCategoryCreate) -> PaymentRecordCategoryOut:
    """创建款项用途"""
    user = request_user(request)
    category = PaymentRecordService.create_category(data.model_dump(), user)
    return category


@router.delete("/payment-categories/{category_id}")
def delete_category(request: HttpRequest, category_id: int) -> dict[str, bool]:
    """删除款项用途"""
    user = request_user(request)
    return PaymentRecordService.delete_category(category_id, user)


@router.post("/payment-categories/init")
def init_categories(request: HttpRequest) -> dict[str, str]:
    """初始化系统内置款项用途"""
    PaymentRecordService.ensure_builtin_categories()
    return {"status": "ok"}


__all__ = ["router"]
