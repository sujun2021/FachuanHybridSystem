"""
LPR 利率种子数据加载服务测试
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.finance.models import LPRRate
from apps.finance.services.lpr.seed_data_loader import load_lpr_seed_data

SAMPLE_LPR = [
    {"effective_date": "2024-10-21", "rate_1y": "3.10", "rate_5y": "3.60", "source": "中国人民银行官网"},
    {"effective_date": "2024-07-22", "rate_1y": "3.35", "rate_5y": "3.85", "source": "中国人民银行官网"},
    {"effective_date": "2024-02-20", "rate_1y": "3.45", "rate_5y": "3.95", "source": "中国人民银行官网"},
]


def _write_seed_file(tmp_path: Path, data: list) -> Path:
    """将数据写入临时 JSON 文件."""
    file_path = tmp_path / "seed_lpr_rates.json"
    file_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return file_path


class TestLoadLprSeedData:
    """LPR 种子数据加载测试."""

    @pytest.mark.django_db
    def test_loads_when_empty(self, tmp_path: Path) -> None:
        """表为空时成功加载."""
        _write_seed_file(tmp_path, SAMPLE_LPR)
        with patch("apps.finance.services.lpr.seed_data_loader.DATA_DIR", tmp_path):
            result = load_lpr_seed_data()

        assert result["loaded"] == 3
        assert result["skipped"] is False
        assert LPRRate.objects.count() == 3

    @pytest.mark.django_db
    def test_skips_when_not_empty(self) -> None:
        """表非空时跳过加载."""
        LPRRate.objects.create(effective_date="2024-01-01", rate_1y="3.45", rate_5y="4.20")
        result = load_lpr_seed_data()
        assert result["loaded"] == 0
        assert result["skipped"] is True
        assert LPRRate.objects.count() == 1

    @pytest.mark.django_db
    def test_force_reload(self, tmp_path: Path) -> None:
        """强制模式清空并重新加载."""
        LPRRate.objects.create(effective_date="2020-01-01", rate_1y="4.15", rate_5y="4.80")
        _write_seed_file(tmp_path, SAMPLE_LPR)
        with patch("apps.finance.services.lpr.seed_data_loader.DATA_DIR", tmp_path):
            result = load_lpr_seed_data(force=True)

        assert result["loaded"] == 3
        assert LPRRate.objects.count() == 3
        assert not LPRRate.objects.filter(effective_date="2020-01-01").exists()

    @pytest.mark.django_db
    def test_idempotent(self, tmp_path: Path) -> None:
        """重复加载不产生重复数据."""
        _write_seed_file(tmp_path, SAMPLE_LPR)
        with patch("apps.finance.services.lpr.seed_data_loader.DATA_DIR", tmp_path):
            load_lpr_seed_data(force=True)
            load_lpr_seed_data(force=True)

        assert LPRRate.objects.count() == 3

    @pytest.mark.django_db
    def test_data_values_preserved(self, tmp_path: Path) -> None:
        """利率数值和来源正确保存."""
        _write_seed_file(tmp_path, SAMPLE_LPR)
        with patch("apps.finance.services.lpr.seed_data_loader.DATA_DIR", tmp_path):
            load_lpr_seed_data()

        rate = LPRRate.objects.get(effective_date="2024-10-21")
        assert str(rate.rate_1y) == "3.10"
        assert str(rate.rate_5y) == "3.60"
        assert rate.source == "中国人民银行官网"
        assert rate.is_auto_synced is False

    @pytest.mark.django_db
    def test_missing_file_returns_skipped(self, tmp_path: Path) -> None:
        """种子文件不存在时返回 skipped."""
        with patch("apps.finance.services.lpr.seed_data_loader.DATA_DIR", tmp_path):
            result = load_lpr_seed_data()

        assert result["loaded"] == 0
        assert result["skipped"] is True
