"""案件合同关联查询服务。"""

from __future__ import annotations

from typing import Any

from apps.cases.models import Case


def get_case_contract_info(case_id: int) -> Any:
    """获取案件绑定的合同 ID 和文件夹绑定 ID。

    Returns:
        dict with keys: contract_id, contract__folder_binding__id，无匹配返回 None。
    """
    return Case.objects.filter(pk=case_id).values("contract_id", "contract__folder_binding__id").first()
