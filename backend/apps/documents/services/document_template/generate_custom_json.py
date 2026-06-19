"""生成 custom_defaults.json 的辅助脚本。

遍历 0101 目录，自动生成文件夹模板 + 文件模板 + 绑定关系的 JSON。
"""
import hashlib
import json
import random
import string
import time
from pathlib import Path
from typing import Any

# --- 根目录 ---
DOCX_ROOT = Path(__file__).resolve().parent.parent.parent / "docx_templates"
CUSTOM_DIR = DOCX_ROOT / "0101【诉讼 仲裁】xxvsxx 案号"

# --- sub_type 映射 ---
SUBTYPE_MAP: dict[str, str] = {
    "00-委托代理材料": "delegation_materials",
    "01-案件内参": "case_reference",
    "02-我方文书": "our_pleadings",
    "03-证据": "evidence_materials",
    "04-法院文书": "court_documents",
    "05-沟通留痕": "communication_records",
    "06-财产保全": "property_preservation_materials",
    "07-网上立案": "online_filing",
    "09-申请强制执行材料": "enforcement_materials",
}

# --- 简洁版文件夹节点名 ---
CLEAN_NAMES: dict[str, str] = {
    "00-委托代理材料（委托合同、授权委托书、风险告知书、付款申请书、发票等）": "00-委托代理材料",
    "01-案件内参（案件分析报告 诉讼策略备忘 庭审提纲 内部探讨）": "01-案件内参",
    "02-我方文书（起诉状 答辩状 上诉状 代理词 质证意见 答辩状 调查令申请等等）": "02-我方文书",
    "03-证据-各方诉讼参与人举证材料（含客户提供的证据、以及其他诉讼参与人的证据）": "03-证据",
    "04-法院文书（案件受理通知书 传票 各类裁定书 判决书 执行通知书 庭审记录 质证意见）": "04-法院文书",
    "05-沟通留痕（与客户 法院 对方的往来邮件、微信截图、电话记录、谈话笔录、案件日志、给客户的案件汇报等）": "05-沟通留痕",
    "06-财产保全（含申请、保险、财产明细、续封等）": "06-财产保全",
    "07-网上立案（内容与网上立案要保持一致）": "07-网上立案",
    "09-申请强制执行材料": "09-申请强制执行材料",
    "99-归档": "99-归档",
}


def gen_id() -> str:
    """生成唯一 ID"""
    ts = int(time.time() * 1000)
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"folder_{ts}_{suffix}"


def is_docx_or_doc(fname: str) -> bool:
    """只处理 .docx 和 .doc 文件"""
    low = fname.lower()
    return low.endswith(".docx") or low.endswith(".doc")


def detect_template_type(path_in_custom: str, fname: str) -> str:
    """判断 template_type: case / contract / archive"""
    # 99-归档下的文件
    if path_in_custom.startswith("99-归档"):
        return "archive"
    # 只有在 00-委托代理材料 目录下，且包含合同关键词的才算合同模板
    if path_in_custom.startswith("00-委托代理材料"):
        contract_keywords = [
            "合同", "代理协议", "委托代理协议", "专项代理协议",
            "风险代理", "代理合同",
        ]
        for kw in contract_keywords:
            if kw in fname:
                # 排除误判：授权委托书等不是合同
                misleading = ["授权委托书", "所函", "变更委托"]
                if any(m in fname for m in misleading):
                    return "case"
                return "contract"
    return "case"


def detect_archive_sub_type(fname: str) -> str | None:
    """归档文件的 archive_sub_type"""
    name = fname
    if any(kw in name for kw in ["案卷封面", "律师业务档案卷宗"]):
        return "case_cover"
    if "结案归档登记表" in name or "收案" in name:
        return "closing_archive_register"
    if "卷内目录" in name:
        return "inner_catalog"
    if "律师工作日志" in name:
        return "lawyer_work_log"
    if "服务质量监督卡" in name:
        return "service_quality_card"
    if "办案小结" in name:
        return "case_summary"
    return "case_cover"


def detect_case_types(path_in_custom: str) -> list[str]:
    """根据文件夹位置推断适用的案件类型"""
    # 强制执行相关
    if "09-申请强制执行材料" in path_in_custom:
        return ["civil", "criminal", "administrative", "execution"]
    return ["civil", "criminal", "administrative"]


def clean_folder_name(raw: str) -> str:
    """获取简洁版文件夹名"""
    for long, short in CLEAN_NAMES.items():
        if raw == long or raw.startswith(long.split("（")[0]):
            return short
    # Unmatched: strip everything after （
    if "（" in raw:
        return raw.split("（")[0]
    return raw


def build_folder_tree(base_dir: Path, top_name: str) -> dict[str, Any]:
    """递归扫描目录构建文件夹树 JSON"""
    children: list[dict[str, Any]] = []
    for item in sorted(base_dir.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            # 跳过子文件夹内的深层目录（只保留一层子目录）
            sub_children: list[dict[str, Any]] = []
            for sub_item in sorted(item.iterdir()):
                if sub_item.name.startswith("."):
                    continue
                if sub_item.is_dir():
                    clean_sub = clean_folder_name(sub_item.name)
                    # 只保留有意义的子目录（非空且非系统目录）
                    has_content = any(
                        f.is_file() and not f.name.startswith(".")
                        for f in sub_item.rglob("*")
                    )
                    if has_content:
                        sub_children.append({
                            "id": gen_id(),
                            "name": clean_sub,
                            "children": [],
                        })
            clean = clean_folder_name(item.name)
            children.append({
                "id": gen_id(),
                "name": clean,
                "children": sub_children,
            })
    return {"children": children}


def extract_file_list(base_dir: Path) -> list[dict[str, Any]]:
    """遍历目录提取所有 docx/doc 文件信息"""
    files: list[dict[str, Any]] = []
    rel_base = str(base_dir.relative_to(DOCX_ROOT)).replace("\\", "/")

    for fpath in sorted(base_dir.rglob("*")):
        if fpath.name.startswith("."):
            continue
        if not fpath.is_file():
            continue
        if not is_docx_or_doc(fpath.name):
            continue

        rel_path = str(fpath.relative_to(DOCX_ROOT)).replace("\\", "/")
        # 找出所属的直接子文件夹（相对于 base_dir）
        try:
            rel_to_base = fpath.relative_to(base_dir)
            parts = rel_to_base.parts
            if len(parts) >= 2:
                parent_dir = parts[0]
            else:
                parent_dir = parts[0] if len(parts) == 1 else ""
        except ValueError:
            parent_dir = ""

        # 获取简洁版文件夹名
        clean_parent = clean_folder_name(parent_dir) if parent_dir else ""

        # 模板名称：去掉扩展名
        display_name = fpath.stem

        # 确定 sub_type
        sub_type = SUBTYPE_MAP.get(clean_parent, "other_materials")

        files.append({
            "name": display_name,
            "file_path": rel_path,
            "parent_dir": clean_parent,
            "sub_type": sub_type,
            "template_type": detect_template_type(clean_parent, fpath.name),
        })

    return files


def main() -> None:
    """生成 custom_defaults.json"""
    # 1. 生成文件夹模板结构
    structure = build_folder_tree(CUSTOM_DIR, "0101")

    # 2. 提取所有文件
    all_files = extract_file_list(CUSTOM_DIR)

    # 3. 文件夹模板列表
    folder_templates: list[dict[str, Any]] = []

    # 民事案件文件夹
    folder_templates.append({
        "name": "民事案件文件夹",
        "template_type": "case",
        "case_types": ["civil"],
        "case_stages": ["all"],
        "contract_types": [],
        "legal_statuses": [],
        "legal_status_match_mode": "any",
        "structure": structure,
        "is_default": False,
        "is_active": True,
        "_custom": True,
    })

    # 刑事案件文件夹
    folder_templates.append({
        "name": "刑事案件文件夹",
        "template_type": "case",
        "case_types": ["criminal"],
        "case_stages": ["all"],
        "contract_types": [],
        "legal_statuses": [],
        "legal_status_match_mode": "any",
        "structure": structure,
        "is_default": False,
        "is_active": True,
        "_custom": True,
    })

    # 行政案件文件夹
    folder_templates.append({
        "name": "行政案件文件夹",
        "template_type": "case",
        "case_types": ["administrative"],
        "case_stages": ["all"],
        "contract_types": [],
        "legal_statuses": [],
        "legal_status_match_mode": "any",
        "structure": structure,
        "is_default": False,
        "is_active": True,
        "_custom": True,
    })

    # 申请执行文件夹
    folder_templates.append({
        "name": "申请执行文件夹（自定义）",
        "template_type": "case",
        "case_types": ["civil", "criminal", "administrative", "execution"],
        "case_stages": ["enforcement"],
        "contract_types": [],
        "legal_statuses": [],
        "legal_status_match_mode": "any",
        "structure": structure,
        "is_default": False,
        "is_active": True,
        "_custom": True,
    })

    # 合同文件夹
    folder_templates.append({
        "name": "合同文件夹（自定义）",
        "template_type": "contract",
        "case_types": [],
        "case_stages": [],
        "contract_types": ["all"],
        "legal_statuses": [],
        "legal_status_match_mode": "any",
        "structure": {"children": [
            {"id": gen_id(), "name": "00-委托代理材料", "children": [
                {"id": gen_id(), "name": "1-合同", "children": []},
                {"id": gen_id(), "name": "2-补充协议", "children": []},
                {"id": gen_id(), "name": "3-发票", "children": []},
                {"id": gen_id(), "name": "4-其他资料", "children": []},
            ]},
            {"id": gen_id(), "name": "02-我方文书", "children": []},
            {"id": gen_id(), "name": "05-沟通留痕", "children": []},
        ]},
        "is_default": False,
        "is_active": True,
        "_custom": True,
    })

    # 4. 文件模板列表
    document_templates: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for finfo in all_files:
        if finfo["name"] in seen_names:
            continue
        seen_names.add(finfo["name"])

        ttype = finfo["template_type"]
        entry: dict[str, Any] = {
            "name": finfo["name"],
            "template_type": ttype,
            "file_path": finfo["file_path"],
            "is_active": True,
        }

        if ttype == "case":
            entry["contract_sub_type"] = None
            entry["case_sub_type"] = finfo["sub_type"]
            entry["archive_sub_type"] = None
            entry["case_types"] = detect_case_types(finfo["parent_dir"])
            entry["case_stages"] = ["all"]
            entry["contract_types"] = []
            entry["legal_statuses"] = []
            entry["legal_status_match_mode"] = "any"
        elif ttype == "contract":
            entry["contract_sub_type"] = "contract"
            entry["case_sub_type"] = None
            entry["archive_sub_type"] = None
            entry["contract_types"] = ["all"]
            entry["case_types"] = []
            entry["case_stages"] = []
            entry["legal_statuses"] = []
            entry["legal_status_match_mode"] = "any"
        elif ttype == "archive":
            entry["contract_sub_type"] = None
            entry["case_sub_type"] = None
            entry["archive_sub_type"] = detect_archive_sub_type(finfo["name"])
            entry["contract_types"] = []
            entry["case_types"] = []
            entry["case_stages"] = []
            entry["legal_statuses"] = []
            entry["legal_status_match_mode"] = "any"

        document_templates.append(entry)

    # 5. 绑定关系
    bindings: list[dict[str, Any]] = []
    for finfo in all_files:
        ttype = finfo["template_type"]
        parent = finfo["parent_dir"]

        # 只有有父目录的文件才绑定
        if not parent:
            continue

        # 确定要绑定的文件夹模板
        if ttype == "contract":
            bindings.append({
                "document_template_name": finfo["name"],
                "folder_template_name": "合同文件夹（自定义）",
                "folder_node_name": parent,
            })
            continue

        if ttype == "archive":
            # 归档文件暂不绑定到 case 文件夹，后续可在 admin 手动操作
            continue

        # Case 类型文件，按 case_types 绑定
        case_types = detect_case_types(finfo["parent_dir"])
        if "civil" in case_types:
            bindings.append({
                "document_template_name": finfo["name"],
                "folder_template_name": "民事案件文件夹",
                "folder_node_name": parent,
            })
        if "criminal" in case_types:
            bindings.append({
                "document_template_name": finfo["name"],
                "folder_template_name": "刑事案件文件夹",
                "folder_node_name": parent,
            })
        if "administrative" in case_types:
            bindings.append({
                "document_template_name": finfo["name"],
                "folder_template_name": "行政案件文件夹",
                "folder_node_name": parent,
            })
        # 强制执行材料额外绑定到申请执行文件夹
        if "execution" in case_types:
            bindings.append({
                "document_template_name": finfo["name"],
                "folder_template_name": "申请执行文件夹（自定义）",
                "folder_node_name": parent,
            })

    # 6. 输出 JSON
    result = {
        "folder_templates": folder_templates,
        "document_templates": document_templates,
        "bindings": bindings,
    }

    output_path = Path(__file__).with_name("custom_defaults.json")
    data = json.dumps(result, ensure_ascii=False, indent=2)
    output_path.write_text(data, encoding="utf-8")

    print(f"Generated: {output_path}")
    print(f"  Folder templates: {len(folder_templates)}")
    print(f"  Document templates: {len(document_templates)}")
    print(f"  Bindings: {len(bindings)}")


if __name__ == "__main__":
    main()
