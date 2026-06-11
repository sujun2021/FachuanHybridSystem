"""
种子数据加载服务

从 JSON 种子文件加载案由和法院数据到数据库.
仅在表为空时加载,不会覆盖已有数据.
"""

import json
import logging
from pathlib import Path
from typing import Any

from django.db import transaction

from apps.core.models import CauseOfAction, Court

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_cause_seed_data(*, force: bool = False) -> dict[str, Any]:
    """从 seed_causes_of_action.json 加载案由数据.

    Args:
        force: 为 True 时忽略表非空检查,强制重新加载.

    Returns:
        {"loaded": N, "skipped": bool}
    """
    if not force and CauseOfAction.objects.exists():
        logger.debug("案由表非空,跳过种子数据加载")
        return {"loaded": 0, "skipped": True}

    seed_file = DATA_DIR / "seed_causes_of_action.json"
    if not seed_file.exists():
        logger.warning("案由种子数据文件不存在: %s", seed_file)
        return {"loaded": 0, "skipped": True}

    data = json.loads(seed_file.read_text(encoding="utf-8"))
    return _import_causes(data, force=force)


def _import_causes(data: list[dict[str, Any]], *, force: bool = False) -> dict[str, Any]:
    """将案由数据导入数据库.

    两遍处理:
    1. 创建所有节点 (parent=None)
    2. 按 parent_code 设置层级关系
    """
    # 按 level 排序,保证父节点先创建
    sorted_data = sorted(data, key=lambda x: x.get("level", 1))

    with transaction.atomic():
        if force:
            CauseOfAction.objects.all().delete()
            logger.info("强制模式: 已清空案由表")

        # 第一遍:创建所有节点,暂不设置 parent
        code_to_obj: dict[str, CauseOfAction] = {}
        for item in sorted_data:
            obj, _created = CauseOfAction.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "case_type": item["case_type"],
                    "level": item.get("level", 1),
                    "is_active": True,
                    "is_deprecated": False,
                    "deprecated_at": None,
                    "deprecated_reason": "",
                    "parent": None,
                },
            )
            code_to_obj[item["code"]] = obj

        # 第二遍:设置 parent 关系
        parent_updated = 0
        for item in sorted_data:
            parent_code = item.get("parent_code")
            if parent_code and parent_code in code_to_obj:
                obj = code_to_obj[item["code"]]
                if obj.parent_id != code_to_obj[parent_code].pk:
                    obj.parent = code_to_obj[parent_code]
                    obj.save(update_fields=["parent"])
                    parent_updated += 1

    loaded = len(sorted_data)
    logger.info("案由种子数据加载完成: %d 条, 更新 parent %d 条", loaded, parent_updated)
    return {"loaded": loaded, "skipped": False}


def load_court_seed_data(*, force: bool = False) -> dict[str, Any]:
    """从 seed_courts.json 加载法院数据.

    Args:
        force: 为 True 时忽略表非空检查,强制重新加载.

    Returns:
        {"loaded": N, "skipped": bool}
    """
    if not force and Court.objects.exists():
        logger.debug("法院表非空,跳过种子数据加载")
        return {"loaded": 0, "skipped": True}

    seed_file = DATA_DIR / "seed_courts.json"
    if not seed_file.exists():
        logger.warning("法院种子数据文件不存在: %s", seed_file)
        return {"loaded": 0, "skipped": True}

    data = json.loads(seed_file.read_text(encoding="utf-8"))
    return _import_courts(data, force=force)


def _import_courts(data: list[dict[str, Any]], *, force: bool = False) -> dict[str, Any]:
    """将法院数据导入数据库.

    两遍处理,逻辑同 _import_causes.
    """
    sorted_data = sorted(data, key=lambda x: x.get("level", 1))

    with transaction.atomic():
        if force:
            Court.objects.all().delete()
            logger.info("强制模式: 已清空法院表")

        # 第一遍:创建所有节点
        code_to_obj: dict[str, Court] = {}
        for item in sorted_data:
            obj, _created = Court.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "level": item.get("level", 1),
                    "province": item.get("province", ""),
                    "is_active": True,
                    "parent": None,
                },
            )
            code_to_obj[item["code"]] = obj

        # 第二遍:设置 parent 关系
        parent_updated = 0
        for item in sorted_data:
            parent_code = item.get("parent_code")
            if parent_code and parent_code in code_to_obj:
                obj = code_to_obj[item["code"]]
                if obj.parent_id != code_to_obj[parent_code].pk:
                    obj.parent = code_to_obj[parent_code]
                    obj.save(update_fields=["parent"])
                    parent_updated += 1

    loaded = len(sorted_data)
    logger.info("法院种子数据加载完成: %d 条, 更新 parent %d 条", loaded, parent_updated)
    return {"loaded": loaded, "skipped": False}
