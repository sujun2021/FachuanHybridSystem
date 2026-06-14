"""
可插拔插件目录

每个插件是一个独立的 Python 包，可以被动态检测和加载。
插件目录会被添加到 .gitignore，用户需要手动安装。
"""

from typing import Literal

__all__ = [
    "has_court_automation_plugin",
    "has_court_filing_api_plugin",
    "has_weike_private_api_plugin",
    "has_law_verification_plugin",
    "has_captcha_ocr_plugin",
    "get_plugin_status",
]


def has_court_automation_plugin() -> bool:
    """
    检测法院自动化立案/担保插件是否已安装。

    检查 plugins.court_automation 模块是否存在。

    Returns:
        bool: 插件存在返回 True，否则返回 False
    """
    try:
        from plugins import court_automation

        return True
    except ImportError:
        return False


def has_court_filing_api_plugin() -> bool:
    """
    检测 HTTP 链路立案插件是否已安装。

    Returns:
        bool: 插件存在返回 True，否则返回 False
    """
    try:
        from plugins.court_filing_http import api_service

        return True
    except ImportError:
        return False


def has_weike_private_api_plugin() -> bool:
    """
    检测WK私有 API 适配器插件是否已安装。

    Returns:
        bool: 插件存在返回 True，否则返回 False
    """
    try:
        from plugins.weike_api_private import adapter

        return True
    except ImportError:
        return False


def get_plugin_status() -> dict[str, Literal["installed", "not_installed"]]:
    return {
        "court_automation": "installed" if has_court_automation_plugin() else "not_installed",
        "court_filing_http": "installed" if has_court_filing_api_plugin() else "not_installed",
        "weike_private_api": "installed" if has_weike_private_api_plugin() else "not_installed",
        "law_verification": "installed" if has_law_verification_plugin() else "not_installed",
        "captcha_ocr": "installed" if has_captcha_ocr_plugin() else "not_installed",
    }


def has_law_verification_plugin() -> bool:
    try:
        from plugins.weike_api_private import law_verification  # noqa: F401

        return True
    except ImportError:
        return False


def has_captcha_ocr_plugin() -> bool:
    """
    检测 captcha_ocr（ddddocr 验证码识别）插件是否已安装。

    Returns:
        bool: 插件存在返回 True，否则返回 False
    """
    try:
        from plugins.captcha_ocr import DdddocrRecognizer  # noqa: F401

        return True
    except ImportError:
        return False
