"""客户收款看板 API"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from django.http import HttpRequest, HttpResponse
from ninja import Router

from apps.core.security.auth import JWTOrSessionAuth
from apps.finance.schemas.collection_schemas import (
    CaseDetailResponse,
    CaseDetailOut,
    CollectionFilterParams,
    CollectionResponse,
    ContractSummaryOut,
    ExportParams,
    PaymentDetailResponse,
    PaymentRecordOut,
)
from apps.finance.services.collection_service import CollectionService

if TYPE_CHECKING:
    from apps.users.models import User

router = Router(tags=["客户收款看板"])


@router.get("/contracts", response=CollectionResponse, auth=JWTOrSessionAuth())
def list_contracts(
    request: HttpRequest,
    filters: CollectionFilterParams = CollectionFilterParams(),  # type: ignore[call-arg]
) -> dict:
    """查询合同层收款汇总"""
    service = CollectionService()
    contracts, total, agg = service.get_contracts(
        client_id=filters.client_id,
        contract_id=filters.contract_id,
        case_id=filters.case_id,
        case_name=filters.case_name,
        fee_mode=filters.fee_mode,
        start_date=filters.start_date,
        end_date=filters.end_date,
        page=filters.page,
        page_size=filters.page_size,
    )

    return {
        "total_expected": agg.total_expected,
        "total_received": agg.total_received,
        "total_balance": agg.total_balance,
        "overall_rate": agg.overall_rate,
        "contracts": [
            ContractSummaryOut(**c) for c in contracts
        ],
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
    }


@router.get("/cases/{contract_id}", response=CaseDetailResponse, auth=JWTOrSessionAuth())
def list_case_details(
    request: HttpRequest,
    contract_id: int,
    case_name: str | None = None,
) -> dict:
    """查询某合同下的案件收款明细"""
    service = CollectionService()
    cases, total = service.get_case_details(contract_id, case_name=case_name)

    return {
        "cases": [CaseDetailOut(**c) for c in cases],
        "total": total,
    }


@router.get("/records", response=PaymentDetailResponse, auth=JWTOrSessionAuth())
def list_payment_records(
    request: HttpRequest,
    contract_id: int | None = None,
    case_id: int | None = None,
    client_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """查询逐笔收款记录"""
    from datetime import date as date_type

    service = CollectionService()
    records, total = service.get_payment_records(
        contract_id=contract_id,
        case_id=case_id,
        client_id=client_id,
        start_date=date_type.fromisoformat(start_date) if start_date else None,
        end_date=date_type.fromisoformat(end_date) if end_date else None,
        page=page,
        page_size=page_size,
    )

    return {
        "records": [PaymentRecordOut(**r) for r in records],
        "total": total,
    }


@router.get("/export", auth=JWTOrSessionAuth())
def export_collection(
    request: HttpRequest,
    level: str = "contract",
    client_id: int | None = None,
    contract_id: int | None = None,
    case_id: int | None = None,
    case_name: str | None = None,
    fee_mode: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> HttpResponse:
    """导出收款数据为 Excel"""
    from datetime import date as date_type

    try:
        import openpyxl
    except ImportError:
        return HttpResponse("openpyxl 未安装", status=500)

    service = CollectionService()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "收款看板"

    s_date = date_type.fromisoformat(start_date) if start_date else None
    e_date = date_type.fromisoformat(end_date) if end_date else None

    if level == "contract":
        ws.append(["合同名称", "客户名称", "收费模式", "合同应收", "已收金额", "未收余额", "回款率", "案件数"])
        contracts, _, _ = service.get_contracts(
            client_id=client_id, contract_id=contract_id, case_id=case_id,
            case_name=case_name, fee_mode=fee_mode,
            start_date=s_date, end_date=e_date, page=1, page_size=10000,
        )
        for c in contracts:
            ws.append([
                c["contract_name"], c["client_name"], c["fee_mode_display"],
                float(c["fixed_amount"]) if c["fixed_amount"] else "",
                float(c["total_received"]), float(c["balance"]),
                f"{c['received_rate']:.1%}", c["case_count"],
            ])

    elif level == "case" and contract_id:
        ws.append(["案件名称", "案件状态", "已收律师费", "总收入", "总支出", "净收入", "收款笔数"])
        cases, _ = service.get_case_details(contract_id, case_name=case_name)
        for c in cases:
            ws.append([
                c["case_name"], c["case_status"],
                float(c["attorney_fee_received"]), float(c["case_income"]),
                float(c["case_expense"]), float(c["net_income"]),
                c["payment_count"],
            ])

    else:
        ws.append(["收款日期", "来源", "方向", "金额", "用途", "合同名称", "案件名称", "备注"])
        records, _ = service.get_payment_records(
            contract_id=contract_id, case_id=case_id, client_id=client_id,
            start_date=s_date, end_date=e_date, page=1, page_size=10000,
        )
        for r in records:
            ws.append([
                r["received_date"], r["source"], r["direction"],
                float(r["amount"]), r["purpose_display"],
                r["contract_name"], r["case_name"], r["note"],
            ])

    # 自适应列宽
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="collection_report.xlsx"'
    return response
