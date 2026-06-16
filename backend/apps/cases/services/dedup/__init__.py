"""文件去重服务模块。"""
from .file_dedup_service import FileDeduplicationService, DedupResult, DuplicateGroup

__all__ = ["FileDeduplicationService", "DedupResult", "DuplicateGroup"]
