"""Business logic services."""

from typing import Any


class PromptTemplateService:
    def get_system_template(self, name: str) -> str | None:
        # PromptVersionService 已移除，始终使用默认 prompt（由调用方提供 fallback）
        return None

    def replace_variables(self, template: str, variables: dict[str, Any]) -> str:  # pragma: no cover
        from .placeholder_render_service import PlaceholderRenderService

        rendered, _stats = PlaceholderRenderService().render(template, variables, syntax="single", keep_unmatched=True)
        return rendered
