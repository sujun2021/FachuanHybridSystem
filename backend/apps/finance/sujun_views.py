"""sujun 自定义功能模块视图"""

from __future__ import annotations

from datetime import date as date_type

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from apps.cases.models import CasePaymentRecord, PaymentDirection
from apps.finance.services.collection_service import CollectionService


@staff_member_required
def sujun_payments(request: HttpRequest) -> HttpResponse:
    """案件收支记录列表 — 支持筛选"""
    from django.core.paginator import Paginator

    # 筛选
    direction = request.GET.get("direction")
    purpose = request.GET.get("purpose")
    case_name = request.GET.get("case_name")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    qs = CasePaymentRecord.objects.select_related("case", "case_log").order_by("-date", "-created_at")

    if direction:
        qs = qs.filter(direction=direction)
    if purpose:
        qs = qs.filter(purpose=purpose)
    if case_name:
        from django.db.models import Q
        qs = qs.filter(Q(case__name__icontains=case_name) | Q(case__case_numbers__number__icontains=case_name))
    if start_date:
        qs = qs.filter(date__gte=date_type.fromisoformat(start_date))
    if end_date:
        qs = qs.filter(date__lte=date_type.fromisoformat(end_date))

    paginator = Paginator(qs, 30)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)

    # 汇总
    from django.db.models import Sum
    income_total = qs.filter(direction=PaymentDirection.INCOME).aggregate(s=Sum("amount"))["s"] or 0
    expense_total = qs.filter(direction=PaymentDirection.EXPENSE).aggregate(s=Sum("amount"))["s"] or 0

    return render(request, "sujun/payments.html", {
        "page_obj": page_obj,
        "income_total": income_total,
        "expense_total": expense_total,
        "net_balance": (income_total or 0) - (expense_total or 0),
        "filters": {
            "direction": direction or "",
            "purpose": purpose or "",
            "case_name": case_name or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
    })


@staff_member_required
def case_autocomplete_api(request: HttpRequest) -> JsonResponse:
    """案件名称模糊搜索 AJAX"""
    q = request.GET.get("q", "").strip()
    if len(q) < 1:
        return JsonResponse({"results": []})
    from apps.cases.models import Case
    from django.db.models import Q
    cases = Case.objects.filter(
        Q(name__icontains=q) | Q(case_numbers__number__icontains=q)
    )[:20].values("id", "name")
    return JsonResponse({"results": [{"id": c["id"], "text": c["name"]} for c in cases]})


@staff_member_required
def sujun_dashboard(request: HttpRequest) -> HttpResponse:
    """sujun 功能主页 — 财务管理 + 收支概览"""
    service = CollectionService()
    contracts, _, agg = service.get_contracts(page=1, page_size=10)

    # 最近 10 条收支记录
    recent_records = CasePaymentRecord.objects.select_related("case", "case_log").order_by(
        "-date", "-created_at"
    )[:10]

    return render(request, "sujun/dashboard.html", {
        "agg": agg,
        "contracts": contracts,
        "recent_records": [
            {
                "id": r.id,
                "date": r.date.isoformat(),
                "direction": r.direction,
                "direction_label": "收入" if r.direction == "income" else "支出",
                "amount": float(r.amount or 0),
                "purpose": r.get_purpose_display() if r.purpose else "-",
                "case_name": r.case.name if r.case else "-",
                "payment_method": r.get_payment_method_display() if r.payment_method else "-",
                "note": r.note or "",
            }
            for r in recent_records
        ],
    })
