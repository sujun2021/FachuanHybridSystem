"""
Automation tasks package.

Re-exports all task callables so string-based imports
(for example Django Q: ``apps.automation.tasks.execute_scraper_task``)
keep working.
"""

from .document_delivery_tasks import query_document_delivery_via_playwright
from .scraping_tasks import (
    check_stuck_tasks,
    execute_preservation_quote_task,
    execute_scraper_task,
    process_pending_tasks,
    reset_running_tasks,
    startup_check,
)

__all__ = [
    "check_stuck_tasks",
    "execute_preservation_quote_task",
    "execute_scraper_task",
    "process_pending_tasks",
    "query_document_delivery_via_playwright",
    "reset_running_tasks",
    "startup_check",
]
