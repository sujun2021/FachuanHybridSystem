"""
ddddocr 验证码识别插件

从上游开源代码迁移至此的 ddddocr 验证码识别实现。
当 plugins.captcha_ocr 模块存在时，captcha_recognizer.py 会自动加载。

依赖：ddddocr（需自行安装：uv add ddddocr）
"""

import logging
from typing import Any, cast

from apps.automation.services.scraper.core.captcha_recognizer import CaptchaRecognizer

logger = logging.getLogger("apps.automation")

PLUGIN_NAME = "captcha_ocr"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "ddddocr 验证码自动识别插件"


class DdddocrRecognizer(CaptchaRecognizer):
    """
    使用 ddddocr 库实现的验证码识别器

    ddddocr 是一个开源的 OCR 库，专门用于识别验证码。
    这个实现提供了基本的验证码识别功能，适用于大多数简单验证码。

    Attributes:
        ocr: ddddocr.DdddOcr 实例，用于执行实际的识别工作

    Example:
        >>> recognizer = DdddocrRecognizer()
        >>> with open('captcha.png', 'rb') as f:
        ...     image_bytes = f.read()
        >>> result = recognizer.recognize(image_bytes)
        >>> logger.info(result)  # '1234'
    """

    def __init__(self, show_ad: bool = False):  # pragma: no cover
        """
        初始化 ddddocr 识别器

        Args:
            show_ad: 是否显示 ddddocr 的广告信息，默认 False

        Raises:
            ImportError: 如果 ddddocr 库未安装
        """
        try:
            import ddddocr

            self.ocr = ddddocr.DdddOcr(show_ad=show_ad)
            logger.info("✅ DdddocrRecognizer 初始化成功")
        except ImportError as e:
            logger.error("❌ ddddocr 未安装，请运行: uv add ddddocr")
            raise ImportError("ddddocr 库未安装。请运行: uv add ddddocr") from e

    def recognize(self, image_bytes: bytes) -> str | None:  # pragma: no cover
        """
        从图片字节流识别验证码

        Args:
            image_bytes: 图片的字节数据

        Returns:
            识别出的验证码文本（已去除空格），识别失败返回 None
        """
        if not image_bytes:
            logger.warning("⚠️ 图片字节流为空")
            return None

        try:
            result = self.ocr.classification(image_bytes)
            cleaned_result = result.strip().replace(" ", "")
            logger.info(f"✅ 验证码识别成功: {cleaned_result}")
            return cast(str | None, cleaned_result)
        except Exception as e:
            logger.error(f"❌ 验证码识别失败: {e}", exc_info=True)
            return None

    def recognize_from_element(self, page: Any, selector: str) -> str | None:  # pragma: no cover
        """
        从页面元素识别验证码

        Args:
            page: Playwright Page 对象
            selector: 验证码图片元素的 CSS 选择器

        Returns:
            识别出的验证码文本，识别失败返回 None
        """
        try:
            element = page.locator(selector)
            element.wait_for(state="visible", timeout=5000)
            image_bytes = element.screenshot()
            return self.recognize(image_bytes)
        except Exception as e:
            logger.error(f"❌ 从页面元素获取验证码失败 (selector: {selector}): {e}", exc_info=True)
            return None
