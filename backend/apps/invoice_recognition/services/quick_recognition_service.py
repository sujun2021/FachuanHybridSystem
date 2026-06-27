from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from apps.automation.services.ocr.pdf_text_extractor import PDFTextExtractor
from apps.core.protocols import IOcrService

from .invoice_parser import InvoiceParser, ParsedInvoice
from .recognition_result import RecognitionResult

logger = logging.getLogger(__name__)


class QuickRecognitionService:
    """快速识别服务：不创建任务，直接返回识别结果。"""

    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20 MB

    def __init__(
        self,
        ocr_service: IOcrService,
        pdf_extractor: PDFTextExtractor,
        parser: InvoiceParser,
    ) -> None:
        self._ocr = ocr_service
        self._pdf_extractor = pdf_extractor
        self._parser = parser

    def recognize_files(self, files: list[UploadedFile]) -> list[RecognitionResult]:
        results: list[RecognitionResult] = []

        for file in files:
            result = self._process_single_file(file)
            results.append(result)

        logger.info("快速识别完成: 总文件数=%d", len(files))
        return results

    async def arecognize_files(self, files: list[UploadedFile]) -> list[RecognitionResult]:
        """异步并发识别多个文件，每个文件的 OCR 独立执行。"""
        tasks = [self._aprocess_single_file(file) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final: list[RecognitionResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("文件识别异常: %s, 文件: %s", result, files[i].name, exc_info=result)
                final.append(
                    RecognitionResult(
                        filename=files[i].name or "unknown",
                        success=False,
                        error="识别失败，请重试",
                    )
                )
            else:
                final.append(result)  # type: ignore[arg-type]

        logger.info("快速识别完成: 总文件数=%d", len(files))
        return final

    def _validate_file(self, file: UploadedFile) -> None:
        name: str = file.name or ""
        ext = Path(name).suffix.lower()

        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValidationError("不支持的文件格式：%(ext)s，仅允许 PDF、JPG、JPEG、PNG。" % {"ext": ext})

        size: int = file.size or 0
        if size > self.MAX_FILE_SIZE:
            raise ValidationError(
                "文件大小超过限制（最大 20 MB），当前文件大小：%(size).1f MB。" % {"size": size / 1024 / 1024}
            )

    def _process_single_file(self, file: UploadedFile) -> RecognitionResult:
        filename: str = file.name or "unknown"

        try:
            self._validate_file(file)

            ext = Path(filename).suffix.lower()
            if ext == ".pdf":
                raw_text = self._process_pdf(file)
            else:
                raw_text = self._process_image(file)

            parsed: ParsedInvoice = self._parser.parse(raw_text)

            logger.info("文件识别成功: %s", filename)
            return RecognitionResult(
                filename=filename,
                success=True,
                data=parsed,
            )

        except ValidationError as exc:
            logger.error("文件验证失败: %s, 文件: %s", exc.message, filename)
            return RecognitionResult(
                filename=filename,
                success=False,
                error=str(exc.message),
            )

        except Exception as exc:
            logger.error(
                "文件识别失败: %s, 文件: %s",
                exc,
                filename,
                exc_info=True,
            )
            return RecognitionResult(
                filename=filename,
                success=False,
                error="识别失败，请重试",
            )

    async def _aprocess_single_file(self, file: UploadedFile) -> RecognitionResult:
        """异步版本的单文件处理，在线程池中运行同步逻辑。"""
        return await sync_to_async(self._process_single_file, thread_sensitive=False)(file)

    def _process_pdf(self, file: UploadedFile) -> str:  # pragma: no cover
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)

        try:
            text = self._pdf_extractor.extract(tmp_path)
            if text is not None:
                return text

            image_paths, img_tmp_dir = self._pdf_extractor.pdf_to_images(tmp_path)
            try:
                parts: list[str] = []
                for img_path in image_paths:
                    parts.append(self._ocr.recognize(str(img_path)))
                return "\n".join(parts)
            finally:
                shutil.rmtree(img_tmp_dir, ignore_errors=True)

        finally:
            tmp_path.unlink(missing_ok=True)

    def _process_image(self, file: UploadedFile) -> str:  # pragma: no cover
        import tempfile

        ext = Path(file.name or "").suffix.lower()
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
            for chunk in file.chunks():
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)

        try:
            return self._ocr.recognize(str(tmp_path))
        finally:
            tmp_path.unlink(missing_ok=True)
