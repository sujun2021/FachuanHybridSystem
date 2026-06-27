"""PDF 合并服务 — documents 模块。

继承 core 基类，仅实现 documents 特有的逻辑。
"""

from __future__ import annotations

import io
from typing import Any

from django.utils import timezone

from apps.core.services.pdf_merge_service import (
    PDFMergeServiceBase,
    PDFMergeValidator,
    PDFMergeWorkflowBase,
)
from apps.documents.models import EvidenceList
from apps.documents.services.infrastructure.pdf_merge_utils import add_page_numbers as add_page_numbers_util
from apps.documents.services.infrastructure.pdf_merge_utils import convert_docx_to_pdf, convert_image_to_pdf


class DocumentsPDFMergeWorkflow(PDFMergeWorkflowBase):
    """documents 模块的 PDF 合并工作流。"""

    def _generate_merged_filename(self, evidence_list: Any) -> str:
        """向后兼容：原方法名带下划线前缀。"""
        return self.generate_merged_filename(evidence_list)

    def convert_to_pdf(self, file_path: str) -> str:  # pragma: no cover
        ext = self._get_ext(file_path)
        self.validator.assert_supported_format(ext, file_path)
        if ext in PDFMergeValidator.IMAGE_FORMATS:
            return convert_image_to_pdf(file_path)
        if ext in PDFMergeValidator.WORD_FORMATS:
            return convert_docx_to_pdf(file_path)
        return file_path

    def add_page_numbers(self, pdf_input: io.BytesIO, start_page: int = 1) -> bytes:
        return add_page_numbers_util(pdf_input, start_page)

    def generate_merged_filename(self, evidence_list: EvidenceList) -> str:
        case_name = evidence_list.case.name
        date_str = timezone.now().strftime("%Y%m%d")
        list_suffix = ""
        title = evidence_list.title
        if title.startswith("证据清单"):
            list_suffix = title[4:]
        elif title.startswith("补充证据清单"):
            list_suffix = title[6:]
        version = evidence_list.export_version
        return f"证据明细{list_suffix}({case_name})V{version}_{date_str}.pdf"

    @staticmethod
    def _get_ext(file_path: str) -> str:
        from pathlib import Path

        return Path(file_path).suffix.lower()


class PDFMergeService(PDFMergeServiceBase):
    """documents 模块的 PDF 合并服务门面。"""

    def _create_workflow(self) -> DocumentsPDFMergeWorkflow:
        return DocumentsPDFMergeWorkflow()


# 向后兼容：原类名
PDFMergeWorkflow = DocumentsPDFMergeWorkflow
