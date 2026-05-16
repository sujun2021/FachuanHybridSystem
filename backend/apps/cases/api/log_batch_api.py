"""批量日志 API"""

from typing import Any

from django.http import HttpRequest
from ninja import Router

from apps.cases.schemas import LogBatchCreateIn, LogBatchListOut, LogBatchOut, LogBatchPreviewOut
from apps.cases.services import LogBatchService
from apps.core.api import request_user

router = Router(tags=["批量日志"])


@router.post("/batch-log/preview", response=LogBatchPreviewOut)
def preview_batch_log(
    request: HttpRequest,
    data: LogBatchCreateIn,
) -> dict[str, Any]:
    """预览批量日志分拆效果"""
    preview = LogBatchService.preview_batch_log(
        original_content=data.content,
        case_ids=data.case_ids,
        expense_amount=data.expense_amount,
        expense_split_count=data.expense_split_count,
        income_amount=data.income_amount,
        income_split_count=data.income_split_count,
    )
    return preview


@router.post("/batch-log", response=LogBatchOut)
def create_batch_log(request: HttpRequest, data: LogBatchCreateIn) -> LogBatchOut:
    """创建批量日志"""
    user = request_user(request)
    batch = LogBatchService.create_batch_log(
        original_content=data.content,
        case_ids=data.case_ids,
        user=user,
        reminder_type=data.reminder_type,
        reminder_time=data.reminder_time,
        expense_amount=data.expense_amount,
        expense_category_id=data.expense_category_id,
        expense_split_count=data.expense_split_count,
        expense_record_date=data.expense_record_date,
        expense_payment_method=data.expense_payment_method,
        expense_description=data.expense_description,
        income_amount=data.income_amount,
        income_category_id=data.income_category_id,
        income_split_count=data.income_split_count,
        income_record_date=data.income_record_date,
        income_payment_method=data.income_payment_method,
        income_description=data.income_description,
    )
    return batch


@router.get("/batch-log/{batch_id}", response=LogBatchOut)
def get_batch_detail(request: HttpRequest, batch_id: int) -> LogBatchOut:
    """获取批量日志详情"""
    batch = LogBatchService.get_batch_detail(batch_id)
    return batch


@router.get("/batch-log", response=list[LogBatchListOut])
def list_batches(request: HttpRequest, limit: int = 50) -> list[LogBatchListOut]:
    """获取批量日志列表"""
    user = request_user(request)
    batches = LogBatchService.list_batches(user_id=getattr(user, "id", None), limit=limit)
    return batches


__all__ = ["router"]
