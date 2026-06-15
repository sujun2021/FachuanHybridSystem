"""客户收款看板服务 — 聚合 ContractPayment + CasePaymentRecord 数据"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

from django.db.models import F, OuterRef, Q, Subquery, Sum, Prefetch
from django.utils import timezone

from apps.cases.models import Case, CasePaymentRecord, PaymentDirection
from apps.client.models import Client
from apps.contracts.models import Contract, ContractPayment, ClientPaymentRecord
from apps.contracts.models.contract import FeeMode


@dataclass
class CollectionAggregation:
    """收款聚合结果"""

    total_expected: Decimal = Decimal("0")
    total_received: Decimal = Decimal("0")
    total_balance: Decimal = Decimal("0")
    overall_rate: float = 0.0


class CollectionService:
    """客户收款看板数据服务"""

    _INCOME_PURPOSES: ClassVar[set[str]] = {
        "attorney_fee",
        "counterparty_payment",
        "enforcement_recovery",
        "settlement",
        "court_fee_refund",
    }

    def get_contracts(
        self,
        *,
        client_id: int | None = None,
        contract_id: int | None = None,
        case_id: int | None = None,
        case_name: str | None = None,
        fee_mode: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, CollectionAggregation]:
        """查询合同层汇总列表 + 全局聚合"""

        # 基础过滤
        contract_filter = Q()
        if contract_id:
            contract_filter &= Q(id=contract_id)
        if client_id:
            from apps.contracts.models.party import ContractParty
            contract_ids = ContractParty.objects.filter(
                client_id=client_id, role="PRINCIPAL"
            ).values_list("contract_id", flat=True)
            contract_filter &= Q(id__in=contract_ids)
        if fee_mode:
            contract_filter &= Q(fee_mode=fee_mode)
        if case_id or case_name:
            case_filter = Q()
            if case_id:
                case_filter &= Q(id=case_id)
            if case_name:
                case_filter &= Q(name__icontains=case_name)
            contract_ids_from_case = Case.objects.filter(case_filter).values_list("contract_id", flat=True).distinct()
            contract_filter &= Q(id__in=contract_ids_from_case)

        # 收款过滤 — 如果指定了日期，只统计该日期范围内的合同有收款记录的
        payment_date_filter = Q()
        if start_date:
            payment_date_filter &= Q(received_at__gte=start_date)
        if end_date:
            payment_date_filter &= Q(received_at__lte=end_date)

        # 查询合同 + prefetch 收款记录
        contracts_qs = (
            Contract.objects.filter(contract_filter)
            .select_related()
            .prefetch_related(
                Prefetch(
                    "payments",
                    queryset=ContractPayment.objects.filter(payment_date_filter).order_by("-received_at"),
                ),
                "contract_parties__client",
                "cases",
            )
            .order_by("-specified_date")
        )

        total = contracts_qs.count()
        offset = (page - 1) * page_size
        contracts = contracts_qs[offset : offset + page_size]

        results: list[dict[str, Any]] = []
        agg = CollectionAggregation()

        for contract in contracts:
            # 合同已收 = SUM(ContractPayment.amount)
            received = sum((p.amount for p in contract.payments.all()), Decimal("0"))

            # 合同应收
            expected = contract.fixed_amount or Decimal("0")

            # 处理风险收费
            fee_mode_label = contract.get_fee_mode_display()
            if contract.fee_mode in (FeeMode.FULL_RISK, FeeMode.CUSTOM):
                # 风险收费或无固定金额：应收用一个占位
                expected_display = None
            else:
                expected_display = expected

            balance = expected - received if expected_display is not None else Decimal("0")
            rate = float(received / expected) if expected > 0 and expected_display is not None else 0.0

            # 获取客户名称
            client_name = ""
            parties = list(contract.contract_parties.all())
            for p in parties:
                if hasattr(p, "client") and p.client:
                    client_name = getattr(p.client, "name", "")
                    break

            results.append({
                "contract_id": contract.id,
                "contract_name": contract.name,
                "client_name": client_name,
                "fee_mode": contract.fee_mode,
                "fee_mode_display": fee_mode_label,
                "fixed_amount": expected_display,
                "total_received": received,
                "balance": balance,
                "case_count": contract.cases.count(),
                "received_rate": round(rate, 4),
            })

            if expected_display is not None:
                agg.total_expected += expected
            agg.total_received += received
            agg.total_balance += balance

        if agg.total_expected > 0:
            agg.overall_rate = round(float(agg.total_received / agg.total_expected), 4)

        return results, total, agg

    def get_case_details(
        self,
        contract_id: int,
        *,
        case_name: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """查询某合同下的案件收款明细"""

        case_filter = Q(contract_id=contract_id)
        if case_name:
            case_filter &= Q(name__icontains=case_name)

        cases = (
            Case.objects.filter(case_filter)
            .prefetch_related(
                Prefetch(
                    "payment_records",
                    queryset=CasePaymentRecord.objects.order_by("-date"),
                )
            )
            .order_by("-start_date")
        )

        total = cases.count()
        results: list[dict[str, Any]] = []

        for case in cases:
            records = list(case.payment_records.all())
            attorney_fee = sum(
                (r.amount for r in records if r.direction == PaymentDirection.INCOME and r.purpose == "attorney_fee"),
                Decimal("0"),
            )
            income = sum(
                (r.amount for r in records if r.direction == PaymentDirection.INCOME),
                Decimal("0"),
            )
            expense = sum(
                (r.amount for r in records if r.direction == PaymentDirection.EXPENSE),
                Decimal("0"),
            )

            results.append({
                "case_id": case.id,
                "case_name": case.name,
                "case_status": case.get_status_display() if hasattr(case, "get_status_display") else str(case.status),
                "attorney_fee_received": attorney_fee,
                "case_income": income,
                "case_expense": expense,
                "net_income": income - expense,
                "payment_count": len([r for r in records if r.direction == PaymentDirection.INCOME]),
            })

        return results, total

    def get_payment_records(
        self,
        *,
        contract_id: int | None = None,
        case_id: int | None = None,
        client_id: int | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """查询逐笔收款记录"""

        records: list[dict[str, Any]] = []

        # 1. ContractPayment 表
        cp_filter = Q()
        if contract_id:
            cp_filter &= Q(contract_id=contract_id)
        if case_id:
            # ContractPayment 无 case FK，通过 Contract→Case 间接
            cp_filter &= Q(contract__cases__id=case_id)
        if client_id:
            from apps.contracts.models.party import ContractParty
            contract_ids = ContractParty.objects.filter(
                client_id=client_id, role="PRINCIPAL"
            ).values_list("contract_id", flat=True)
            cp_filter &= Q(contract_id__in=contract_ids)
        if start_date:
            cp_filter &= Q(received_at__gte=start_date)
        if end_date:
            cp_filter &= Q(received_at__lte=end_date)

        cp_qs = (
            ContractPayment.objects.filter(cp_filter)
            .select_related("contract")
            .order_by("-received_at")
        )
        for p in cp_qs:
            records.append({
                "id": p.id,
                "source": "contract_payment",
                "direction": "income",
                "amount": p.amount,
                "purpose": "attorney_fee",
                "purpose_display": "律师费",
                "received_date": p.received_at.isoformat(),
                "contract_name": p.contract.name,
                "case_name": "",
                "client_name": "",
                "note": p.note or "",
            })

        # 2. CasePaymentRecord 表
        cpr_filter = Q(direction=PaymentDirection.INCOME)
        if case_id:
            cpr_filter &= Q(case_id=case_id)
        if contract_id:
            cpr_filter &= Q(case__contract_id=contract_id)
        if start_date:
            cpr_filter &= Q(date__gte=start_date)
        if end_date:
            cpr_filter &= Q(date__lte=end_date)

        cpr_qs = (
            CasePaymentRecord.objects.filter(cpr_filter)
            .select_related("case__contract")
            .order_by("-date")
        )

        for r in cpr_qs:
            records.append({
                "id": r.id,
                "source": "case_payment_record",
                "direction": r.direction,
                "amount": r.amount or Decimal("0"),
                "purpose": r.purpose,
                "purpose_display": r.get_purpose_display() if r.purpose else "",
                "received_date": r.date.isoformat(),
                "contract_name": getattr(r.case, "contract", None) and r.case.contract.name or "",
                "case_name": r.case.name if r.case else "",
                "client_name": "",
                "note": r.note or "",
            })

        # 合并排序
        records.sort(key=lambda x: x["received_date"], reverse=True)

        total = len(records)
        offset = (page - 1) * page_size
        return records[offset : offset + page_size], total
