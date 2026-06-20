from django.apps import AppConfig
from django.apps import apps as django_apps


class AutomationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.automation"
    verbose_name = "自动化工具"

    def ready(self) -> None:  # pragma: no cover
        """应用启动时的配置"""
        from django.contrib import admin

        from .admin.scraper.scraper_admin_site import customize_admin_index

        customize_admin_index(admin.site)

        from . import signals

        self._register_sms_recovery_schedule()

    def _register_sms_recovery_schedule(self) -> None:
        """注册短信自动恢复定时任务（每3分钟检查一次卡住的任务）"""
        try:
            from apps.automation.services.sms.task_recovery_service import TaskRecoveryService

            recovery_svc = TaskRecoveryService()
            recovery_svc.schedule_periodic_recovery(interval_minutes=3)
        except Exception:
            import logging

            logger = logging.getLogger("apps.automation")
            logger.debug("短信恢复调度注册跳过（数据库可能未就绪）")
