"""API endpoints."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from django.http import HttpRequest
from ninja import Router, Schema

from apps.cases.schemas import (
    CaseMaterialBindCandidateOut,
    CaseMaterialBindIn,
    CaseMaterialDeleteAllIn,
    CaseMaterialDeleteAllOut,
    CaseMaterialDeleteOut,
    CaseMaterialGroupOrderIn,
    CaseMaterialGroupRenameIn,
    CaseMaterialGroupRenameOut,
    CaseMaterialReplaceIn,
    CaseMaterialReplaceOut,
    CaseMaterialUploadOut,
)
from apps.cases.services import CaseLogService
from apps.cases.services.material.wiring import build_case_material_service
from apps.core.infrastructure.throttling import rate_limit_from_settings
from apps.core.security import get_request_access_context

router = Router()
logger = logging.getLogger("apps.cases.material_api")


def _get_case_material_service() -> Any:
    return build_case_material_service()


def _get_caselog_service() -> CaseLogService:
    return CaseLogService()


@router.get("/{case_id}/materials/bind-candidates", response=list[CaseMaterialBindCandidateOut])
def list_bind_candidates(request: HttpRequest, case_id: int) -> Any:  # pragma: no cover
    service = _get_case_material_service()
    ctx = get_request_access_context(request)
    return service.list_bind_candidates(
        case_id=case_id,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )


@router.post("/{case_id}/materials/bind")
@rate_limit_from_settings("TASK", by_user=True)
def bind_materials(request: HttpRequest, case_id: int, payload: CaseMaterialBindIn) -> dict[str, int]:  # pragma: no cover
    service = _get_case_material_service()
    ctx = get_request_access_context(request)
    items: list[dict[str, Any]] = [x.model_dump() for x in payload.items]
    saved = service.bind_materials(
        case_id=case_id,
        items=items,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )
    return {"saved_count": len(saved)}


@router.post("/{case_id}/materials/group-order")
@rate_limit_from_settings("TASK", by_user=True)
def save_group_order(request: HttpRequest, case_id: int, payload: CaseMaterialGroupOrderIn) -> dict[str, bool]:  # pragma: no cover
    service = _get_case_material_service()
    ctx = get_request_access_context(request)
    service.save_group_order(
        case_id=case_id,
        category=payload.category,
        ordered_type_ids=payload.ordered_type_ids,
        side=payload.side,
        supervising_authority_id=payload.supervising_authority_id,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )
    return {"ok": True}


@router.post("/{case_id}/materials/upload", response=CaseMaterialUploadOut)
@rate_limit_from_settings("UPLOAD", by_user=True)
def upload_materials(request: HttpRequest, case_id: int) -> dict[str, Any]:  # pragma: no cover
    service = _get_caselog_service()
    ctx = get_request_access_context(request)
    files = request.FILES.getlist("files") if hasattr(request, "FILES") else []
    log = service.create_log(  # type: ignore[call-arg, call-arg]
        case_id=case_id,
        content="上传材料",
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )
    created = service.upload_attachments(
        log_id=log.id,
        files=files,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )
    return {"log_id": log.id, "attachment_ids": [x.id for x in created]}  # type: ignore[attr-defined]


@router.post(
    "/{case_id}/materials/{material_id}/replace",
    response=CaseMaterialReplaceOut,
)
@rate_limit_from_settings("TASK", by_user=True)
def replace_material_file(  # pragma: no cover
    request: HttpRequest, case_id: int, material_id: int, payload: CaseMaterialReplaceIn
) -> dict[str, Any]:
    """替换材料对应的附件文件。"""
    service = _get_case_material_service()
    ctx = get_request_access_context(request)
    return service.replace_material_file(
        case_id=case_id,
        material_id=material_id,
        new_attachment_id=payload.new_attachment_id,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )


@router.post(
    "/{case_id}/materials/group-rename",
    response=CaseMaterialGroupRenameOut,
)
@rate_limit_from_settings("TASK", by_user=True)
def rename_group(request: HttpRequest, case_id: int, payload: CaseMaterialGroupRenameIn) -> dict[str, Any]:  # pragma: no cover
    """重命名材料分组。"""
    service = _get_case_material_service()
    ctx = get_request_access_context(request)
    return service.rename_group(
        case_id=case_id,
        type_id=payload.type_id,
        new_type_name=payload.new_type_name,
        update_global=payload.update_global,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )


@router.delete(
    "/{case_id}/materials/{material_id}",
    response=CaseMaterialDeleteOut,
)
@rate_limit_from_settings("TASK", by_user=True)
def delete_material(request: HttpRequest, case_id: int, material_id: int) -> dict[str, Any]:  # pragma: no cover
    """删除材料绑定（附件文件不受影响）。"""
    service = _get_case_material_service()
    ctx = get_request_access_context(request)
    return service.delete_material(
        case_id=case_id,
        material_id=material_id,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )


@router.delete(
    "/{case_id}/materials",
    response=CaseMaterialDeleteAllOut,
)
@rate_limit_from_settings("TASK", by_user=True)
def delete_all_materials(request: HttpRequest, case_id: int, payload: CaseMaterialDeleteAllIn) -> dict[str, Any]:  # pragma: no cover
    """按分类删除案件下的所有材料。"""
    service = _get_case_material_service()
    ctx = get_request_access_context(request)
    return service.delete_all_materials(
        case_id=case_id,
        category=payload.category,
        user=ctx.user,
        org_access=ctx.org_access,
        perm_open_access=ctx.perm_open_access,
    )


# ── 文件去重（内联在材料页面） ──

class _DedupFileInfo(Schema):
    attachment_id: int
    file_name: str
    file_url: str = ""
    file_size: int = 0
    size_display: str = ""
    uploaded_at: str = ""


class _DedupGroup(Schema):
    hash_value: str
    files: list[_DedupFileInfo] = []
    wasted_display: str = ""


class _DedupScanOut(Schema):
    total_files: int = 0
    duplicate_groups: list[_DedupGroup] = []
    total_duplicates: int = 0
    wasted_display: str = ""


class _DedupDeleteIn(Schema):
    attachment_ids: list[int]


def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


@router.post("/{case_id}/materials/dedup-scan", response=_DedupScanOut)
def scan_case_duplicates(request: HttpRequest, case_id: int) -> dict[str, Any]:
    """扫描该案件下所有上传附件的 MD5 重复。"""
    from apps.cases.models.log import CaseLogAttachment

    attachments = list(
        CaseLogAttachment.objects.filter(log__case_id=case_id)
        .select_related("log")
        .order_by("-uploaded_at")
    )
    if not attachments:
        return {"total_files": 0, "duplicate_groups": [], "total_duplicates": 0, "wasted_display": "0 B"}

    # 按大小预分组
    size_groups: dict[int, list[CaseLogAttachment]] = {}
    for att in attachments:
        try:
            size = att.file.size
        except Exception:
            size = 0
        if size not in size_groups:
            size_groups[size] = []
        size_groups[size].append(att)

    # 只保留 >1 的大小组
    size_groups = {s: g for s, g in size_groups.items() if len(g) > 1}

    # 计算哈希
    duplicate_groups: list[dict[str, Any]] = []
    total_wasted = 0
    total_duplicates = 0

    for size, group in size_groups.items():
        hash_map: dict[str, list[CaseLogAttachment]] = {}
        for att in group:
            try:
                with att.file.open("rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
            except Exception:
                continue
            if file_hash not in hash_map:
                hash_map[file_hash] = []
            hash_map[file_hash].append(att)

        for file_hash, dup_list in hash_map.items():
            if len(dup_list) <= 1:
                continue
            dup_list.sort(key=lambda a: a.uploaded_at, reverse=True)
            files = []
            wasted = 0
            for i, att in enumerate(dup_list):
                file_url = ""
                try:
                    file_url = att.file.url
                except Exception:
                    pass
                files.append({
                    "attachment_id": att.id,
                    "file_name": att.original_filename or att.file.name.split("/")[-1],
                    "file_url": file_url,
                    "file_size": att.file.size or 0,
                    "size_display": _fmt_size(att.file.size or 0),
                    "uploaded_at": att.uploaded_at.strftime("%Y-%m-%d %H:%M") if att.uploaded_at else "",
                })
                if i > 0:
                    wasted += att.file.size or 0
            duplicate_groups.append({
                "hash_value": file_hash,
                "files": files,
                "wasted_display": _fmt_size(wasted),
            })
            total_wasted += wasted
            total_duplicates += len(dup_list) - 1

    duplicate_groups.sort(key=lambda g: sum(f["file_size"] for f in g["files"][1:]), reverse=True)

    return {
        "total_files": len(attachments),
        "duplicate_groups": duplicate_groups,
        "total_duplicates": total_duplicates,
        "wasted_display": _fmt_size(total_wasted),
    }


@router.post("/{case_id}/materials/dedup-delete")
@rate_limit_from_settings("TASK", by_user=True)
def delete_case_duplicates(request: HttpRequest, case_id: int, payload: _DedupDeleteIn) -> dict[str, Any]:
    """删除指定的重复附件（同时删除磁盘文件）。"""
    from apps.cases.models.log import CaseLogAttachment

    ids = payload.attachment_ids
    if not ids:
        return {"deleted": 0, "message": "未选择任何文件"}

    # 仅删除该案件下的附件，防止越权
    attachments = list(CaseLogAttachment.objects.filter(id__in=ids, log__case_id=case_id))
    deleted_count = 0
    errors: list[str] = []

    for att in attachments:
        try:
            att.file.delete(save=False)
            att.delete()
            deleted_count += 1
        except Exception as e:
            errors.append(f"{att.original_filename or att.id}: {e}")

    return {"deleted": deleted_count, "errors": errors}
