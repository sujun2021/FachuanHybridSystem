"""案件收支类别字典模型"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    pass


class PaymentRecordCategory(models.Model):
    """可自定义的款项用途类别（收入/支出）"""

    id: int
    name = models.CharField(max_length=100, verbose_name=_("名称"))
    is_income = models.BooleanField(
        default=True,
        verbose_name=_("是否收入类别"),
        help_text=_("True=收入类别（如回款），False=支出类别（如差旅费）"),
    )
    is_system = models.BooleanField(
        default=False,
        verbose_name=_("系统内置"),
        help_text=_("系统内置类别不可删除，用户自定义的类别可删除"),
    )
    sort_order = models.IntegerField(default=0, verbose_name=_("排序顺序"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("创建时间"))

    class Meta:
        verbose_name = _("款项用途")
        verbose_name_plural = _("款项用途")
        ordering = ["is_income", "sort_order", "name"]
        indexes: ClassVar = [
            models.Index(fields=["is_income"]),
            models.Index(fields=["is_system"]),
        ]

    def __str__(self) -> str:
        direction = _("收入") if self.is_income else _("支出")
        return f"{self.name}（{direction}）"

    @classmethod
    def get_builtin_categories(cls) -> list[dict]:
        return [
            {"name": "相对方主动支付", "is_income": True, "is_system": True, "sort_order": 10},
            {"name": "执行回款", "is_income": True, "is_system": True, "sort_order": 20},
            {"name": "律师费", "is_income": False, "is_system": True, "sort_order": 10},
            {"name": "差旅费", "is_income": False, "is_system": True, "sort_order": 20},
            {"name": "诉讼保全费", "is_income": False, "is_system": True, "sort_order": 30},
            {"name": "评估费", "is_income": False, "is_system": True, "sort_order": 40},
            {"name": "公证费", "is_income": False, "is_system": True, "sort_order": 50},
            {"name": "诉讼费", "is_income": False, "is_system": True, "sort_order": 60},
            {"name": "其他费用", "is_income": False, "is_system": True, "sort_order": 99},
        ]

    @classmethod
    def ensure_builtin_categories(cls) -> None:
        """确保系统内置类别存在，不存在则创建"""
        for cat_data in cls.get_builtin_categories():
            cls.objects.get_or_create(
                name=cat_data["name"],
                defaults={
                    "is_income": cat_data["is_income"],
                    "is_system": cat_data["is_system"],
                    "sort_order": cat_data["sort_order"],
                },
            )
