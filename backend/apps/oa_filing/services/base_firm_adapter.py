"""OA 系统适配器协议。

每个律所 OA 系统实现一组 Protocol，由 ScriptExecutorService 统一调度。
新增律所只需：
1. 在 oa_scripts/<firm>/ 下创建 adapter.py 实现这些 Protocol
2. 在 oa_firm_registry.py 中注册
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FilingAdapter(Protocol):
    """立案适配器协议。"""

    async def execute_filing(
        self,
        session: Any,
        credential: Any,
        contract_id: int,
        case_id: int | None,
    ) -> None:
        """执行立案操作。"""
        ...


@runtime_checkable
class StampAdapter(Protocol):
    """盖章适配器协议。"""

    async def execute_stamp(self, session: Any) -> None:
        """执行盖章申请。从 session 中读取凭证和表单数据。"""
        ...


@runtime_checkable
class ArchiveAdapter(Protocol):
    """归档适配器协议。"""

    async def execute_archive(self, session: Any) -> None:
        """执行归档材料提交。从 session 中读取凭证和文件路径。"""
        ...

    async def open_oa_page(
        self,
        credential: Any,
        oa_case_number: str,
        description: str,
    ) -> None:
        """打开 OA 归档页面，填写案件编号和小结，保持浏览器打开。"""
        ...


@runtime_checkable
class CaseImportAdapter(Protocol):
    """案件导入适配器协议。"""

    async def execute_case_import(self, session: Any) -> None:
        """执行案件导入。"""
        ...


@runtime_checkable
class ClientImportAdapter(Protocol):
    """客户导入适配器协议。"""

    async def execute_client_import(self, session: Any) -> None:
        """执行客户导入。"""
        ...
