"""
种子数据加载服务测试
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from apps.core.models import CauseOfAction, Court
from apps.core.services.seed_data_loader import load_cause_seed_data, load_court_seed_data

SAMPLE_CAUSES = [
    {"code": "1", "name": "人格权纠纷", "case_type": "civil", "parent_code": None, "level": 1},
    {"code": "1.1", "name": "生命权纠纷", "case_type": "civil", "parent_code": "1", "level": 2},
    {"code": "1.1.1", "name": "交通事故", "case_type": "civil", "parent_code": "1.1", "level": 3},
]

SAMPLE_COURTS = [
    {"code": "000", "name": "最高人民法院", "parent_code": None, "level": 1, "province": ""},
    {"code": "100", "name": "北京市高级人民法院", "parent_code": "000", "level": 2, "province": "北京市"},
    {"code": "101", "name": "北京市第一中级人民法院", "parent_code": "100", "level": 3, "province": "北京市"},
]


def _write_seed_file(tmp_path: Path, filename: str, data: list) -> Path:
    """将数据写入临时 JSON 文件."""
    file_path = tmp_path / filename
    file_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return file_path


# =====================================================================
# 案由种子数据
# =====================================================================


class TestLoadCauseSeedData:
    """案由种子数据加载测试."""

    @pytest.mark.django_db
    def test_loads_when_empty(self, tmp_path: Path) -> None:
        """表为空时成功加载."""
        seed_file = _write_seed_file(tmp_path, "seed_causes_of_action.json", SAMPLE_CAUSES)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            result = load_cause_seed_data()

        assert result["loaded"] == 3
        assert result["skipped"] is False
        assert CauseOfAction.objects.count() == 3

    @pytest.mark.django_db
    def test_skips_when_not_empty(self) -> None:
        """表非空时跳过加载."""
        CauseOfAction.objects.create(code="existing", name="已有", case_type="civil", level=1)
        result = load_cause_seed_data()
        assert result["loaded"] == 0
        assert result["skipped"] is True
        assert CauseOfAction.objects.count() == 1

    @pytest.mark.django_db
    def test_force_reload(self, tmp_path: Path) -> None:
        """强制模式清空并重新加载."""
        CauseOfAction.objects.create(code="old", name="旧数据", case_type="civil", level=1)
        seed_file = _write_seed_file(tmp_path, "seed_causes_of_action.json", SAMPLE_CAUSES)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            result = load_cause_seed_data(force=True)

        assert result["loaded"] == 3
        assert CauseOfAction.objects.count() == 3
        assert not CauseOfAction.objects.filter(code="old").exists()

    @pytest.mark.django_db
    def test_parent_resolution(self, tmp_path: Path) -> None:
        """parent FK 正确关联."""
        _write_seed_file(tmp_path, "seed_causes_of_action.json", SAMPLE_CAUSES)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            load_cause_seed_data()

        root = CauseOfAction.objects.get(code="1")
        child = CauseOfAction.objects.get(code="1.1")
        grandchild = CauseOfAction.objects.get(code="1.1.1")

        assert root.parent is None
        assert child.parent_id == root.pk
        assert grandchild.parent_id == child.pk

    @pytest.mark.django_db
    def test_missing_file_returns_skipped(self, tmp_path: Path) -> None:
        """种子文件不存在时返回 skipped."""
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            result = load_cause_seed_data()

        assert result["loaded"] == 0
        assert result["skipped"] is True

    @pytest.mark.django_db
    def test_idempotent(self, tmp_path: Path) -> None:
        """重复加载不产生重复数据."""
        _write_seed_file(tmp_path, "seed_causes_of_action.json", SAMPLE_CAUSES)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            load_cause_seed_data(force=True)
            load_cause_seed_data(force=True)

        assert CauseOfAction.objects.count() == 3


# =====================================================================
# 法院种子数据
# =====================================================================


class TestLoadCourtSeedData:
    """法院种子数据加载测试."""

    @pytest.mark.django_db
    def test_loads_when_empty(self, tmp_path: Path) -> None:
        """表为空时成功加载."""
        _write_seed_file(tmp_path, "seed_courts.json", SAMPLE_COURTS)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            result = load_court_seed_data()

        assert result["loaded"] == 3
        assert result["skipped"] is False
        assert Court.objects.count() == 3

    @pytest.mark.django_db
    def test_skips_when_not_empty(self) -> None:
        """表非空时跳过加载."""
        Court.objects.create(code="existing", name="已有法院", level=1)
        result = load_court_seed_data()
        assert result["loaded"] == 0
        assert result["skipped"] is True
        assert Court.objects.count() == 1

    @pytest.mark.django_db
    def test_parent_resolution(self, tmp_path: Path) -> None:
        """parent FK 正确关联."""
        _write_seed_file(tmp_path, "seed_courts.json", SAMPLE_COURTS)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            load_court_seed_data()

        supreme = Court.objects.get(code="000")
        beijing_high = Court.objects.get(code="100")
        beijing_first = Court.objects.get(code="101")

        assert supreme.parent is None
        assert beijing_high.parent_id == supreme.pk
        assert beijing_first.parent_id == beijing_high.pk

    @pytest.mark.django_db
    def test_province_preserved(self, tmp_path: Path) -> None:
        """省份信息正确保存."""
        _write_seed_file(tmp_path, "seed_courts.json", SAMPLE_COURTS)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            load_court_seed_data()

        assert Court.objects.get(code="000").province == ""
        assert Court.objects.get(code="100").province == "北京市"

    @pytest.mark.django_db
    def test_idempotent(self, tmp_path: Path) -> None:
        """重复加载不产生重复数据."""
        _write_seed_file(tmp_path, "seed_courts.json", SAMPLE_COURTS)
        with patch("apps.core.services.seed_data_loader.DATA_DIR", tmp_path):
            load_court_seed_data(force=True)
            load_court_seed_data(force=True)

        assert Court.objects.count() == 3
