"""案件收支记录服务"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from apps.cases.models import Case, CasePaymentRecord, PaymentRecordCategory
from apps.core.exceptions import ForbiddenError, NotFoundError, ValidationException


class PaymentRecordService:
    """收支记录服务"""

    @staticmethod
    def get_case_payment_records(
        case_id: int,
        user: Any | None = None,
        org_access: dict[str, Any] | None = None,
    ) -> list[CasePaymentRecord]:
        """获取案件的所有收支记录"""
        try:
            case = Case.objects.get(id=case_id)
        except Case.DoesNotExist:
            raise NotFoundError(_("案件不存在"))

        if user and not getattr(user, "is_authenticated", False):
            raise ForbiddenError(_("未授权访问"))

        return list(
            CasePaymentRecord.objects.filter(case_id=case_id)
            .select_related("category", "actor", "case_number")
            .order_by("-record_date", "-created_at")
        )

    @staticmethod
    def get_payment_summary(case_id: int) -> dict[str, Any]:
        """获取案件收支汇总"""
        records = CasePaymentRecord.objects.filter(case_id=case_id)

        income_records = records.filter(is_income=True)
        expense_records = records.filter(is_income=False)

        total_income = income_records.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        total_expense = expense_records.aggregate(total=Sum("amount"))["total"] or Decimal("0")

        return {
            "case_id": case_id,
            "total_income": total_income,
            "total_expense": total_expense,
            "net_amount": total_income - total_expense,
            "income_count": income_records.count(),
            "expense_count": expense_records.count(),
        }

    @staticmethod
    @transaction.atomic
    def create_payment_record(
        data: dict[str, Any],
        user: Any | None = None,
    ) -> CasePaymentRecord:
        """创建收支记录"""
        case_id = data.get("case_id")
        if not case_id:
            raise ValidationException(_("案件ID不能为空"))

        try:
            case = Case.objects.get(id=case_id)
        except Case.DoesNotExist:
            raise NotFoundError(_("案件不存在"))

        category_id = data.get("category_id")
        if not category_id:
            raise ValidationException(_("款项用途不能为空"))

        try:
            category = PaymentRecordCategory.objects.get(id=category_id)
        except PaymentRecordCategory.DoesNotExist:
            raise NotFoundError(_("款项用途不存在"))

        actor_id = getattr(user, "id", None) if user else None
        if not actor_id:
            raise ValidationException(_("操作人不能为空"))

        record = CasePaymentRecord.objects.create(
            case_id=case_id,
            category_id=category_id,
            amount=data["amount"],
            record_date=data["record_date"],
            is_income=data.get("is_income", category.is_income),
            payment_method=data.get("payment_method"),
            payer_payee_name=data.get("payer_payee_name", ""),
            case_number_id=data.get("case_number_id"),
            source_type=data.get("source_type", "manual"),
            source_id=data.get("source_id"),
            is_split=data.get("is_split", False),
            split_count=data.get("split_count", 1),
            has_receipt=data.get("has_receipt", False),
            receipt_note=data.get("receipt_note", ""),
            description=data.get("description", ""),
            actor_id=actor_id,
        )

        return record

    @staticmethod
    @transaction.atomic
    def update_payment_record(
        record_id: int,
        data: dict[str, Any],
        user: Any | None = None,
    ) -> CasePaymentRecord:
        """更新收支记录"""
        try:
            record = CasePaymentRecord.objects.get(id=record_id)
        except CasePaymentRecord.DoesNotExist:
            raise NotFoundError(_("收支记录不存在"))

        if "category_id" in data:
            category_id = data["category_id"]
            try:
                PaymentRecordCategory.objects.get(id=category_id)
            except PaymentRecordCategory.DoesNotExist:
                raise NotFoundError(_("款项用途不存在"))
            record.category_id = category_id

        for key in ["amount", "record_date", "is_income", "payment_method", "payer_payee_name", "case_number_id", "has_receipt", "receipt_note", "description"]:
            if key in data:
                setattr(record, key, data[key])

        record.save()
        return record

    @staticmethod
    @transaction.atomic
    def delete_payment_record(
        record_id: int,
        user: Any | None = None,
    ) -> dict[str, bool]:
        """删除收支记录"""
        try:
            record = CasePaymentRecord.objects.get(id=record_id)
        except CasePaymentRecord.DoesNotExist:
            raise NotFoundError(_("收支记录不存在"))

        record.delete()
        return {"success": True}

    @staticmethod
    def create_category(
        data: dict[str, Any],
        user: Any | None = None,
    ) -> PaymentRecordCategory:
        """创建款项用途"""
        name = data.get("name", "").strip()
        if not name:
            raise ValidationException(_("名称不能为空"))

        if PaymentRecordCategory.objects.filter(name=name).exists():
            raise ValidationException(_("该名称已存在"))

        return PaymentRecordCategory.objects.create(
            name=name,
            is_income=data.get("is_income", True),
            is_system=False,
            sort_order=data.get("sort_order", 99),
        )

    @staticmethod
    def list_categories(is_income: bool | None = None) -> list[PaymentRecordCategory]:
        """获取款项用途列表"""
        queryset = PaymentRecordCategory.objects.all()
        if is_income is not None:
            queryset = queryset.filter(is_income=is_income)
        return list(queryset.order_by("is_income", "sort_order", "name"))

    @staticmethod
    @transaction.atomic
    def delete_category(
        category_id: int,
        user: Any | None = None,
    ) -> dict[str, bool]:
        """删除款项用途（仅限非系统内置）"""
        try:
            category = PaymentRecordCategory.objects.get(id=category_id)
        except PaymentRecordCategory.DoesNotExist:
            raise NotFoundError(_("款项用途不存在"))

        if category.is_system:
            raise ValidationException(_("系统内置用途不能删除"))

        if category.payment_records.exists():
            raise ValidationException(_("该用途已有收支记录，不能删除"))

        category.delete()
        return {"success": True}

    @staticmethod
    def ensure_builtin_categories() -> None:
        """确保系统内置类别存在"""
        PaymentRecordCategory.ensure_builtin_categories()


class ContentSplitService:
    """内容分拆服务"""

    @staticmethod
    def split_content(
        original_content: str,
        case_ids: list[int],
        expense_amount: Decimal | None = None,
        expense_split_count: int | None = None,
    ) -> list[dict[str, Any]]:
        """分拆日志内容"""
        results = []
        count = len(case_ids)
        split_count = expense_split_count or count

        content = original_content

        if expense_amount and count > 0 and split_count > 0:
            per_case = expense_amount / Decimal(str(split_count))
            per_case_rounded = per_case.quantize(Decimal("0.01"))

            content = re.sub(
                r"([花费|共计|支出|付款])\s*[:：]?\s*(\d+(?:\.\d+)?)\s*元",
                lambda m: f"{m.group(1)}：{per_case_rounded}元/共{split_count}个案件",
                content,
            )

            content = re.sub(
                r"([花费|共计|支出|付款])\s*(\d+(?:\.\d+)?)\s*元",
                lambda m: f"{m.group(1)}：{per_case_rounded}元/共{split_count}个案件",
                content,
            )

        content = re.sub(
            r"用时\s*(\d+)\s*分钟",
            lambda m: f"用时 {int(int(m.group(1)) / split_count)} 分钟/共{split_count}个案件",
            content,
        )

        for case_id in case_ids:
            results.append({
                "case_id": case_id,
                "content": content,
                "expense_amount": expense_amount / Decimal(str(split_count)) if expense_amount and split_count > 0 else None,
            })

        return results

    @staticmethod
    def generate_preview(
        original_content: str,
        case_ids: list[int],
        expense_amount: Decimal | None = None,
        expense_split_count: int | None = None,
    ) -> list[dict[str, Any]]:
        """生成分拆预览"""
        cases = {c.id: c.name for c in Case.objects.filter(id__in=case_ids)}

        splits = ContentSplitService.split_content(
            original_content,
            case_ids,
            expense_amount,
            expense_split_count,
        )

        preview = []
        for split in splits:
            case_name = cases.get(split["case_id"], f"案件{split['case_id']}")
            preview.append({
                "case_id": split["case_id"],
                "case_name": case_name,
                "content_preview": split["content"][:200] + ("..." if len(split["content"]) > 200 else ""),
                "expense_amount": split["expense_amount"],
                "has_expense_split": expense_amount is not None,
            })

        return preview


__all__ = [
    "PaymentRecordService",
    "ContentSplitService",
]
