"""文档解析 API Schema"""

from typing import Any, Dict, Optional

from ninja import Schema


class ParseDocumentRequest(Schema):
    """文档解析请求"""

    backend: str = "auto"
    """后端类型：mineru、local、paddleocr、auto"""

    extract_tables: bool = True
    """是否提取表格"""

    extract_images: bool = False
    """是否提取图片"""

    return_markdown: bool = True
    """是否返回 Markdown 格式"""


class ParseDocumentResponse(Schema):
    """文档解析响应"""

    success: bool
    """是否成功"""

    text: str | None = None
    """纯文本内容"""

    markdown: str | None = None
    """Markdown 格式"""

    metadata: dict[str, Any] | None = None
    """元数据"""

    parse_method: str | None = None
    """解析方法"""

    error: str | None = None
    """错误信息（如果失败）"""


class ExtractTextRequest(Schema):
    """文本提取请求"""

    backend: str = "auto"
    """后端类型"""

    max_length: int | None = None
    """最大文本长度"""


class ExtractTextResponse(Schema):
    """文本提取响应"""

    success: bool
    """是否成功"""

    text: str
    """提取的文本"""

    method: str | None = None
    """使用的方法"""

    metadata: dict[str, Any] | None = None
    """元数据"""

    error: str | None = None
    """错误信息（如果失败）"""
