"""客户收款看板 Django 模板视图"""

from __future__ import annotations

from datetime import date as date_type

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render

from apps.finance.services.collection_service import CollectionService


@staff_member_required
def case_autocomplete_api(request: HttpRequest) -> JsonResponse:
    """案件名称模糊搜索 AJAX 接口（匹配法院短信 autocomplete 风格）"""
    q = request.GET.get("q", "").strip()
    if len(q) < 1:
        return JsonResponse({"results": []})

    from apps.cases.models import Case
    from django.db.models import Q

    cases = Case.objects.filter(
        Q(name__icontains=q) | Q(case_numbers__number__icontains=q)
    )[:20].values("id", "name")

    return JsonResponse({
        "results": [{"id": c["id"], "text": c["name"]} for c in cases]
    })


@staff_member_required
def collection_kanban_view(request: HttpRequest) -> HttpResponse:
    """客户收款看板页面"""
    service = CollectionService()

    # 筛选参数
    client_id = request.GET.get("client_id")
    contract_id = request.GET.get("contract_id")
    case_id = request.GET.get("case_id")
    case_name = request.GET.get("case_name")
    fee_mode = request.GET.get("fee_mode")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    s_date = date_type.fromisoformat(start_date) if start_date else None
    e_date = date_type.fromisoformat(end_date) if end_date else None

    contracts, total_count, agg = service.get_contracts(
        client_id=int(client_id) if client_id else None,
        contract_id=int(contract_id) if contract_id else None,
        case_id=int(case_id) if case_id else None,
        case_name=case_name if case_name else None,
        fee_mode=fee_mode if fee_mode else None,
        start_date=s_date,
        end_date=e_date,
        page=1,
        page_size=200,
    )

    # 查询案件明细（如果指定了 contract_id）
    case_details = []
    expanded_contract_id = None
    if request.GET.get("expand_contract"):
        expanded_contract_id = int(request.GET["expand_contract"])
        case_details, _ = service.get_case_details(expanded_contract_id)

    # 查询收款明细（如果指定了 contract_id + case_id）
    payment_records = []
    if request.GET.get("detail_contract") and request.GET.get("detail_case"):
        payment_records, _ = service.get_payment_records(
            contract_id=int(request.GET["detail_contract"]),
            case_id=int(request.GET["detail_case"]),
            page=1,
            page_size=200,
        )

    return render(request, "finance/collection_kanban.html", {
        "contracts": contracts,
        "total_count": total_count,
        "agg": agg,
        "case_details": case_details,
        "expanded_contract_id": expanded_contract_id,
        "payment_records": payment_records,
        "filters": {
            "client_id": client_id or "",
            "contract_id": contract_id or "",
            "case_name": case_name or "",
            "fee_mode": fee_mode or "",
            "start_date": start_date or "",
            "end_date": end_date or "",
        },
    })
