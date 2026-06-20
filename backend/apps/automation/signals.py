"""
自动化模块信号处理

处理模型删除事件，自动触发文件清理。
创建和更新事件已迁移至 django-lifecycle @hook 装饰器。
"""

import logging
from pathlib import Path
from typing import Any, cast

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

logger = logging.getLogger("apps.automation")


# ───────────────────────────────────────────────
# 文件清理信号
# ───────────────────────────────────────────────

@receiver(post_delete, dispatch_uid="cleanup_court_document_local_file")
def cleanup_court_document_local_file(sender: type, **kwargs: Any) -> None:  # pragma: no cover
    """
    删除 CourtDocument 记录时，自动清理下载的法院文书物理文件

    CourtDocument 使用 CharField(local_file_path) 存储文件路径（非 FileField），
    因此需要通过信号手动删除物理文件。
    """
    from .models.court_document import CourtDocument

    if sender is not CourtDocument:
        return
    instance = kwargs["instance"]
    if not instance.local_file_path:
        return
    from django.conf import settings

    file_path = Path(instance.local_file_path)
    if not file_path.is_absolute():
        file_path = Path(settings.MEDIA_ROOT) / instance.local_file_path
    if file_path.exists():
        try:
            transaction.on_commit(lambda p=file_path: _unlink_court_doc(p, instance.court_sms_id))
        except OSError as exc:
            logger.error(
                "清理法院文书物理文件失败",
                extra={"file_path": str(file_path), "error": str(exc)},
            )


def _unlink_court_doc(file_path: Path, court_sms_id: Any) -> None:
    try:
        file_path.unlink()
        logger.info(
            "已清理法院文书物理文件",
            extra={"file_path": str(file_path), "court_sms_id": court_sms_id},
        )
    except OSError as exc:
        logger.error(
            "清理法院文书物理文件失败",
            extra={"file_path": str(file_path), "error": str(exc)},
        )


@receiver(post_delete, dispatch_uid="cleanup_gsxt_report_task_file")
def cleanup_gsxt_report_task_file(sender: type, **kwargs: Any) -> None:  # pragma: no cover
    """GsxtReportTask 使用 FileField(report_file) 存储企业信用报告 PDF"""
    from .models.gsxt_report import GsxtReportTask

    if sender is not GsxtReportTask:
        return
    instance = kwargs["instance"]
    if instance.report_file:
        try:
            transaction.on_commit(lambda f=instance.report_file: f.delete(save=False))
            logger.info("已清理企业信用报告文件", extra={"file_path": str(instance.report_file)})
        except Exception:
            logger.exception("清理企业信用报告失败")


# ───────────────────────────────────────────────
# 案件目录绑定 → 自动补归档 SMS
# ───────────────────────────────────────────────

@receiver(post_save, sender="cases.CaseFolderBinding")
def auto_archive_sms_on_folder_binding(  # pragma: no cover
    sender: Any,
    instance: Any,
    created: bool,
    **kwargs: Any,
) -> None:
    """当 CaseFolderBinding 创建或更新时，自动补归档该案件的所有已完成但未归档的 SMS。

    只处理满足以下条件的 SMS：
    - 状态为 COMPLETED（已完成）
    - archived_to_case_folder=False（尚未归档）
    - 有关联的 scraper_task（有下载文书）
    - resolved_folder_path 可用（案件文件夹绑定有效）
    """
    try:
        from apps.automation.models import CourtSMS, CourtSMSStatus

        binding = instance
        if not binding.resolved_folder_path:
            return

        case_id = binding.case_id
        unarchived_sms_qs = CourtSMS.objects.filter(
            case_id=case_id,
            status=CourtSMSStatus.COMPLETED,
            archived_to_case_folder=False,
            scraper_task__isnull=False,
        )

        unarchived_sms_list = list(unarchived_sms_qs)
        if not unarchived_sms_list:
            return

        from apps.automation.services.sms.case_folder_archive_service import CaseFolderArchiveService

        archive_service = CaseFolderArchiveService()
        archived_count = 0

        for sms in unarchived_sms_list:
            try:
                renamed_paths = _resolve_renamed_paths(sms)
                if not renamed_paths:
                    continue
                success = archive_service.archive_sms_documents(
                    cast(Any, sms), renamed_paths
                )
                if success:
                    archived_count += 1
            except Exception as e:
                logger.warning(
                    f"信号补归档失败: SMS ID={sms.id}, 错误: {e!s}"
                )

        if archived_count > 0:
            logger.info(
                f"信号补归档完成: case_id={case_id}, "
                f"已归档/总数={archived_count}/{len(unarchived_sms_list)}"
            )
    except Exception as e:
        logger.warning(f"信号 auto_archive_sms_on_folder_binding 执行异常: {e!s}")


def _resolve_renamed_paths(sms: Any) -> list[str]:
    """解析 SMS 的 renamed 文件路径列表，用于补归档。"""
    from pathlib import Path as _Path

    paths: list[str] = []

    task = sms.scraper_task
    if not task:
        return paths

    # 来源 1：renamed_files
    result = task.result
    if isinstance(result, dict):
        renamed = result.get("renamed_files", [])
        if renamed and isinstance(renamed, list):
            for p in renamed:
                if p and _Path(p).exists():
                    paths.append(p)

    # 来源 2：documents.local_file_path
    if not paths and hasattr(task, "documents"):
        for doc in task.documents.filter(download_status="success"):
            if doc.local_file_path and _Path(doc.local_file_path).exists():
                paths.append(doc.local_file_path)

    # 来源 3：result["files"]
    if not paths and isinstance(result, dict):
        files = result.get("files", [])
        if files and isinstance(files, list):
            for p in files:
                if p and _Path(p).exists():
                    paths.append(p)

    return list(dict.fromkeys(paths))  # 去重保序
