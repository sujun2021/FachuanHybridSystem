"""用户自定义模板初始化服务。

读取 custom_defaults.json，创建文件夹模板/文件模板/绑定关系。
原作者的 complete_defaults.json 完全独立，互不影响。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from django.db import transaction

from apps.documents.models import DocumentTemplate, DocumentTemplateFolderBinding, FolderTemplate
from apps.documents.storage import resolve_docx_template_path

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).with_name("custom_defaults.json")


class CustomTemplateInitService:
    """用户自定义模板初始化服务（与原作者默认模板完全独立）"""

    def _find_missing_docx_files(self, document_templates: list[dict[str, Any]]) -> list[str]:
        missing_files: list[str] = []
        for template_data in document_templates:
            relative_file_path = str(template_data.get("file_path", "")).strip()
            if not relative_file_path:
                continue
            try:
                absolute_file_path = resolve_docx_template_path(relative_file_path)
            except ValueError:
                missing_files.append(relative_file_path)
                continue
            if not absolute_file_path.exists():
                missing_files.append(relative_file_path)
        return missing_files

    def _find_folder_node_id(self, folder: FolderTemplate, node_name: str) -> str | None:
        """在文件夹模板的 structure JSON 中递归查找节点名称对应的 ID"""
        if not folder.structure:
            return None
        return self._search_node(folder.structure, node_name)

    def _search_node(self, node: dict[str, Any], target_name: str) -> str | None:
        """递归搜索节点名"""
        if isinstance(node.get("name"), str) and node["name"] == target_name:
            return node.get("id")
        children = node.get("children", [])
        for child in children:
            result = self._search_node(child, target_name)
            if result:
                return result
        return None

    def _load_data(self) -> dict[str, Any]:
        if not _DATA_FILE.exists():
            raise FileNotFoundError(
                "缺少自定义模板配置文件 custom_defaults.json。\n"
                "请先运行: python backend/apps/documents/services/document_template/generate_custom_json.py"
            )
        return json.loads(_DATA_FILE.read_text(encoding="utf-8"))

    @transaction.atomic
    def initialize_custom_templates(self) -> dict[str, Any]:
        """初始化所有自定义模板（事务性，失败全部回滚）"""
        data = self._load_data()

        missing_files = self._find_missing_docx_files(data["document_templates"])
        if missing_files:
            logger.warning("自定义模板初始化失败：缺失 %s 个 docx 文件", len(missing_files))
            return {
                "success": False,
                "error_code": "missing_docx_files",
                "missing_files": missing_files,
                "folder_created": 0,
                "folder_skipped": 0,
                "doc_created": 0,
                "doc_skipped": 0,
                "binding_created": 0,
                "binding_skipped": 0,
            }

        folder_created = 0
        folder_skipped = 0
        doc_created = 0
        doc_skipped = 0
        binding_created = 0
        binding_skipped = 0

        # ---------- 1. 文件夹模板 ----------
        folder_map: dict[str, FolderTemplate] = {}
        for fd in data["folder_templates"]:
            folder_data = {k: v for k, v in fd.items() if not k.startswith("_")}
            existing = FolderTemplate.objects.filter(name=folder_data["name"]).first()
            if existing:
                logger.info("跳过已存在的文件夹模板: %s", folder_data["name"])
                folder_skipped += 1
                folder_map[folder_data["name"]] = existing
            else:
                ft = FolderTemplate.objects.create(**folder_data)
                logger.info("创建文件夹模板: %s", folder_data["name"])
                folder_created += 1
                folder_map[folder_data["name"]] = ft

        # ---------- 2. 文件模板 ----------
        doc_map: dict[str, DocumentTemplate] = {}
        for td in data["document_templates"]:
            existing = DocumentTemplate.objects.filter(
                name=td["name"], template_type=td["template_type"]
            ).first()
            if existing:
                logger.info("跳过已存在的文件模板: %s", td["name"])
                doc_skipped += 1
                doc_map[td["name"]] = existing
            else:
                create_data = {k: v for k, v in td.items() if not k.startswith("_")}
                dt = DocumentTemplate.objects.create(**create_data)
                logger.info("创建文件模板: %s", td["name"])
                doc_created += 1
                doc_map[td["name"]] = dt

        # ---------- 3. 绑定关系 ----------
        from apps.documents.services.template.contract_template.binding_service import (
            DocumentTemplateBindingService,
        )

        binding_service = DocumentTemplateBindingService()

        for bd in data["bindings"]:
            doc_name = bd["document_template_name"]
            folder_name = bd["folder_template_name"]
            node_name = bd["folder_node_name"]

            if doc_name not in doc_map or folder_name not in folder_map:
                logger.warning("跳过绑定（模板不存在）: %s → %s", doc_name, folder_name)
                continue

            doc = doc_map[doc_name]
            folder = folder_map[folder_name]

            # 把 folder_node_name 解析为 folder_node_id
            node_id = self._find_folder_node_id(folder, node_name)
            if not node_id:
                logger.warning("跳过绑定（未找到节点 %s 在 %s）", node_name, folder_name)
                continue

            existing_binding = DocumentTemplateFolderBinding.objects.filter(
                document_template=doc, folder_template=folder, folder_node_id=node_id
            ).exists()

            if existing_binding:
                logger.info("跳过已存在的绑定: %s → %s / %s", doc_name, folder_name, node_name)
                binding_skipped += 1
            else:
                folder_node_path = binding_service.calculate_folder_path(folder, node_id)
                DocumentTemplateFolderBinding.objects.create(
                    document_template=doc,
                    folder_template=folder,
                    folder_node_id=node_id,
                    folder_node_path=folder_node_path,
                )
                logger.info(
                    "创建绑定: %s → %s / %s (路径: %s)",
                    doc_name, folder_name, node_name, folder_node_path,
                )
                binding_created += 1

        return {
            "success": True,
            "folder_created": folder_created,
            "folder_skipped": folder_skipped,
            "doc_created": doc_created,
            "doc_skipped": doc_skipped,
            "binding_created": binding_created,
            "binding_skipped": binding_skipped,
            "missing_files": [],
        }

    def delete_all_custom_templates(self) -> dict[str, int]:
        """删除所有自定义模板（文件夹/文件/绑定）"""
        data = self._load_data()

        folder_names = [f["name"] for f in data["folder_templates"]]
        doc_names = [d["name"] for d in data["document_templates"]]

        folder_deleted = FolderTemplate.objects.filter(name__in=folder_names).delete()[0]
        doc_deleted = DocumentTemplate.objects.filter(name__in=doc_names).delete()[0]

        return {
            "folders_deleted": folder_deleted,
            "documents_deleted": doc_deleted,
            # 绑定会随模板级联删除，不需要单独统计
        }
