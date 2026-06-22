"""Stub: http_login plugin has been moved to plugins/court_automation/login/http_login/

This file re-exports from the plugin for backward compatibility.
"""

try:
    from plugins.court_automation.login.http_login import *  # noqa: F401,F403
    from plugins.court_automation.login.http_login import is_available  # noqa: F401

except ImportError:
    pass
