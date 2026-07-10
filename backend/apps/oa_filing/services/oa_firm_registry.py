"""OA 站点适配器注册表。

新增律所只需：
1. 在 oa_scripts/<firm>/adapter.py 中实现适配器
2. 在 _ADAPTERS 中注册 site_name → adapter class 的映射
"""

from __future__ import annotations

from typing import Any

_ADAPTERS: dict[str, str] = {
    "金诚同达OA": "apps.oa_filing.services.oa_scripts.jtn.adapter.JTNAdapter",
}

SUPPORTED_SITES: list[str] = list(_ADAPTERS.keys())


def get_adapter_class(site_name: str) -> type:
    """按 site_name 查找适配器类。"""
    dotted = _ADAPTERS.get(site_name)
    if dotted is None:
        raise ValueError(f"不支持的 OA 系统: {site_name}，可用: {SUPPORTED_SITES}")

    module_path, class_name = dotted.rsplit(".", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)  # type: ignore[no-any-return]


def create_adapter(site_name: str, account: str, password: str) -> Any:
    """按 site_name 创建适配器实例。"""
    cls = get_adapter_class(site_name)
    return cls(account=account, password=password)
