"""
Cases App Admin模块主文件
统一管理所有案件的Admin界面
"""

from __future__ import annotations

from .case_admin import CaseAdmin
from .case_chat_admin import CaseChatAdmin
from .caselog_admin import CaseLogAdmin, CaseLogAttachmentAdmin
from .caseassignment_admin import CaseAssignmentAdmin
from .caseparty_admin import CasePartyAdmin
from .log_batch_admin import CaseLogBatchAdmin
from .payment_admin import CasePaymentRecordAdmin, PaymentRecordCategoryAdmin

__all__ = [
    "CaseAdmin",
    "CaseAssignmentAdmin",
    "CaseChatAdmin",
    "CaseLogAdmin",
    "CaseLogAttachmentAdmin",
    "CaseLogBatchAdmin",
    "CasePartyAdmin",
    "CasePaymentRecordAdmin",
    "PaymentRecordCategoryAdmin",
]
