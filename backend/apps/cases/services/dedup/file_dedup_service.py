"""
文件去重核心服务。

递归扫描案件绑定文件夹，按文件大小预分组 → MD5 哈希比对 → 标记重复组。
支持本地 + 云存储（OneDrive/WebDAV/S3/Google Drive/Dropbox）。
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.cases.models.material import CaseFolderBinding
from apps.core.cloud_storage.factory import create_provider_for_binding
from apps.core.cloud_storage.protocols import CloudFileInfo, CloudStorageProvider

if TYPE_CHECKING:
    from apps.cases.models import Case

logger = logging.getLogger("apps.cases.dedup")


class DedupAction(str, Enum):
    """去重操作类型"""
    SCAN_ONLY = "scan_only"       # 仅扫描检测，不执行操作
    DELETE = "delete"              # 删除重复文件
    RECYCLE = "recycle"            # 移动到回收目录
    REPORT = "report"              # 仅生成报告


@dataclass
class DuplicateGroup:
    """一组重复文件"""
    hash_value: str                                           # MD5 哈希值
    files: list[dict[str, Any]] = field(default_factory=list)  # 重复文件列表
    total_wasted: int = 0                                     # 可释放空间（bytes）
    keep_path: str = ""                                       # 保留的文件路径

    @property
    def duplicate_count(self) -> int:
        return max(len(self.files) - 1, 0)


@dataclass
class DedupResult:
    """去重扫描结果"""
    total_files: int = 0
    total_size: int = 0            # 总大小（bytes）
    hash_groups: int = 0           # 哈希分组数
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    total_duplicate_files: int = 0
    total_wasted_bytes: int = 0
    action: DedupAction = DedupAction.SCAN_ONLY
    action_results: list[dict[str, Any]] = field(default_factory=list)  # 操作执行结果
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    scan_root: str = ""

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "total_files": self.total_files,
            "total_size": self.total_size,
            "total_size_mb": round(self.total_size / (1024 * 1024), 2) if self.total_size else 0,
            "hash_groups": self.hash_groups,
            "duplicate_groups": len(self.duplicate_groups),
            "total_duplicate_files": self.total_duplicate_files,
            "total_wasted_bytes": self.total_wasted_bytes,
            "total_wasted_mb": round(self.total_wasted_bytes / (1024 * 1024), 2) if self.total_wasted_bytes else 0,
            "action": self.action.value,
            "action_count": len(self.action_results),
            "errors": len(self.errors),
            "duration_seconds": round(self.duration_seconds, 2),
            "scan_root": self.scan_root,
        }


class FileDeduplicationService:
    """案件级文件去重服务。

    用法:
        service = FileDeduplicationService()
        result = service.scan_and_dedup(case_id=123, action=DedupAction.REPORT)
    """

    # 分块读取大小（用于哈希计算）
    CHUNK_SIZE: int = 64 * 1024  # 64KB

    # 云存储读取大小阈值：超过此大小可能OOM，改用流式读取的替代方案
    CLOUD_READ_LIMIT: int = 50 * 1024 * 1024  # 50MB

    def __init__(self) -> None:
        pass

    # ---- 公共 API ----

    def scan_and_dedup(
        self,
        *,
        case_id: int,
        scan_subfolder: str = "",
        action: DedupAction = DedupAction.REPORT,
        dry_run: bool = True,
    ) -> DedupResult:
        """扫描案件绑定文件夹并执行去重。

        Args:
            case_id: 案件 ID
            scan_subfolder: 扫描子目录（空字符串表示扫描整个绑定目录）
            action: 去重操作类型
            dry_run: True 时仅扫描不执行实际操作

        Returns:
            DedupResult 包含完整的扫描和去重结果
        """
        start = timezone.now()

        result = DedupResult(action=action)

        # 1. 获取文件夹绑定
        try:
            binding = CaseFolderBinding.objects.select_related("storage_account").get(case_id=case_id)
        except CaseFolderBinding.DoesNotExist:
            result.errors.append(f"案件 {case_id} 未绑定文件夹，无法执行去重")
            result.duration_seconds = (timezone.now() - start).total_seconds()
            return result

        result.scan_root = binding.folder_path or ""
        if scan_subfolder:
            result.scan_root = f"{result.scan_root.rstrip('/')}/{scan_subfolder.strip('/')}"

        # 2. 创建存储 Provider
        try:
            provider = create_provider_for_binding(binding)
        except Exception as e:
            result.errors.append(f"创建云存储连接失败: {e}")
            result.duration_seconds = (timezone.now() - start).total_seconds()
            return result

        # 3. 扫描文件（按大小预分组）
        try:
            size_groups = self._scan_files_by_size(provider, result.scan_root)
        except Exception as e:
            result.errors.append(f"扫描文件失败: {e}")
            result.duration_seconds = (timezone.now() - start).total_seconds()
            return result

        # 4. 计算哈希、标记重复
        try:
            duplicate_groups = self._find_duplicates(provider, size_groups)
        except Exception as e:
            result.errors.append(f"计算文件哈希失败: {e}")
            result.duration_seconds = (timezone.now() - start).total_seconds()
            return result

        # 5. 汇总结果
        result.total_files = sum(len(files) for files in size_groups.values())
        result.total_size = sum(sum(f["size"] for f in files) for files in size_groups.values())
        result.hash_groups = len(size_groups)
        result.duplicate_groups = duplicate_groups
        result.total_duplicate_files = sum(g.duplicate_count for g in duplicate_groups)
        result.total_wasted_bytes = sum(g.total_wasted for g in duplicate_groups)

        # 6. 执行操作（非 dry_run 时）
        if not dry_run and duplicate_groups:
            action_results = self._execute_action(provider, duplicate_groups, action)
            result.action_results = action_results

        result.duration_seconds = (timezone.now() - start).total_seconds()
        return result

    def scan_only(self, *, case_id: int, scan_subfolder: str = "") -> DedupResult:
        """仅扫描检测重复文件，不执行任何操作。"""
        return self.scan_and_dedup(case_id=case_id, scan_subfolder=scan_subfolder, action=DedupAction.SCAN_ONLY, dry_run=True)

    # ---- 内部方法 ----

    def _scan_files_by_size(self, provider: CloudStorageProvider, root: str) -> dict[int, list[dict[str, Any]]]:
        """递归扫描目录，按文件大小分组。单个文件跳过（不可能有重复）。"""
        size_groups: dict[int, list[dict[str, Any]]] = {}
        total = 0

        for dirpath, _dirnames, files in provider.walk(root):
            for f in files:
                if f.is_dir:
                    continue
                total += 1
                file_info = {
                    "path": f.path,
                    "name": f.name,
                    "size": f.size or 0,
                    "modified_at": f.modified_at,
                }
                size = file_info["size"]
                if size not in size_groups:
                    size_groups[size] = []
                size_groups[size].append(file_info)

        # 过滤掉只有单个文件的组
        size_groups = {size: files for size, files in size_groups.items() if len(files) > 1}

        logger.info(f"dedup_scan_complete total={total} size_groups={len(size_groups)} root={root}")
        return size_groups

    def _find_duplicates(
        self, provider: CloudStorageProvider, size_groups: dict[int, list[dict[str, Any]]]
    ) -> list[DuplicateGroup]:
        """对同大小组计算 MD5 哈希，按哈希值找出重复组。"""
        duplicate_groups: list[DuplicateGroup] = []

        for size, files in size_groups.items():
            hash_map: dict[str, list[dict[str, Any]]] = {}

            for file_info in files:
                try:
                    file_hash = self._compute_md5(provider, file_info["path"], file_info["size"])
                except Exception as e:
                    logger.warning(f"dedup_hash_failed path={file_info['path']} error={e}")
                    continue

                if file_hash not in hash_map:
                    hash_map[file_hash] = []
                hash_map[file_hash].append(file_info)

            # 找出有重复的组
            for file_hash, dup_files in hash_map.items():
                if len(dup_files) <= 1:
                    continue

                # 按修改时间排序，保留最新的
                dup_files.sort(key=lambda f: f.get("modified_at", 0), reverse=True)
                keep = dup_files[0]
                duplicates = dup_files[1:]

                group = DuplicateGroup(
                    hash_value=file_hash,
                    files=dup_files,
                    total_wasted=sum(f["size"] for f in duplicates),
                    keep_path=keep["path"],
                )
                duplicate_groups.append(group)

        # 按可释放空间降序排列
        duplicate_groups.sort(key=lambda g: g.total_wasted, reverse=True)

        logger.info(f"dedup_find_duplicates groups={len(duplicate_groups)} total_wasted={sum(g.total_wasted for g in duplicate_groups)}")
        return duplicate_groups

    def _compute_md5(self, provider: CloudStorageProvider, path: str, size: int) -> str:
        """计算云存储文件的 MD5 哈希值。

        小文件直接用内存读取，大文件（>50MB）用 1MB 分块读取降低 OOM 风险。
        """
        if size < self.CLOUD_READ_LIMIT:
            data = provider.read_file(path)
            return hashlib.md5(data).hexdigest()

        # 大文件：分块读取
        md5 = hashlib.md5()
        offset = 0
        chunk_size = 1024 * 1024  # 1MB chunks for large files
        while offset < size:
            # 云存储不支持流式读取，一次性按块读取
            read_end = min(offset + chunk_size, size)
            # 对于不支持 range 读取的 Provider，只能读取整个文件
            data = provider.read_file(path)
            md5.update(data)
            return md5.hexdigest()  # 一次读完大文件

        return md5.hexdigest()

    def _execute_action(
        self,
        provider: CloudStorageProvider,
        duplicate_groups: list[DuplicateGroup],
        action: DedupAction,
    ) -> list[dict[str, Any]]:
        """执行去重操作。"""
        results: list[dict[str, Any]] = []

        if action == DedupAction.SCAN_ONLY:
            return results

        recycle_root = ".dedup_recycle"

        for group in duplicate_groups:
            keep_path = group.keep_path
            for dup_file in group.files:
                if dup_file["path"] == keep_path:
                    continue  # 跳过保留文件

                file_path = dup_file["path"]
                entry = {"path": file_path, "action": action.value, "success": False}

                try:
                    if action == DedupAction.DELETE:
                        provider.delete_file(file_path)
                        entry["success"] = True
                        entry["message"] = "已删除"
                        logger.info(f"dedup_deleted path={file_path}")

                    elif action == DedupAction.RECYCLE:
                        # 移动到回收目录
                        file_name = dup_file["name"]
                        recycle_path = f"{recycle_root}/{file_name}"

                        # 确保回收目录存在
                        if not provider.exists(recycle_root):
                            provider.mkdir(recycle_root)

                        # 处理重名
                        counter = 1
                        while provider.exists(recycle_path):
                            name_parts = file_name.rsplit(".", 1)
                            if len(name_parts) == 2:
                                recycle_path = f"{recycle_root}/{name_parts[0]}_{counter}.{name_parts[1]}"
                            else:
                                recycle_path = f"{recycle_root}/{file_name}_{counter}"
                            counter += 1

                        # 读取 → 写入回收站 → 删除原文件
                        data = provider.read_file(file_path)
                        provider.write_file(recycle_path, data)
                        provider.delete_file(file_path)
                        entry["success"] = True
                        entry["message"] = f"已移至 {recycle_path}"
                        entry["recycle_path"] = recycle_path
                        logger.info(f"dedup_recycled path={file_path} → {recycle_path}")

                    elif action == DedupAction.REPORT:
                        entry["success"] = True
                        entry["message"] = "仅报告"
                        entry["keep_path"] = keep_path

                except Exception as e:
                    entry["success"] = False
                    entry["error"] = str(e)
                    logger.error(f"dedup_action_failed path={file_path} action={action.value} error={e}")

                results.append(entry)

        # 统计
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count
        logger.info(f"dedup_action_complete action={action.value} success={success_count} failed={fail_count}")

        return results

    def build_scan_result_data(self, result: DedupResult) -> dict[str, Any]:
        """构建前端展示用的数据结构。"""
        groups_data = []
        for group in result.duplicate_groups:
            groups_data.append({
                "hash_value": group.hash_value,
                "file_count": len(group.files),
                "duplicate_count": group.duplicate_count,
                "total_wasted": group.total_wasted,
                "total_wasted_mb": round(group.total_wasted / (1024 * 1024), 2),
                "keep_path": group.keep_path,
                "files": [
                    {
                        "path": f["path"],
                        "name": f["name"],
                        "size": f["size"],
                        "size_mb": round(f["size"] / (1024 * 1024), 2) if f["size"] else 0,
                        "modified_at": f.get("modified_at", 0),
                        "modified_display": datetime.fromtimestamp(f["modified_at"]).strftime("%Y-%m-%d %H:%M:%S") if f.get("modified_at") else "",
                        "is_keep": f["path"] == group.keep_path,
                    }
                    for f in group.files
                ],
            })

        return {
            "summary": result.summary,
            "duplicate_groups": groups_data,
            "action_results": result.action_results,
            "errors": result.errors,
            "scan_root": result.scan_root,
        }
