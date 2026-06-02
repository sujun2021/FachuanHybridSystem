"""公众号登录状态管理（扫码检测）。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def check_login_status(page: Page) -> bool:
    """检查当前页面是否已登录公众号后台。"""
    try:
        current_url = page.url
        if "mp.weixin.qq.com/cgi-bin/loginpage" in current_url:
            return False

        login_indicators = [
            ".mp_account_box",
            ".acount_box-nickname",
            ".weui-desktop-account__info",
            ".weui-desktop-account__nickname",
            ".user_info",
            ".main_hd",
        ]
        for selector in login_indicators:
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                return True
        return False
    except Exception as exc:
        if "Execution context was destroyed" in str(exc):
            return False
        logger.warning("Failed to check login status: %s", exc)
        return False


async def wait_for_qr_scan(page: Page, timeout_seconds: int = 120) -> bool:
    """等待用户扫码登录。"""
    start_time = time.time()
    check_interval = 2

    while time.time() - start_time < timeout_seconds:
        if await check_login_status(page):
            logger.info("QR scan login successful")
            return True
        await asyncio.sleep(check_interval)

    logger.warning("QR scan login timeout after %d seconds", timeout_seconds)
    return False


async def capture_qr_code(page: Page) -> bytes | None:
    """截取登录二维码区域的截图。"""
    try:
        qr_selectors = [
            ".login__type__container__scan",
            ".qrcode",
            "#loginQrCode",
            "img[src*='qrcode']",
            ".login_box",
        ]

        for selector in qr_selectors:
            qr_element = await page.query_selector(selector)
            if qr_element:
                return await qr_element.screenshot()

        logger.warning("QR code element not found, capturing full page")
        return await page.screenshot()
    except Exception:
        logger.warning("Failed to capture QR code", exc_info=True)
        return None
