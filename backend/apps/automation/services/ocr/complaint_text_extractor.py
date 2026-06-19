"""起诉状文本提取器 —— 多级回退引擎。

从起诉状 PDF 中提取文本内容，用于后续解析当事人信息。

回退策略：
  1. pdfplumber 文本层提取（最快，秒级）
  2. PaddleOCR-VL-1.6 云端 OCR（高精度版面分析）
  3. MinerU 云端智能文档解析
  4. 通知人工处理
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("apps.automation")


# 提取目标文本最少字符数，低于此值认为提取不足
_MIN_TEXT_LENGTH = 80


def _clean_ocr_text(text: str) -> str:
    """清洗 OCR / pdfplumber 输出的文本。

    去掉中文之间多余的空格（OCR 常见问题），
    但保留英文单词和数字之间的单个空格。
    """
    if not text:
        return ""
    # 去掉所有空白字符，然后用统一的换行分隔
    cleaned = re.sub(r"[ \t]+", "", text)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    return cleaned


def _extract_via_pdfplumber(file_path: str) -> str | None:
    """第 1 级：pdfplumber 文本层提取。"""
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber 未安装，跳过文本层提取")
        return None

    try:
        with pdfplumber.open(file_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception:
        logger.exception("pdfplumber 打开 PDF 失败: %s", file_path)
        return None

    raw = "\n".join(pages)
    cleaned = _clean_ocr_text(raw)
    if len(cleaned) >= _MIN_TEXT_LENGTH:
        logger.info("pdfplumber 提取成功: %s (%d 字符)", Path(file_path).name, len(cleaned))
        return cleaned

    logger.info("pdfplumber 提取文本不足 (%d 字符)，降级到 OCR", len(cleaned))
    return None


def _extract_via_paddleocr(file_path: str) -> str | None:
    """第 2 级：PaddleOCR-VL-1.6 云端 OCR。"""
    try:
        from apps.automation.services.ocr.paddleocr_api_service import PaddleOCRApiEngine

        engine = PaddleOCRApiEngine()
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        is_pdf = Path(file_path).suffix.lower() == ".pdf"
        result = engine.recognize_bytes(file_bytes, is_pdf=is_pdf)
        if result and result.text:
            cleaned = _clean_ocr_text(result.text)
            if len(cleaned) >= _MIN_TEXT_LENGTH:
                logger.info("PaddleOCR 提取成功: %s (%d 字符)", Path(file_path).name, len(cleaned))
                return cleaned
            logger.info("PaddleOCR 提取文本不足 (%d 字符)", len(cleaned))
        else:
            logger.warning("PaddleOCR 返回空结果: %s", file_path)
    except Exception:
        logger.exception("PaddleOCR 提取失败: %s", file_path)

    return None


def _extract_via_mineru(file_path: str) -> str | None:
    """第 3 级：MinerU 云端文档解析。"""
    try:
        from apps.document_parsing.services.parser_factory import ParserFactory

        parser = ParserFactory.create_parser("mineru", timeout=120)
        result = parser.parse_document(file_path)
        if result and result.text:
            cleaned = _clean_ocr_text(result.text)
            if len(cleaned) >= _MIN_TEXT_LENGTH:
                logger.info("MinerU 提取成功: %s (%d 字符)", Path(file_path).name, len(cleaned))
                return cleaned
            logger.info("MinerU 提取文本不足 (%d 字符)", len(cleaned))
        else:
            logger.warning("MinerU 返回空结果: %s", file_path)
    except ValueError as e:
        if "未配置 MinerU" in str(e):
            logger.warning("MinerU 未配置 API Key，跳过")
        else:
            logger.exception("MinerU 提取失败: %s", file_path)
    except Exception:
        logger.exception("MinerU 提取失败: %s", file_path)

    return None


def _extract_from_complaint_pdf(file_path: str) -> str | None:
    """多级回退：从起诉状 PDF 中提取文本。

    Args:
        file_path: 起诉状 PDF 文件的绝对路径

    Returns:
        提取到的文本内容，如果所有引擎均失败则返回 None
    """
    logger.info("开始提取起诉状文本: %s", file_path)

    # 第 1 级：pdfplumber
    text = _extract_via_pdfplumber(file_path)
    if text:
        return text

    # 第 2 级：PaddleOCR-VL-1.6
    text = _extract_via_paddleocr(file_path)
    if text:
        return text

    # 第 3 级：MinerU
    text = _extract_via_mineru(file_path)
    if text:
        return text

    # 第 4 级：全部失败
    logger.error("所有 OCR 引擎均无法提取起诉状文本: %s", file_path)
    return None
