"""客户收款看板 API Schema."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from ninja import Field, Schema


class CollectionFilterParams(Schema):
    """收款看板筛选参数"""

    client_id: int | None = Field(None, description="客户ID")
    contract_id: int | None = Field(None, description="合同ID")
    case_id: int | None = Field(None, description="案件ID")
    case_name: str | None = Field(None, description="案件名称（模糊匹配）")
    fee_mode: str | None = Field(None, description="收费模式: FIXED/SEMI_RISK/FULL_RISK/CUSTOM")
    start_date: date | None = Field(None, description="收款开始日期")
    end_date: date | None = Field(None, description="收款结束日期")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页条数")


class ContractSummaryOut(Schema):
    """合同层汇总"""

    contract_id: int
    contract_name: str
    client_name: str
    fee_mode: str
    fee_mode_display: str
    fixed_amount: Decimal | None = None
    total_received: Decimal
    balance: Decimal
    case_count: int
    received_rate: float  # 0.0 ~ 1.0


class CaseDetailOut(Schema):
    """案件层明细"""

    case_id: int
    case_name: str
    case_status: str
    attorney_fee_received: Decimal  # 本案已收律师费
    case_income: Decimal  # 本案总收入
    case_expense: Decimal  # 本案总支出
    net_income: Decimal  # 净收入
    payment_count: int  # 收款记录数


class PaymentRecordOut(Schema):
    """逐笔收款记录"""

    id: int
    source: str = Field(..., description="来源表: contract_payment / case_payment_record")
    direction: str = Field("income", description="收入/支出")
    amount: Decimal
    purpose: str = ""
    purpose_display: str = ""
    received_date: str  # ISO date
    contract_name: str = ""
    case_name: str = ""
    client_name: str = ""
    note: str = ""


class CollectionResponse(Schema):
    """收款看板响应"""

    # 摘要
    total_expected: Decimal
    total_received: Decimal
    total_balance: Decimal
    overall_rate: float
    # 合同层列表（含展开的案件）
    contracts: list[ContractSummaryOut]
    # 分页
    total: int
    page: int
    page_size: int


class CaseDetailResponse(Schema):
    """案件明细响应（合同展开后查询）"""

    cases: list[CaseDetailOut]
    total: int


class PaymentDetailResponse(Schema):
    """收款明细响应（案件展开后查询）"""

    records: list[PaymentRecordOut]
    total: int


class ExportParams(Schema):
    """导出参数"""

    level: Literal["contract", "case", "detail"] = Field("contract", description="导出层级")
    fields: list[str] = Field(default_factory=list, description="导出字段列表")
    # 继承筛选参数
    client_id: int | None = None
    contract_id: int | None = None
    case_id: int | None = None
    case_name: str | None = None
    fee_mode: str | None = None
    start_date: date | None = None
    end_date: date | None = None
