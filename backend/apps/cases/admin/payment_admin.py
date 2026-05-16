from __future__ import annotations

from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest

from apps.cases.admin.base_admin import BaseModelAdmin, BaseTabularInline
from apps.cases.models import CasePaymentRecord, PaymentRecordCategory


@admin.register(PaymentRecordCategory)
class PaymentRecordCategoryAdmin(BaseModelAdmin):
    list_display = ("id", "name", "is_income", "is_system", "sort_order", "created_at")
    list_filter = ("is_income", "is_system")
    search_fields = ("name",)
    ordering = ("is_income", "sort_order", "name")
    readonly_fields = ("created_at",)

    def get_readonly_fields(self, request: HttpRequest, obj: PaymentRecordCategory | None = None) -> list[str]:
        if obj and obj.is_system:
            return list(super().get_readonly_fields(request, obj)) + ["is_income", "is_system"]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj: PaymentRecordCategory | None = None) -> bool:
        if obj and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)


class CasePaymentRecordInline(BaseTabularInline):
    model = CasePaymentRecord
    extra = 0
    fields = ("category", "amount", "record_date", "is_income", "payment_method", "payer_payee_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CasePaymentRecord)
class CasePaymentRecordAdmin(BaseModelAdmin):
    list_display = ("id", "case_link", "category", "amount", "is_income", "record_date", "payment_method", "actor", "created_at")
    list_select_related = ("case", "category", "actor")
    list_filter = ("is_income", "category", "record_date", "source_type")
    search_fields = ("case__name", "category__name", "description")
    ordering = ("-record_date", "-created_at")
    readonly_fields = ("created_at", "updated_at", "actor")
    autocomplete_fields = ("case", "category", "actor", "case_number")

    @admin.display(description="案件名称", ordering="case__name")
    def case_link(self, obj: CasePaymentRecord) -> str:
        from django.urls import reverse
        from django.utils.html import format_html
        url = reverse("admin:cases_case_detail", args=[obj.case_id])
        return format_html('<a href="{}">{}</a>', url, obj.case.name if obj.case else obj.case_id)

    def save_model(
        self,
        request: HttpRequest,
        obj: CasePaymentRecord,
        form: ModelForm[CasePaymentRecord],
        change: bool,
    ) -> None:
        if not getattr(obj, "actor_id", None):
            user_id = getattr(request.user, "id", None)
            if user_id is not None:
                obj.actor_id = user_id
        super().save_model(request, obj, form, change)
