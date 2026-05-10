"""批量分析异步任务包

Django Q2 入口点通过此模块的路径引用：
  - apps.workbench.tasks.run_batch_analysis
  - apps.workbench.tasks.run_batch_retry
"""

from .batch_runner import run_batch_analysis, run_batch_retry
from .registry import TaskRegistry, task_registry
from .summary import build_detail_zip_sync

__all__ = [
    "TaskRegistry",
    "build_detail_zip_sync",
    "run_batch_analysis",
    "run_batch_retry",
    "task_registry",
]
