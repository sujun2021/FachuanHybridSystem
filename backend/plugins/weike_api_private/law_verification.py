"""
法规引用核查服务

从法律文书中抽取法规引用，通过威科先行 API 核查并比对条文内容。
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Any


# ──────────────────────────────────────────────────────────────
# 正则抽取
# ──────────────────────────────────────────────────────────────

_CN_DIGITS = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_CN_UNITS = {"十": 10, "百": 100, "千": 1000}


def _chinese_to_int(cn: str) -> int:
    if not cn:
        return 0
    result = 0
    current = 0
    for ch in cn:
        if ch in _CN_DIGITS:
            current = _CN_DIGITS[ch]
        elif ch in _CN_UNITS:
            unit = _CN_UNITS[ch]
            if current == 0 and unit == 10:
                current = 1
            result += current * unit
            current = 0
    result += current
    return result if result > 0 else 0


_ARTICLE_PATTERNS = [
    re.compile(r"第(\d+)条(?:第(\d+)款)?(?:第[（(]?(\d+)[)）]?项)?"),
    re.compile(r"第([一二三四五六七八九十百千]+)条(?:第([一二三四五六七八九十百千]+)款)?(?:第[（(]?([一二三四五六七八九十百千]+)[)）]?项)?"),
]


def extract_references(text: str) -> list[dict[str, Any]]:
    """从文档全文中抽取所有法规引用.

    Returns:
        [{law_name, article_num, context}]
    """
    refs: list[dict[str, Any]] = []
    for m in re.finditer(r"《([^》]+)》", text):
        law_name = m.group(1).strip()
        if not law_name:
            continue

        after = text[m.end(): m.end() + 200]
        cutoff = len(after)
        for stop_char in ["《", "。", "；", "\n"]:
            idx = after.find(stop_char)
            if 0 < idx < cutoff:
                cutoff = idx
        after = after[:cutoff]

        for pattern in _ARTICLE_PATTERNS:
            for am in pattern.finditer(after):
                groups = am.groups()
                article_str = groups[0]
                article_num = int(article_str) if article_str.isdigit() else _chinese_to_int(article_str)
                if article_num <= 0:
                    continue

                ctx_start = max(0, m.start() - 50)
                ctx_end = min(len(text), m.end() + len(am.group()) + 50)
                context = text[ctx_start:ctx_end].replace("\n", " ").strip()

                refs.append({
                    "law_name": law_name,
                    "article_num": article_num,
                    "context": context,
                })

    seen: set[tuple[str, int]] = set()
    unique: list[dict[str, Any]] = []
    for ref in refs:
        key = (ref["law_name"], ref["article_num"])
        if key not in seen:
            seen.add(key)
            unique.append(ref)
    return unique


# ──────────────────────────────────────────────────────────────
# 条文比对
# ──────────────────────────────────────────────────────────────


def _normalize_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("　", " ")
    text = re.sub(r"[，。；：、“”‘’（）《》【】\s\n\r\t]", "", text)
    text = unicodedata.normalize("NFKC", text)
    return text.strip()


def compare_texts(reference_context: str, article_text: str) -> float:
    """计算引用上下文与条文原文的相似度."""
    ref_clean = reference_context
    ref_clean = re.sub(r"《[^》]+》", "", ref_clean)
    ref_clean = re.sub(r"第[一二三四五六七八九十百千\d]+条", "", ref_clean)
    ref_clean = re.sub(r"根据|依据|参照|按照|之规定|规定[，,：:]", "", ref_clean)

    norm_ref = _normalize_text(ref_clean)
    norm_art = _normalize_text(article_text)
    if not norm_ref or not norm_art:
        return 0.0

    seq_score = difflib.SequenceMatcher(None, norm_ref, norm_art).ratio()
    shorter, longer = (norm_ref, norm_art) if len(norm_ref) <= len(norm_art) else (norm_art, norm_ref)
    contain_score = 0.0
    if len(shorter) >= 10 and shorter in longer:
        contain_score = len(shorter) / len(longer)
    return max(seq_score, contain_score)


# ──────────────────────────────────────────────────────────────
# 核查主流程
# ──────────────────────────────────────────────────────────────


def verify_references(
    text: str,
    *,
    search_laws_fn: Any,
    fetch_article_fn: Any,
) -> list[dict[str, Any]]:
    """核查文档中所有法规引用.

    Args:
        text: 文档全文
        search_laws_fn: callable(law_name) -> list[dict]
        fetch_article_fn: callable(doc_id, article_num) -> str | None

    Returns:
        [{law_name, article_num, status, validity, article_text, reference_text, similarity, weike_url}]
    """
    refs = extract_references(text)
    results: list[dict[str, Any]] = []
    law_cache: dict[str, list[dict]] = {}

    for ref in refs:
        law_name = ref["law_name"]
        article_num = ref["article_num"]

        if law_name not in law_cache:
            try:
                law_cache[law_name] = search_laws_fn(law_name)
            except Exception:
                law_cache[law_name] = []

        matches = law_cache[law_name]
        if not matches:
            results.append({
                "law_name": law_name, "article_num": article_num,
                "status": "not_found", "validity": "未找到",
                "article_text": None, "reference_text": ref["context"],
                "similarity": None, "weike_url": "",
            })
            continue

        best = matches[0]
        doc_id = best["docId"]
        validity_text = best.get("validityStatusText", "")

        if validity_text and "废止" in validity_text:
            results.append({
                "law_name": law_name, "article_num": article_num,
                "status": "deprecated", "validity": validity_text,
                "article_text": None, "reference_text": ref["context"],
                "similarity": None,
                "weike_url": f"https://law.wkinfo.com.cn/legislation/detail/{doc_id}",
            })
            continue

        article_text = None
        try:
            article_text = fetch_article_fn(doc_id, article_num)
        except Exception:
            pass

        if not article_text:
            results.append({
                "law_name": law_name, "article_num": article_num,
                "status": "not_found", "validity": validity_text or "现行有效",
                "article_text": None, "reference_text": ref["context"],
                "similarity": None,
                "weike_url": f"https://law.wkinfo.com.cn/legislation/detail/{doc_id}",
            })
            continue

        similarity = compare_texts(ref["context"], article_text)
        status = "verified" if similarity >= 0.8 else "mismatch"

        results.append({
            "law_name": law_name, "article_num": article_num,
            "status": status, "validity": validity_text or "现行有效",
            "article_text": article_text[:500], "reference_text": ref["context"],
            "similarity": round(similarity, 2),
            "weike_url": f"https://law.wkinfo.com.cn/legislation/detail/{doc_id}",
        })

    return results
