from __future__ import annotations

import logging
import sys

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FinanceConfig(AppConfig):
    """Finance app configuration."""

    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "apps.finance"
    verbose_name: str = "金融工具"

    def ready(self) -> None:  # pragma: no cover
        """App ready hook."""
        from django.db.models.signals import post_migrate

        post_migrate.connect(self._on_post_migrate, sender=self)

    def _on_post_migrate(self, sender, **kwargs):  # type: ignore[no-untyped-def]
        """数据库迁移完成后自动加载 LPR 种子数据(仅表为空时)."""
        if "test" in sys.argv or "pytest" in sys.modules:
            return
        try:
            from apps.finance.services.lpr.seed_data_loader import load_lpr_seed_data

            load_lpr_seed_data()
        except Exception as e:
            logger.warning("LPR 种子数据自动加载跳过: %s", e)
