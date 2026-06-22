"""Stub: Token services moved to plugins/court_automation/token/"""

try:
    from plugins.court_automation.token import (  # noqa: F401
        AccountSelectionStrategy,
        AutoLoginService,
        AutoTokenAcquisitionService,
    )
except ImportError:
    AccountSelectionStrategy = None  # type: ignore[assignment,misc]
    AutoLoginService = None  # type: ignore[assignment,misc]
    AutoTokenAcquisitionService = None  # type: ignore[assignment,misc]
