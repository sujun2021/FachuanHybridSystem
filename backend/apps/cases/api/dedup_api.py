"""文件去重 API 端点。"""

from __future__ import annotations

from django.http import HttpRequest
from ninja import Router

from apps.cases.schemas import (
    DedupExecuteIn,
    DedupScanIn,
    DedupScanOut,
)
from apps.cases.services.case.case_access_policy import CaseAccessPolicy
from apps.cases.services.case.case_query_service import CaseQueryService
from apps.cases.services.dedup.file_dedup_service import DedupAction, FileDeduplicationService
from apps.core.infrastructure.throttling import rate_limit_from_settings
from apps.core.security import get_request_access_context

router = Router()


def _get_service() -> FileDeduplicationService:
    return FileDeduplicationService()


def _require_case_access(request: HttpRequest, case_id: int) -> None:
    ctx = get_request_access_context(request)
    CaseQueryService(access_policy=CaseAccessPolicy()).get_case(
        case_id=case_id,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )


@router.post("/{case_id}/dedup-scan", response=DedupScanOut)
@rate_limit_from_settings("TASK", by_user=True)
def scan_duplicates(request: HttpRequest, case_id: int, payload: DedupScanIn) -> dict:
    """扫描案件绑定文件夹中的重复文件。

    按文件大小预分组 → MD5 哈希比对 → 返回重复文件组列表。
    默认不执行实际操作（仅报告），需调用 dedup-execute 执行删除/回收。
    """
    _require_case_access(request, case_id)

    action = DedupAction.REPORT
    if payload.action == "delete":
        action = DedupAction.DELETE
    elif payload.action == "recycle":
        action = DedupAction.RECYCLE

    service = _get_service()
    result = service.scan_and_dedup(
        case_id=case_id,
        scan_subfolder=payload.scan_subfolder,
        action=action,
        dry_run=True,  # 扫描阶段仅检测，不执行操作
    )

    return service.build_scan_result_data(result)


@router.post("/{case_id}/dedup-execute")
@rate_limit_from_settings("TASK", by_user=True)
def execute_dedup(request: HttpRequest, case_id: int, payload: DedupExecuteIn) -> dict:
    """执行去重操作（删除或移动到回收目录）。

    注意：此操作不可逆，请先通过 dedup-scan 预览结果。
    """
    _require_case_access(request, case_id)

    action = DedupAction.DELETE if payload.action == "delete" else DedupAction.RECYCLE

    service = _get_service()

    if payload.dry_run:
        result = service.scan_and_dedup(
            case_id=case_id,
            action=action,
            dry_run=True,
        )
        return {
            "dry_run": True,
            "data": service.build_scan_result_data(result),
        }

    result = service.scan_and_dedup(
        case_id=case_id,
        action=action,
        dry_run=False,
    )

    return {
        "dry_run": False,
        "data": service.build_scan_result_data(result),
    }
