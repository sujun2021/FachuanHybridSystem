"""选题建议服务 — 使用 LLM 搜索热点法律事件，给出选题建议。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from apps.core.interfaces import ServiceLocator
from apps.core.llm.structured_output import clean_text, parse_model_content

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是一位资深的法律内容编辑，专门为普通读者寻找有故事性的法律选题。

请根据当前社会热点和近期常见纠纷类型，推荐 5 个适合写成"街坊邻居聊案件"风格故事的选题。

要求：
1. 选题应贴近普通人的日常生活（邻里纠纷、家庭矛盾、消费维权、劳动争议等）
2. 每个选题要有趣味性，能引起读者好奇心
3. 提供一个简短的描述说明为什么这个选题有意思
4. 给出建议的检索关键词（用于在裁判文书库中搜索）

请严格按照 JSON 格式输出。
"""


class TopicSuggestion(BaseModel):
    title: str = Field(description="选题标题")
    description: str = Field(description="选题简介，说明为什么这个选题有意思")
    suggested_keyword: str = Field(description="建议的检索关键词")


class TopicSuggestions(BaseModel):
    topics: list[TopicSuggestion] = Field(description="选题建议列表")


@dataclass
class TopicResult:
    topics: list[dict[str, str]]
    model: str
    token_usage: dict[str, int]


class TopicService:
    """使用 LLM 生成选题建议。"""

    async def suggest(self) -> TopicResult:
        llm_service = ServiceLocator.get_llm_service()

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": "请推荐 5 个适合写成法律故事的选题。"},
        ]

        response = await llm_service.achat(
            messages=messages,
            model="mimo-v2.5-pro",
            temperature=0.8,
        )

        content = clean_text(response.content)
        parsed = parse_model_content(content, TopicSuggestions)

        return TopicResult(
            topics=[t.model_dump() for t in parsed.topics],
            model=response.model,
            token_usage={
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
        )
