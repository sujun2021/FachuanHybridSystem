"""Markdown → 公众号 HTML 转换服务（专业排版）。

支持多种主题，输出内联样式的 HTML，可直接通过剪贴板粘贴到公众号 ProseMirror 编辑器。
参考 doocs/md 和 mdnice 的排版设计。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import markdown  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


@dataclass
class ThemeConfig:
    """排版主题配置。"""

    name: str = "default"

    # 主色调
    primary_color: str = "#0F4C81"
    secondary_color: str = "#1a73e8"

    # 字体
    font_family: str = "-apple-system,BlinkMacSystemFont,'Helvetica Neue','PingFang SC','Microsoft YaHei',sans-serif"
    font_size: str = "15px"
    line_height: str = "1.8"

    # 代码高亮主题（内联样式）
    code_theme: str = "github"  # github / dark / green

    # 分隔线样式
    hr_style: str = "gradient"  # gradient / dot / dash


# ── 预定义主题 ─────────────────────────────────────────────────────────────

THEME_CLASSIC = ThemeConfig(
    name="classic",
    primary_color="#0F4C81",
    code_theme="github",
    hr_style="gradient",
)

THEME_ELEGANT = ThemeConfig(
    name="elegant",
    primary_color="#6C5CE7",
    code_theme="dark",
    hr_style="gradient",
)

THEME_GREEN = ThemeConfig(
    name="green",
    primary_color="#07c160",
    code_theme="green",
    hr_style="dot",
)

THEMES: dict[str, ThemeConfig] = {
    "classic": THEME_CLASSIC,
    "elegant": THEME_ELEGANT,
    "green": THEME_GREEN,
}


# ── GFM Alert / Callout 支持 ──────────────────────────────────────────────

_ALERT_TYPES: dict[str, tuple[str, str]] = {
    # (标题, 颜色)
    "NOTE": ("📘 注意", "#478be6"),
    "TIP": ("💡 提示", "#57ab5a"),
    "IMPORTANT": ("❗ 重要", "#986ee2"),
    "WARNING": ("⚠️ 警告", "#c69026"),
    "CAUTION": ("🔴 危险", "#e5534b"),
    "INFO": ("ℹ️ 信息", "#93c5fd"),
    "SUCCESS": ("✅ 成功", "#57ab5a"),
    "QUESTION": ("❓ 问题", "#c69026"),
    "DANGER": ("🚨 危险", "#e5534b"),
}


def _build_callout_html(alert_type: str, title: str, color: str, content: str) -> str:
    """构建 callout 盒子的内联样式 HTML。"""
    # 清理内容中的 <p> 标签
    content = content.strip()
    content = re.sub(r"^<p>", "", content)
    content = re.sub(r"</p>$", "", content)

    return (
        f'<section style="margin:16px 0;padding:12px 16px;'
        f"border-left:4px solid {color};"
        f"background:{color}11;"
        f'border-radius:0 6px 6px 0;">'
        f'<p style="margin:0 0 6px;font-weight:bold;font-size:15px;color:{color};">'
        f"{title}</p>"
        f'<p style="margin:0;font-size:14px;color:#555;line-height:1.7;">'
        f"{content}</p>"
        f"</section>"
    )


def _process_alerts(html: str) -> str:
    """将 GFM alert 语法转换为 callout 盒子。

    支持格式：
        > [!NOTE]
        > 内容

        > [!WARNING]
        > 警告内容
    """
    for alert_type, (title, color) in _ALERT_TYPES.items():
        # 匹配 > [!TYPE]\n> content 模式
        pattern = re.compile(
            rf"<blockquote>\s*<p>\[!{alert_type}\]</p>\s*(.*?)</blockquote>",
            re.DOTALL,
        )
        html = pattern.sub(
            lambda m: _build_callout_html(alert_type, title, color, m.group(1)),
            html,
        )
    return html


# ── 主题样式生成 ────────────────────────────────────────────────────────────


def _get_styles(theme: ThemeConfig) -> dict[str, str]:
    """根据主题生成内联样式映射。"""
    c = theme.primary_color
    font = theme.font_family
    fs = theme.font_size
    lh = theme.line_height

    # 代码高亮配色
    code_styles = {
        "github": {
            "inline_code": "background:rgba(27,31,35,0.06);color:#c7254e;padding:2px 6px;border-radius:3px;font-size:0.9em;font-family:Consolas,Monaco,'Courier New',monospace;",
            "pre": "background:#f6f8fa;padding:16px;border-radius:6px;overflow-x:auto;margin:16px 0;font-size:13px;line-height:1.6;font-family:Consolas,Monaco,'Courier New',monospace;white-space:pre-wrap;word-wrap:break-word;",
        },
        "dark": {
            "inline_code": "background:rgba(255,255,255,0.1);color:#e06c75;padding:2px 6px;border-radius:3px;font-size:0.9em;font-family:Consolas,Monaco,'Courier New',monospace;",
            "pre": "background:#282c34;color:#abb2bf;padding:16px;border-radius:6px;overflow-x:auto;margin:16px 0;font-size:13px;line-height:1.6;font-family:Consolas,Monaco,'Courier New',monospace;white-space:pre-wrap;word-wrap:break-word;",
        },
        "green": {
            "inline_code": "background:#f0faf0;color:#07c160;padding:2px 6px;border-radius:3px;font-size:0.9em;font-weight:bold;font-family:Consolas,Monaco,'Courier New',monospace;",
            "pre": "background:#f0faf0;border:1px solid #e0f5e0;padding:16px;border-radius:6px;overflow-x:auto;margin:16px 0;font-size:13px;line-height:1.6;font-family:Consolas,Monaco,'Courier New',monospace;white-space:pre-wrap;word-wrap:break-word;",
        },
    }
    code = code_styles.get(theme.code_theme, code_styles["github"])

    # 分隔线样式
    hr_styles = {
        "gradient": f"height:1px;border:none;margin:2em 0;background:linear-gradient(to right,rgba(0,0,0,0),{c}40,rgba(0,0,0,0));",
        "dot": f"border:none;border-top:2px dotted {c}40;margin:2em 0;",
        "dash": f"border:none;border-top:2px dashed {c}30;margin:2em 0;",
    }
    hr = hr_styles.get(theme.hr_style, hr_styles["gradient"])

    return {
        "section": f"font-family:{font};font-size:{fs};line-height:{lh};color:#333;word-wrap:break-word;overflow-wrap:break-word;",
        # 标题：h1 居中 + 底部边框
        "h1": (
            f"display:table;margin:2em auto 1em;padding:0 16px 10px;"
            f"font-size:22px;font-weight:bold;color:#1a1a1a;"
            f"border-bottom:3px solid {c};text-align:center;"
        ),
        # h2：左侧彩色边框 + 浅色背景
        "h2": (
            f"margin:28px 0 14px;padding:8px 14px;"
            f"font-size:18px;font-weight:bold;color:#1a1a1a;"
            f"border-left:5px solid {c};"
            f"background:{c}08;"
        ),
        # h3：圆角边框 + 浅色背景
        "h3": (
            f"margin:22px 0 10px;padding:6px 14px;"
            f"font-size:16px;font-weight:bold;color:#333;"
            f"border:1px solid {c}20;"
            f"border-left:4px solid {c};"
            f"background:{c}06;"
            f"border-radius:0 6px 6px 0;"
        ),
        "h4": "margin:18px 0 8px;font-size:15px;font-weight:bold;color:#333;",
        # 正文
        "p": f"font-size:{fs};margin:10px 0;text-align:justify;line-height:{lh};letter-spacing:0.5px;",
        # 加粗：主色调
        "strong": f"color:{c};font-weight:bold;",
        "em": "font-style:italic;color:#666;",
        # 引用块：优雅卡片式
        "blockquote": (
            f"font-style:normal;padding:12px 16px;margin:16px 0;"
            f"border-left:4px solid {c};border-radius:0 8px 8px 0;"
            f"color:#555;background:{c}08;font-size:14px;line-height:1.7;"
        ),
        # 列表
        "ul": "padding-left:24px;margin:10px 0;",
        "ol": "padding-left:24px;margin:10px 0;",
        "li": f"font-size:{fs};margin:6px 0;line-height:{lh};",
        # 代码
        "code": code["inline_code"],
        "pre": code["pre"],
        # 分隔线
        "hr": hr,
        # 图片
        "img": "display:block;max-width:100%;height:auto;margin:12px auto;border-radius:6px;",
        # 表格
        "table": (
            "width:100%;border-collapse:separate;border-spacing:0;"
            "margin:16px 0;font-size:14px;"
            "border-radius:8px;overflow:hidden;"
            "box-shadow:0 2px 8px rgba(0,0,0,0.06);"
        ),
        "th": (f"padding:10px 14px;text-align:left;font-weight:bold;background:{c};color:#fff;font-size:14px;"),
        "td": "padding:10px 14px;text-align:left;border-bottom:1px solid #eee;font-size:14px;",
        # 链接
        "a": f"color:{c};text-decoration:none;border-bottom:1px solid {c}40;",
    }


# ── 内联样式应用 ────────────────────────────────────────────────────────────


def _apply_inline_styles(html: str, styles: dict[str, str]) -> str:
    """将内联样式应用到 HTML 元素上。"""
    for tag, style in styles.items():
        if tag == "section":
            continue
        # 匹配 <tag> 或 <tag ...>，但不重复添加 style
        pattern = rf"<{tag}(?![^>]*style=)(\s|>)"
        replacement = f'<{tag} style="{style}"\\1'
        html = re.sub(pattern, replacement, html)
    return html


def _wrap_section(html: str, styles: dict[str, str]) -> str:
    """用 section 包裹 HTML 并添加全局样式。"""
    return f'<section style="{styles["section"]}">{html}</section>'


# ── 主转换函数 ──────────────────────────────────────────────────────────────


def convert_markdown_to_wechat_html(
    md_content: str,
    theme: str | ThemeConfig = "classic",
) -> str:
    """将 Markdown 转换为公众号支持的内联样式 HTML。

    支持 GFM alert 语法（> [!NOTE] 等）和多种排版主题。

    Args:
        md_content: Markdown 格式的文本
        theme: 主题名称（classic/elegant/green）或 ThemeConfig 对象

    Returns:
        内联样式的 HTML 字符串，可直接粘贴到公众号编辑器
    """
    # 解析主题
    if isinstance(theme, str):
        theme_config = THEMES.get(theme, THEME_CLASSIC)
    else:
        theme_config = theme

    # 移除第一行标题（公众号标题单独设置）
    lines = md_content.strip().split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    md_content = "\n".join(lines).strip()

    # 转换 Markdown → HTML
    html = markdown.markdown(
        md_content,
        extensions=[
            "markdown.extensions.tables",
            "markdown.extensions.fenced_code",
            "markdown.extensions.codehilite",
            "markdown.extensions.nl2br",
        ],
        extension_configs={
            "markdown.extensions.codehilite": {
                "css_class": "highlight",
                "noclasses": True,
            },
        },
    )

    # 处理 GFM alert → callout 盒子
    html = _process_alerts(html)

    # 生成主题样式
    styles = _get_styles(theme_config)

    # 应用内联样式
    html = _apply_inline_styles(html, styles)

    # 处理表格行交替背景色
    html = _add_table_striping(html, theme_config.primary_color)

    # 用 section 包裹
    html = _wrap_section(html, styles)

    return html


def _add_table_striping(html: str, color: str) -> str:
    """为表格奇数行添加浅色背景。"""
    # 为奇数 td 行添加背景（通过在 <tr> 上添加样式）
    counter = 0

    def _replace_tr(match: re.Match) -> str:
        nonlocal counter
        counter += 1
        if counter % 2 == 0:
            return f'<tr style="background:{color}05;">'
        return match.group(0)

    html = re.sub(r"<tr>", _replace_tr, html)
    return html


def extract_summary(md_content: str, max_length: int = 120) -> str:
    """从 Markdown 内容中提取摘要（用于公众号文章摘要）。"""
    # 移除标题行
    lines = md_content.strip().split("\n")
    text_lines = [line for line in lines if not line.startswith("#")]

    # 移除 Markdown 标记
    text = " ".join(text_lines)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > max_length:
        text = text[:max_length] + "..."

    return text
