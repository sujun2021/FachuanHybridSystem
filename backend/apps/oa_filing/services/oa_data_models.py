"""OA 导入通用数据结构。

供 import services 使用，不依赖任何律所特定模块。
各律所 adapter 产出这些数据结构，services 消费它们。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── 案件导入数据 ──────────────────────────────────────────────────


@dataclass
class OACaseCustomerData:
    """OA客户数据（案件中提取）。"""

    name: str
    customer_type: str  # natural / legal
    address: str | None = None
    phone: str | None = None
    id_number: str | None = None
    industry: str | None = None
    legal_representative: str | None = None


@dataclass
class OACaseInfoData:
    """OA案件信息数据。"""

    case_no: str
    case_name: str | None = None
    case_stage: str | None = None
    acceptance_date: str | None = None
    case_category: str | None = None
    case_type: str | None = None
    responsible_lawyer: str | None = None
    description: str | None = None
    client_side: str | None = None


@dataclass
class OAConflictData:
    """OA利益冲突数据。"""

    name: str
    conflict_type: str | None = None


@dataclass
class OACaseData:
    """OA案件完整数据。"""

    case_no: str
    keyid: str
    customers: list[OACaseCustomerData] = field(default_factory=list)
    case_info: OACaseInfoData | None = None
    conflicts: list[OAConflictData] = field(default_factory=list)


# ── 客户导入数据 ──────────────────────────────────────────────────


@dataclass
class OACustomerData:
    """OA客户数据。"""

    name: str
    client_type: str  # natural / legal
    phone: str | None = None
    address: str | None = None
    id_number: str | None = None
    legal_representative: str | None = None
    gender: str | None = None
