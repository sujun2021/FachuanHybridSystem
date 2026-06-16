"""文件去重 API 请求/响应 Schema。"""

from __future__ import annotations

from ninja import Schema


class DedupScanIn(Schema):
    """去重扫描请求"""
    scan_subfolder: str = ""
    action: str = "report"  # report | delete | recycle


class DedupFileInfo(Schema):
    """重复文件信息"""
    path: str
    name: str
    size: int
    size_mb: float = 0
    modified_at: float = 0
    modified_display: str = ""
    is_keep: bool = False


class DedupGroupOut(Schema):
    """一组重复文件"""
    hash_value: str
    file_count: int
    duplicate_count: int
    total_wasted: int
    total_wasted_mb: float = 0
    keep_path: str = ""
    files: list[DedupFileInfo] = []


class DedupActionResult(Schema):
    """操作执行结果"""
    path: str
    action: str
    success: bool = False
    message: str = ""
    recycle_path: str = ""
    error: str = ""
    keep_path: str = ""


class DedupSummaryOut(Schema):
    """去重扫描摘要"""
    total_files: int = 0
    total_size: int = 0
    total_size_mb: float = 0
    hash_groups: int = 0
    duplicate_groups: int = 0
    total_duplicate_files: int = 0
    total_wasted_bytes: int = 0
    total_wasted_mb: float = 0
    action: str = "report"
    action_count: int = 0
    errors: int = 0
    duration_seconds: float = 0
    scan_root: str = ""


class DedupScanOut(Schema):
    """去重扫描完整结果"""
    summary: DedupSummaryOut
    duplicate_groups: list[DedupGroupOut] = []
    action_results: list[DedupActionResult] = []
    errors: list[str] = []
    scan_root: str = ""


class DedupExecuteIn(Schema):
    """执行去重操作请求"""
    action: str  # delete | recycle
    hash_values: list[str] = []  # 指定处理的重复组哈希值，空=全部
    dry_run: bool = True


__all__ = [
    "DedupScanIn",
    "DedupFileInfo",
    "DedupGroupOut",
    "DedupActionResult",
    "DedupSummaryOut",
    "DedupScanOut",
    "DedupExecuteIn",
]
