"""通用、数据库、Redis、文件存储、日志、通知等配置数据"""

from typing import Any

__all__ = ["get_general_configs"]


def get_general_configs() -> list[dict[str, Any]]:
    """获取通用配置项"""
    return [
        {
            "key": "CASE_LOG_ATTACHMENT_AUTO_SUBDIR",
            "category": "general",
            "description": "案件日志附件存入绑定文件夹（true=上传附件时存入绑定文件夹的「案件日志附件」子目录；false=存入 MEDIA_ROOT，不使用绑定文件夹）",
            "value": "true",
            "is_secret": False,
        },
    ]
