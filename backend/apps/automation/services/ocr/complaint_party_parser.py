"""起诉状当事人信息解析器。

从起诉状 OCR 文本中提取当事人（原告/被告/第三人）的：
  - 名称
  - 地址
  - 统一社会信用代码 / 身份证号
  - 法定代表人/负责人姓名
  - 法定代表人/负责人手机号
  - 联系电话
"""

from __future__ import annotations

import re
from typing import Any

# ─── 法定代表人关键词（含"负责人""局长"等变体）─────────────────────
_FDDDR_NAME_KEYWORDS = [
    "法定代表人",
    "负责人",
    "法定代表",
    "局长",
    "市长",
    "县长",
    "区长",
    "镇长",
    "乡长",
    "主任",
    "执行董事",
    "董事长",
    "总经理",
    "厂长",
    "院长",
    "校长",
    "社长",
    "会长",
    "理事长",
]

_FDDDR_PHONE_KEYWORDS = [
    "法定代表人手机号",
    "法定代表人电话",
    "法定代表人联系电话",
    "负责人手机号",
    "负责人电话",
    "负责人联系电话",
    "手机号",
    "手机号码",
    "联系电话",
    "电话",
]

# ─── 当事人身份关键词 ─────────────────────────────────────────────
_PLAINTIFF_KEYWORDS = ["原告", "申请人", "申请执行人", "起诉人", "上诉人"]
_DEFENDANT_KEYWORDS = ["被告", "被申请人", "被执行人", "被上诉人"]
_THIRD_KEYWORDS = ["第三人"]

# ─── 字段关键词 ───────────────────────────────────────────────────
_NAME_KEYWORDS = ["名称", "单位名称", "姓名", "公司名称", "企业名称"]
_ADDRESS_KEYWORDS = ["地址", "住所", "住所地", "经营场所", "注册地址", "住址"]
_USCC_KEYWORDS = ["统一社会信用代码", "信用代码", "社会信用代码"]
_ID_NUMBER_KEYWORDS = ["身份证号码", "身份证号", "身份证", "证件号码"]
_PHONE_KEYWORDS = ["联系电话", "电话", "手机", "手机号码", "手机号"]

# ─── 字段名净化正则 ───────────────────────────────────────────────
_FIELD_LABEL_RE = re.compile(r"^[：:]\s*")


def _clean_field_value(value: str) -> str:
    """去掉字段值中可能残留的字段标签（如冒号开头）。"""
    return _FIELD_LABEL_RE.sub("", value).strip()


def _parse_section(section_text: str, role: str) -> dict[str, str] | None:
    """解析一个当事人段落的文本。

    策略：按行扫描，识别字段标签（如"统一社会信用代码：xxx"），
    提取紧跟着标签的值。找不到标签时用启发式推测。
    """
    if not section_text:
        return None

    lines = [l.strip() for l in section_text.split("\n") if l.strip()]
    info: dict[str, str] = {"role": role}
    current_field: str | None = None
    buffer: list[str] = []
    has_tag_match = False

    for line in lines:
        # 尝试匹配字段标签
        matched = False
        for kw in _NAME_KEYWORDS:
            if kw in line:
                val = _clean_field_value(line.split(kw, 1)[-1])
                if val and (not info.get("name") or len(val) < len(str(info.get("name", "")))):
                    info["name"] = val
                matched = True
                has_tag_match = True
                break
        if matched:
            continue

        for kw in _ADDRESS_KEYWORDS:
            if kw in line:
                info["address"] = _clean_field_value(line.split(kw, 1)[-1])
                matched = True
                has_tag_match = True
                break
        if matched:
            continue

        for kw in _USCC_KEYWORDS:
            if kw in line:
                val = _clean_field_value(line.split(kw, 1)[-1])
                if len(val) >= 15:
                    info["uscc"] = val
                matched = True
                has_tag_match = True
                break
        if matched:
            continue

        for kw in _ID_NUMBER_KEYWORDS:
            if kw in line:
                val = _clean_field_value(line.split(kw, 1)[-1])
                if len(val) >= 15:
                    info["id_number"] = val
                matched = True
                has_tag_match = True
                break
        if matched:
            continue

        for kw in _PHONE_KEYWORDS:
            if kw in line:
                phone_val = re.sub(r"\s+", "", _clean_field_value(line.split(kw, 1)[-1]))
                if re.search(r"\d{7,}", phone_val):
                    info["phone"] = phone_val
                matched = True
                has_tag_match = True
                break
        if matched:
            continue

        # 法定代表人匹配
        fddbr_matched = False
        for kw in _FDDDR_NAME_KEYWORDS:
            if kw in line:
                # 可能是 "法定代表人：张三" 或 "法定代表人 张三"
                val = _clean_field_value(line.split(kw, 1)[-1])
                if val and len(val) > 1 and len(val) < 20:
                    info["legal_rep"] = val
                elif not val and len(lines) > 0:
                    # 下一行可能是名字
                    pass
                fddbr_matched = True
                has_tag_match = True
                break
        if fddbr_matched:
            current_field = "fddbr"
            continue

        # 法定代表人电话匹配
        for kw in _FDDDR_PHONE_KEYWORDS:
            if kw in line:
                phone_val = re.sub(r"\s+", "", _clean_field_value(line.split(kw, 1)[-1]))
                if re.search(r"\d{7,}", phone_val):
                    info["fddbrsjhm_phone"] = phone_val
                matched = True
                has_tag_match = True
                break
        if matched:
            continue

        # 无标签行 → 可能是名字（第一行）或续行
        buffer.append(line)

    # ─── 名称识别 + 启发式提取 ────────────────────────────
    if buffer:
        if not has_tag_match or not info.get("name"):
            first_line = buffer[0]
            name = _clean_field_value(first_line.split("：", 1)[-1] if "：" in first_line else first_line)
            info.setdefault("name", name)

        if not has_tag_match:
            for line in buffer:
                uscc_match = re.search(r"[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}", line)
                if uscc_match:
                    info["uscc"] = uscc_match.group(0)
                    continue

                phone_match = re.search(r"1[3-9]\d{9}", line)
                if phone_match:
                    info.setdefault("phone", phone_match.group(0))
                    continue

                fixed_phone = re.search(r"0\d{2,3}[-\s]*\d{7,8}", line)
                if fixed_phone:
                    info.setdefault("phone", fixed_phone.group(0))
                    continue

                id_match = re.search(r"\d{17}[\dXx]", line)
                if id_match:
                    info.setdefault("id_number", id_match.group(0))
                    continue

    # ─── 法定代表人电话回退 ────────────────────────────
    if info.get("fddbrsjhm_phone"):
        pass  # 已经提取了法定代表人手机号
    elif info.get("phone") and info.get("legal_rep"):
        # 有法定代表人姓名但没有独立手机号 → 用联系电话兜底
        info["fddbrsjhm_phone"] = info["phone"]

    return info if info.get("name") else None


def _split_sections(text: str) -> list[tuple[str, str]]:
    """将文本按当事人身份（原告/被告/第三人）分段。

    Returns:
        [(角色, 段落文本), ...]
    """
    sections: list[tuple[str, str]] = []
    current_role: str | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # 检测段落开始（关键词出现在行开头或紧跟前缀标识符）
        new_role: str | None = None
        if any(stripped.startswith(kw) for kw in _PLAINTIFF_KEYWORDS):
            new_role = "plaintiff"
        elif any(stripped.startswith(kw) for kw in _DEFENDANT_KEYWORDS):
            new_role = "defendant"
        elif any(stripped.startswith(kw) for kw in _THIRD_KEYWORDS):
            new_role = "third_party"
        # 也匹配 "一、原告" 或 "1. 原告" 等格式
        elif not new_role:
            for kw in _PLAINTIFF_KEYWORDS:
                if kw in stripped and len(stripped) < 50:
                    new_role = "plaintiff"
                    break
            for kw in _DEFENDANT_KEYWORDS:
                if kw in stripped and len(stripped) < 50 and not new_role:
                    new_role = "defendant"
                    break
            for kw in _THIRD_KEYWORDS:
                if kw in stripped and len(stripped) < 50 and not new_role:
                    new_role = "third_party"
                    break

        if new_role:
            if current_role and current_lines:
                sections.append((current_role, "\n".join(current_lines)))
            current_role = new_role
            current_lines = [stripped]
            continue

        if current_role:
            current_lines.append(stripped)

    if current_role and current_lines:
        sections.append((current_role, "\n".join(current_lines)))

    return sections


def parse_complaint_text(text: str) -> dict[str, list[dict[str, str]]]:
    """从起诉状文本中解析所有当事人信息。

    Args:
        text: 清洗后的起诉状 OCR 文本

    Returns:
        {
            "plaintiffs": [{name, address, uscc, legal_rep, fddbrsjhm_phone, phone, ...}],
            "defendants": [...],
            "third_parties": [...],
        }
    """
    sections = _split_sections(text)
    result: dict[str, list[dict[str, str]]] = {
        "plaintiffs": [],
        "defendants": [],
        "third_parties": [],
    }

    for role, section_text in sections:
        info = _parse_section(section_text, role)
        if info:
            if role == "plaintiff":
                result["plaintiffs"].append(info)
            elif role == "defendant":
                result["defendants"].append(info)
            elif role == "third_party":
                result["third_parties"].append(info)

    return result


def merge_ocr_with_client(
    *,
    ocr_parties: dict[str, list[dict[str, str]]],
    existing_parties: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """将 OCR 提取的当事人信息与 Client 表已有数据合并。

    合并规则：
      - Client 表已有的字段（name、uscc、legal_rep 等）：保留 Client 表数据
      - Client 表缺失的字段（fddbrsjhm_phone 等）：用 OCR 提取的补充
      - 都缺失的不强行覆盖

    Args:
        ocr_parties: OCR 提取的当事人字典
        existing_parties: _build_party_payloads 构建的当事人列表

    Returns:
        合并后的当事人列表
    """
    import logging

    _logger = logging.getLogger("apps.automation")

    def _find_match(name: str, ocr_list: list[dict[str, str]]) -> dict[str, str] | None:
        if not name:
            return None
        for item in ocr_list:
            item_name = item.get("name", "")
            if item_name and (item_name in name or name in item_name):
                return item
        return None

    for party in existing_parties:
        party_name = party.get("name", "")
        party_type = party.get("client_type", "legal")

        if party_type == "legal":
            # 找 OCR 中的匹配项
            ocr_match = _find_match(party_name, ocr_parties.get("plaintiffs", []))
            if not ocr_match:
                ocr_match = _find_match(party_name, ocr_parties.get("defendants", []))
            if not ocr_match:
                ocr_match = _find_match(party_name, ocr_parties.get("third_parties", []))

            if ocr_match:
                # 法定代表人手机号：OCR 提取 > 已有
                ocr_phone = ocr_match.get("fddbrsjhm_phone", "")
                if ocr_phone and not party.get("fddbrsjhm_phone"):
                    party["fddbrsjhm_phone"] = ocr_phone
                    _logger.info("OCR 补充法定代表人手机号: %s → %s", party_name, ocr_phone)

                # 法定代表人姓名：Client 表优先，OCR 补充
                ocr_legal_rep = ocr_match.get("legal_rep", "")
                if ocr_legal_rep and not party.get("legal_rep"):
                    party["legal_rep"] = ocr_legal_rep
                    _logger.info("OCR 补充法定代表人: %s → %s", party_name, ocr_legal_rep)

                # 其他字段同理（只补充不覆盖）
                for key in ("address", "uscc", "phone"):
                    ocr_val = ocr_match.get(key, "")
                    if ocr_val and not party.get(key):
                        party[key] = ocr_val
                        _logger.info("OCR 补充 %s: %s → %s", key, party_name, ocr_val)

    return existing_parties
