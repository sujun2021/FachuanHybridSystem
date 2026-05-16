"""批量日志创建服务"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from apps.cases.models import Case, CaseLog, CaseLogBatch, CasePaymentRecord, PaymentRecordCategory
from apps.cases.services.payment.payment_service import ContentSplitService
from apps.core.exceptions import NotFoundError, ValidationException

logger = logging.getLogger(__name__)


class LogBatchService:
    """批量日志服务"""

    @staticmethod
    def preview_batch_log(
        original_content: str,
        case_ids: list[int],
        expense_amount: Decimal | None = None,
        expense_split_count: int | None = None,
        income_amount: Decimal | None = None,
        income_split_count: int | None = None,
    ) -> dict[str, Any]:
        """预览批量日志分拆效果"""
        if not case_ids:
            raise ValidationException(_("请选择至少一个案件"))

        if not original_content or not original_content.strip():
            raise ValidationException(_("日志内容不能为空"))

        count = len(case_ids)
        exp_split_count = expense_split_count or count
        inc_split_count = income_split_count or count

        preview = ContentSplitService.generate_preview(
            original_content,
            case_ids,
            expense_amount,
            exp_split_count,
        )

        expense_per_case = None
        if expense_amount and exp_split_count > 0:
            expense_per_case = expense_amount / Decimal(str(exp_split_count))

        income_per_case = None
        if income_amount and inc_split_count > 0:
            income_per_case = income_amount / Decimal(str(inc_split_count))

        return {
            "total_count": count,
            "logs": preview,
            "expense_per_case": expense_per_case,
            "has_expense_split": expense_amount is not None,
            "income_per_case": income_per_case,
            "has_income_split": income_amount is not None,
            "original_content": original_content,
        }

    @staticmethod
    @transaction.atomic
    def create_batch_log(
        original_content: str,
        case_ids: list[int],
        user: Any,
        reminder_type: str | None = None,
        reminder_time: Any | None = None,
        expense_amount: Decimal | None = None,
        expense_category_id: int | None = None,
        expense_split_count: int | None = None,
        expense_record_date: Any | None = None,
        expense_payment_method: str | None = None,
        expense_description: str | None = None,
        income_amount: Decimal | None = None,
        income_category_id: int | None = None,
        income_split_count: int | None = None,
        income_record_date: Any | None = None,
        income_payment_method: str | None = None,
        income_description: str | None = None,
    ) -> CaseLogBatch:
        """创建批量日志"""
        if not case_ids:
            raise ValidationException(_("请选择至少一个案件"))

        if not original_content or not original_content.strip():
            raise ValidationException(_("日志内容不能为空"))

        valid_case_ids = list(Case.objects.filter(id__in=case_ids).values_list("id", flat=True))
        if len(valid_case_ids) != len(case_ids):
            invalid_ids = set(case_ids) - set(valid_case_ids)
            raise ValidationException(_(f"以下案件ID不存在: {invalid_ids}"))

        count = len(valid_case_ids)
        exp_split_count = expense_split_count or count
        inc_split_count = income_split_count or count

        expense_category = None
        if expense_amount and expense_category_id:
            try:
                expense_category = PaymentRecordCategory.objects.get(id=expense_category_id)
            except PaymentRecordCategory.DoesNotExist:
                raise NotFoundError(_("费用类型不存在"))

        income_category = None
        if income_amount and income_category_id:
            try:
                income_category = PaymentRecordCategory.objects.get(id=income_category_id)
            except PaymentRecordCategory.DoesNotExist:
                raise NotFoundError(_("收入类型不存在"))

        expense_per_case = None
        if expense_amount and exp_split_count > 0:
            expense_per_case = expense_amount / Decimal(str(exp_split_count))

        income_per_case = None
        if income_amount and inc_split_count > 0:
            income_per_case = income_amount / Decimal(str(inc_split_count))

        batch = CaseLogBatch.objects.create(
            actor=user,
            original_content=original_content,
            case_ids=valid_case_ids,
            reminder_type=reminder_type,
            reminder_time=reminder_time,
            has_expense_split=bool(expense_amount and expense_category_id),
            expense_amount=expense_amount,
            expense_split_count=exp_split_count,
            expense_per_case=expense_per_case,
            expense_record_date=expense_record_date,
            expense_category=expense_category,
            has_income_split=bool(income_amount and income_category_id),
            income_amount=income_amount,
            income_split_count=inc_split_count,
            income_per_case=income_per_case,
            income_record_date=income_record_date,
            income_category=income_category,
            total_cases=count,
        )

        splits = ContentSplitService.split_content(
            original_content,
            valid_case_ids,
            expense_amount,
            exp_split_count,
        )

        success_count = 0
        fail_count = 0
        error_messages = []

        for i, split in enumerate(splits):
            try:
                case_id = split["case_id"]
                log = CaseLog.objects.create(
                    case_id=case_id,
                    content=split["content"],
                    reminder_type=reminder_type,
                    reminder_time=reminder_time,
                    batch=batch,
                    is_split_child=True,
                    split_source_id=batch.id,
                    split_count=count,
                    actor=user,
                )

                if expense_amount and expense_category_id and split["expense_amount"]:
                    CasePaymentRecord.objects.create(
                        case_id=case_id,
                        category_id=expense_category_id,
                        amount=split["expense_amount"],
                        record_date=expense_record_date or log.record_date,
                        is_income=False,
                        payment_method=expense_payment_method,
                        source_type="log_batch_split",
                        source_id=batch.id,
                        is_split=True,
                        split_count=exp_split_count,
                        has_receipt=False,
                        description=expense_description or "",
                        actor=user,
                    )

                if income_amount and income_category_id:
                    per_case_income = income_amount / Decimal(str(inc_split_count))
                    CasePaymentRecord.objects.create(
                        case_id=case_id,
                        category_id=income_category_id,
                        amount=per_case_income,
                        record_date=income_record_date or log.record_date,
                        is_income=True,
                        payment_method=income_payment_method,
                        source_type="log_batch_split",
                        source_id=batch.id,
                        is_split=True,
                        split_count=inc_split_count,
                        has_receipt=False,
                        description=income_description or "",
                        actor=user,
                    )

                success_count += 1

            except Exception as e:
                fail_count += 1
                error_msg = f"案件{split['case_id']}创建失败: {str(e)}"
                error_messages.append(error_msg)
                logger.error(error_msg)

        batch.success_count = success_count
        batch.fail_count = fail_count
        batch.error_message = "\n".join(error_messages)
        batch.save()

        return batch

    @staticmethod
    def get_batch_detail(batch_id: int) -> CaseLogBatch:
        """获取批量日志详情"""
        try:
            return CaseLogBatch.objects.select_related(
                "actor", "expense_category", "income_category"
            ).prefetch_related("logs").get(id=batch_id)
        except CaseLogBatch.DoesNotExist:
            raise NotFoundError(_("批量日志不存在"))

    @staticmethod
    def list_batches(user_id: int | None = None, limit: int = 50) -> list[CaseLogBatch]:
        """获取批量日志列表"""
        queryset = CaseLogBatch.objects.select_related(
            "actor", "expense_category", "income_category"
        ).order_by("-created_at")
        if user_id:
            queryset = queryset.filter(actor_id=user_id)
        return list(queryset[:limit])


__all__ = [
    "LogBatchService",
]
