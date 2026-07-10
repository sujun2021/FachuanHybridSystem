"""金诚同达 OA 发票申请页面自动化。"""

from __future__ import annotations

from .playwright_invoice import PlaywrightInvoiceMixin
from .service import JtnInvoiceScript

__all__ = ["JtnInvoiceScript"]
