"""工作台 App 配置"""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class WorkbenchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workbench"
    verbose_name = _("工作台")
