"""sujun 自定义功能模块视图"""

from __future__ import annotations

import io
from datetime import date as date_type

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from apps.cases.models import Case, CasePaymentRecord, PaymentDirection
from apps.finance.services.collection_service import CollectionService


# ── SQL 注入防护白名单 ──
_SAFE_CASE_FIELDS = frozenset({
    "name", "status", "start_date", "cause_of_action", "target_amount",
    "case_type", "current_stage", "remarks", "created_at",
})


@staff_member_required
def sujun_cases_view(request: HttpRequest) -> HttpResponse:
    """案件全景一览 — 套案管理，多维度筛选 + 统计"""
    from django.core.paginator import Paginator

    status = request.GET.get("status", "")
    case_type = request.GET.get("case_type", "")
    year = request.GET.get("year", "")
    party_name = request.GET.get("party_name", "")
    case_name = request.GET.get("case_name", "")
    case_id = request.GET.get("case_id", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    qs = (
        Case.objects.select_related("contract")
        .prefetch_related("case_numbers", "parties__client", "assignments__lawyer")
        .order_by("-start_date")
    )

    if status:
        qs = qs.filter(status=status)
    if case_type:
        qs = qs.filter(case_type=case_type)
    if year:
        qs = qs.filter(start_date__year=int(year))
    if case_name:
        qs = qs.filter(
            Q(name__icontains=case_name) | Q(case_numbers__number__icontains=case_name)
        ).distinct()
    if case_id:
        qs = qs.filter(id=int(case_id))
    if party_name:
        qs = qs.filter(parties__client__name__icontains=party_name).distinct()
    if start_date:
        qs = qs.filter(start_date__gte=date_type.fromisoformat(start_date))
    if end_date:
        qs = qs.filter(start_date__lte=date_type.fromisoformat(end_date))

    total = qs.count()
    paginator = Paginator(qs, 25)
    page_num = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_num)

    rows = []
    for case in page_obj:
        parties = list(case.parties.all())
        plaintiff = ""
        defendant = ""
        for p in parties:
            name_val = getattr(p.client, "name", "") if p.client else ""
            ls = (p.legal_status or "") if hasattr(p, "legal_status") else ""
            if ls in ("plaintiff",):
                plaintiff = str(name_val or "")
            elif ls in ("defendant",):
                defendant = str(name_val or "")

        case_nums = [n.number for n in list(case.case_numbers.all()) if n.number]

        rows.append({
            "id": case.id,
            "name": case.name,
            "status": case.get_status_display(),
            "start_date": case.start_date.isoformat() if case.start_date else "",
            "cause_of_action": case.cause_of_action or "",
            "target_amount": float(case.target_amount or 0),
            "case_type": case.get_case_type_display(),
            "current_stage": case.get_current_stage_display() if case.current_stage else "",
            "plaintiff": plaintiff,
            "defendant": defendant,
            "case_numbers": ", ".join(case_nums),
            "contract_name": case.contract.name if case.contract else "",
        })

    return render(request, "sujun/cases.html", {
        "page_obj": page_obj,
        "rows": rows,
        "total": total,
        "years": ["2026", "2025", "2024", "2023", "2022", "2021", "2020"],
        "filters": dict(status=status, case_type=case_type, year=year,
                       party_name=party_name, case_name=case_name,
                       start_date=start_date, end_date=end_date),
    })


@staff_member_required
def sujun_cases_export(request: HttpRequest) -> HttpResponse:
    """导出案件列表为 .xlsx"""
    try:
        import openpyxl
    except ImportError:
        return HttpResponse("openpyxl 未安装", status=500)

    # 复用筛选
    status = request.GET.get("status", "")
    case_type = request.GET.get("case_type", "")
    year = request.GET.get("year", "")
    party_name = request.GET.get("party_name", "")
    case_name = request.GET.get("case_name", "")
    case_id = request.GET.get("case_id", "")
    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    qs = (
        Case.objects.select_related("contract")
        .prefetch_related("case_numbers", "parties__client")
        .order_by("-start_date")
    )
    if status: qs = qs.filter(status=status)
    if case_type: qs = qs.filter(case_type=case_type)
    if year: qs = qs.filter(start_date__year=int(year))
    if case_name: qs = qs.filter(Q(name__icontains=case_name) | Q(case_numbers__number__icontains=case_name)).distinct()
    if case_id: qs = qs.filter(id=int(case_id))
    if party_name: qs = qs.filter(parties__client__name__icontains=party_name).distinct()
    if start_date: qs = qs.filter(start_date__gte=date_type.fromisoformat(start_date))
    if end_date: qs = qs.filter(start_date__lte=date_type.fromisoformat(end_date))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "案件一览"
    ws.append(["案件名称","状态","收案日期","案由","标的额","类型","阶段","原告","被告","案号","合同"])

    for case in qs[:2000]:
        parties = list(case.parties.all())
        pl = ""; df = ""
        for p in parties:
            nm = str(getattr(p.client, "name", "") if p.client else "")
            ls = (p.legal_status or "") if hasattr(p, "legal_status") else ""
            if ls == "plaintiff": pl = nm
            elif ls == "defendant": df = nm
        cns = ", ".join(n.number for n in case.case_numbers.all() if n.number)
        ws.append([
            case.name, case.get_status_display(), str(case.start_date),
            case.cause_of_action or "", float(case.target_amount or 0),
            case.get_case_type_display(),
            case.get_current_stage_display() if case.current_stage else "",
            pl, df, cns,
            case.contract.name if case.contract else "",
        ])

    for col in ws.columns:
        mx = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(mx + 2, 50)

    out = io.BytesIO()
    wb.save(out); out.seek(0)
    resp = HttpResponse(out.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="cases_export.xlsx"'
    return resp


# ── 已有视图 ──

@staff_member_required
def sujun_payments(request: HttpRequest) -> HttpResponse:
    from django.core.paginator import Paginator
    direction = request.GET.get("direction")
    purpose = request.GET.get("purpose")
    case_name = request.GET.get("case_name")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    qs = CasePaymentRecord.objects.select_related("case", "case_log").order_by("-date", "-created_at")
    if direction: qs = qs.filter(direction=direction)
    if purpose: qs = qs.filter(purpose=purpose)
    if case_name: qs = qs.filter(Q(case__name__icontains=case_name) | Q(case__case_numbers__number__icontains=case_name))
    if start_date: qs = qs.filter(date__gte=date_type.fromisoformat(start_date))
    if end_date: qs = qs.filter(date__lte=date_type.fromisoformat(end_date))
    paginator = Paginator(qs, 30)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    income_total = qs.filter(direction=PaymentDirection.INCOME).aggregate(s=Sum("amount"))["s"] or 0
    expense_total = qs.filter(direction=PaymentDirection.EXPENSE).aggregate(s=Sum("amount"))["s"] or 0
    return render(request, "sujun/payments.html", {
        "page_obj": page_obj, "income_total": income_total, "expense_total": expense_total,
        "net_balance": (income_total or 0) - (expense_total or 0),
        "filters": dict(direction=direction or "", purpose=purpose or "",
                       case_name=case_name or "", start_date=start_date or "", end_date=end_date or ""),
    })


@staff_member_required
def case_autocomplete_api(request: HttpRequest) -> JsonResponse:
    q = request.GET.get("q", "").strip()
    if len(q) < 1: return JsonResponse({"results": []})
    cases = Case.objects.filter(Q(name__icontains=q) | Q(case_numbers__number__icontains=q))[:20].values("id", "name")
    return JsonResponse({"results": [{"id": c["id"], "text": c["name"]} for c in cases]})


@staff_member_required
def sujun_dashboard(request: HttpRequest) -> HttpResponse:
    service = CollectionService()
    contracts, _, agg = service.get_contracts(page=1, page_size=10)
    recent = CasePaymentRecord.objects.select_related("case", "case_log").order_by("-date", "-created_at")[:10]
    return render(request, "sujun/dashboard.html", {
        "agg": agg, "contracts": contracts,
        "recent_records": [{"id": r.id, "date": r.date.isoformat(),
            "direction": r.direction, "direction_label": "收入" if r.direction == "income" else "支出",
            "amount": float(r.amount or 0), "purpose": r.get_purpose_display() if r.purpose else "-",
            "case_name": r.case.name if r.case else "-",
            "payment_method": r.get_payment_method_display() if r.payment_method else "-",
            "note": r.note or ""} for r in recent],
    })
