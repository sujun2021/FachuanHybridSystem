"""
爬虫核心服务
"""

try:
    from .captcha_recognizer import CaptchaRecognizer, ManualCaptchaRecognizer, get_captcha_recognizer
except ImportError:
    CaptchaRecognizer = None  # type: ignore[assignment,misc]
    ManualCaptchaRecognizer = None  # type: ignore[assignment,misc]
    get_captcha_recognizer = None  # type: ignore[assignment]
from .exceptions import (
    BrowserConfigurationError,
    BrowserCreationError,
    CaptchaRecognitionError,
    LoginError,
    ScraperException,
)
from .monitor_service import MonitorService
from .screenshot_utils import ScreenshotUtils
from .security_service import SecurityService
from .validator_service import ValidatorService

__all__ = [
    "CaptchaRecognizer",
    "ManualCaptchaRecognizer",
    "get_captcha_recognizer",
    "SecurityService",
    "ValidatorService",
    "MonitorService",
    "ScreenshotUtils",
    "ScraperException",
    "BrowserCreationError",
    "BrowserConfigurationError",
    "CaptchaRecognitionError",
    "LoginError",
]
