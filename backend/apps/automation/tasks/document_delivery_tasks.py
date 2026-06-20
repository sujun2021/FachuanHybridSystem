"""文书送达 Playwright 查询后台任务。"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger("apps.automation")


def query_document_delivery_via_playwright(
    credential_id: int,
    cutoff_time_iso: str,
    tab: str = "pending",
) -> None:
    """Django-Q 后台任务：使用 Playwright 方式查询文书。

    当 API 快速路径失败时，由 API 层 dispatch 到此任务。
    Playwright 浏览器自动化可能耗时 30-120 秒，不适合同步请求。

    Args:
        credential_id: 账号凭证 ID
        cutoff_time_iso: 截止时间 ISO 字符串（序列化安全）
        tab: 查询标签页 pending / reviewed
    """
    from django.utils.dateparse import parse_datetime

    cutoff_time = parse_datetime(cutoff_time_iso)
    if cutoff_time is None:
        logger.error("无法解析 cutoff_time: %s", cutoff_time_iso)
        return

    logger.info(
        "后台任务启动: Playwright 文书查询 credential_id=%d, cutoff_time=%s, tab=%s",
        credential_id,
        cutoff_time_iso,
        tab,
    )

    from apps.automation.services.document_delivery.document_delivery_service import DocumentDeliveryService

    service = DocumentDeliveryService()
    result = service._query_via_playwright(
        credential_id=credential_id,
        cutoff_time=cutoff_time,
        tab=tab,
        debug_mode=False,
    )

    logger.info(
        "后台任务完成: Playwright 文书查询 credential_id=%d, "
        "found=%d, processed=%d, skipped=%d, failed=%d",
        credential_id,
        result.total_found,
        result.processed_count,
        result.skipped_count,
        result.failed_count,
    )
