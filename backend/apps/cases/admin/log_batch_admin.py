from __future__ import annotations

from django.contrib import admin
from django.http import HttpRequest

from apps.cases.admin.base_admin import BaseModelAdmin, BaseTabularInline
from apps.cases.models import CaseLog, CaseLogBatch


class CaseLogInline(BaseTabularInline):
    model = CaseLog
    extra = 0
    fields = ("case", "content", "reminder_type", "reminder_time", "is_split_child", "split_count")
    readonly_fields = ("created_at", "is_split_child", "split_count")
    show_change_link = True


@admin.register(CaseLogBatch)
class CaseLogBatchAdmin(BaseModelAdmin):
    list_display = ("id", "actor", "total_cases", "success_count", "fail_count", "has_expense_split", "expense_amount", "has_income_split", "income_amount", "created_at")
    list_select_related = ("actor", "expense_category", "income_category")
    list_filter = ("has_expense_split", "has_income_split", "created_at")
    search_fields = ("original_content",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "success_count", "fail_count", "error_message")
    inlines = (CaseLogInline,)
    fieldsets = (
        (None, {
            "fields": ("actor", "original_content", "case_ids")
        }),
        ("提醒设置", {
            "fields": ("reminder_type", "reminder_time"),
            "classes": ("collapse",)
        }),
        ("费用分摊", {
            "fields": ("has_expense_split", "expense_amount", "expense_category", "expense_split_count", "expense_per_case", "expense_record_date"),
            "classes": ("collapse",)
        }),
        ("收入分摊", {
            "fields": ("has_income_split", "income_amount", "income_category", "income_split_count", "income_per_case", "income_record_date"),
            "classes": ("collapse",)
        }),
        ("执行结果", {
            "fields": ("total_cases", "success_count", "fail_count", "error_message"),
            "classes": ("collapse",)
        }),
    )
