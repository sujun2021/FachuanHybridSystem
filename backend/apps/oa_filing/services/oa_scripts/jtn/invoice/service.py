"""金诚同达 OA 发票申请 — 门面服务。"""

from __future__ import annotations

from .playwright_invoice import PlaywrightInvoiceMixin


class JtnInvoiceScript(PlaywrightInvoiceMixin):
    """金诚同达 OA 发票申请门面类。"""

    def __init__(self, account: str, password: str) -> None:
        from ..auth.service import JtnAuthService

        self._account = account
        self._password = password
        self._auth = JtnAuthService(account, password)

    async def open_page(self, oa_case_number: str) -> tuple:
        """打开发票页面并填写，返回 (playwright, browser)。"""
        return await self._open_page(oa_case_number)
