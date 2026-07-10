"""Unit tests for JTNAdapter mapping methods and oa_firm_registry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.oa_filing.services.oa_firm_registry import SUPPORTED_SITES, create_adapter, get_adapter_class
from apps.oa_filing.services.oa_scripts.jtn.adapter import JTNAdapter


@pytest.fixture
def adapter():
    return JTNAdapter("test_account", "fake_secret")  # pragma: allowlist secret


# ──────────── _map_case_category ────────────


class TestMapCaseCategory:
    def test_civil(self, adapter):
        case = MagicMock(case_type="civil")
        assert adapter._map_case_category(case) == "03"

    def test_criminal(self, adapter):
        case = MagicMock(case_type="criminal")
        assert adapter._map_case_category(case) == "05"

    def test_administrative(self, adapter):
        case = MagicMock(case_type="administrative")
        assert adapter._map_case_category(case) == "04"

    def test_labor(self, adapter):
        case = MagicMock(case_type="labor")
        assert adapter._map_case_category(case) == "03"

    def test_intl(self, adapter):
        case = MagicMock(case_type="intl")
        assert adapter._map_case_category(case) == "06"

    def test_execution(self, adapter):
        case = MagicMock(case_type="execution")
        assert adapter._map_case_category(case) == "03"

    def test_bankruptcy(self, adapter):
        case = MagicMock(case_type="bankruptcy")
        assert adapter._map_case_category(case) == "03"

    def test_special(self, adapter):
        case = MagicMock(case_type="special")
        assert adapter._map_case_category(case) == "02"

    def test_advisor(self, adapter):
        case = MagicMock(case_type="advisor")
        assert adapter._map_case_category(case) == "01"

    def test_unknown_defaults_to_civil(self, adapter):
        case = MagicMock(case_type="unknown_type")
        assert adapter._map_case_category(case) == "03"

    def test_none_defaults_to_civil(self, adapter):
        case = MagicMock(case_type=None)
        assert adapter._map_case_category(case) == "03"


# ──────────── _map_case_stage ────────────


class TestMapCaseStage:
    def test_civil_first_trial(self, adapter):
        case = MagicMock(case_type="civil", current_stage="first_trial")
        assert adapter._map_case_stage(case) == "0301"

    def test_civil_second_trial(self, adapter):
        case = MagicMock(case_type="civil", current_stage="second_trial")
        assert adapter._map_case_stage(case) == "0305"

    def test_civil_enforcement(self, adapter):
        case = MagicMock(case_type="civil", current_stage="enforcement")
        assert adapter._map_case_stage(case) == "0314"

    def test_administrative_review(self, adapter):
        case = MagicMock(case_type="administrative", current_stage="administrative_review")
        assert adapter._map_case_stage(case) == "0401"

    def test_administrative_first_trial(self, adapter):
        case = MagicMock(case_type="administrative", current_stage="first_trial")
        assert adapter._map_case_stage(case) == "0402"

    def test_criminal_investigation(self, adapter):
        case = MagicMock(case_type="criminal", current_stage="investigation")
        assert adapter._map_case_stage(case) == "0501"

    def test_criminal_first_trial(self, adapter):
        case = MagicMock(case_type="criminal", current_stage="first_trial")
        assert adapter._map_case_stage(case) == "0503"

    def test_advisor_no_stage(self, adapter):
        case = MagicMock(case_type="advisor", current_stage="first_trial")
        assert adapter._map_case_stage(case) == ""

    def test_special_no_stage(self, adapter):
        case = MagicMock(case_type="special", current_stage="first_trial")
        assert adapter._map_case_stage(case) == ""

    def test_unknown_stage_defaults_civil(self, adapter):
        case = MagicMock(case_type="civil", current_stage="unknown_stage")
        assert adapter._map_case_stage(case) == "0301"

    def test_none_stage_defaults_civil(self, adapter):
        case = MagicMock(case_type="civil", current_stage=None)
        assert adapter._map_case_stage(case) == "0301"


# ──────────── _map_fee_mode ────────────


class TestMapFeeMode:
    def test_fixed(self, adapter):
        contract = MagicMock(fee_mode="FIXED")
        assert adapter._map_fee_mode(contract) == "01"

    def test_semi_risk(self, adapter):
        contract = MagicMock(fee_mode="SEMI_RISK")
        assert adapter._map_fee_mode(contract) == "02"

    def test_full_risk(self, adapter):
        contract = MagicMock(fee_mode="FULL_RISK")
        assert adapter._map_fee_mode(contract) == "02"

    def test_custom(self, adapter):
        contract = MagicMock(fee_mode="CUSTOM")
        assert adapter._map_fee_mode(contract) == "01"

    def test_unknown_defaults(self, adapter):
        contract = MagicMock(fee_mode="UNKNOWN")
        assert adapter._map_fee_mode(contract) == "01"

    def test_none_defaults(self, adapter):
        contract = MagicMock(fee_mode=None)
        assert adapter._map_fee_mode(contract) == "01"


# ──────────── _map_kindtype ────────────


class TestMapKindtype:
    def test_non_litigation_returns_empty(self, adapter):
        kind, kind_sed = adapter._map_kindtype("03", [])
        assert kind == ""
        assert kind_sed == ""

    def test_advisor_enterprise(self, adapter):
        party = MagicMock()
        party.client = MagicMock(client_type="legal")
        kind, kind_sed = adapter._map_kindtype("01", [party])
        assert kind == "KindType01_01"
        assert kind_sed == "KindType01_0103"

    def test_advisor_natural_person(self, adapter):
        party = MagicMock()
        party.client = MagicMock(client_type="natural")
        kind, kind_sed = adapter._map_kindtype("01", [party])
        assert kind == "KindType01_05"
        assert kind_sed == ""

    def test_special_enterprise(self, adapter):
        party = MagicMock()
        party.client = MagicMock(client_type="legal")
        kind, kind_sed = adapter._map_kindtype("02", [party])
        assert kind == "KindType02_01"
        assert kind_sed == ""

    def test_special_natural_person(self, adapter):
        party = MagicMock()
        party.client = MagicMock(client_type="natural")
        kind, kind_sed = adapter._map_kindtype("02", [party])
        assert kind == "KindType02_05"
        assert kind_sed == ""

    def test_no_parties_enterprise(self, adapter):
        kind, kind_sed = adapter._map_kindtype("01", [])
        assert kind == "KindType01_01"
        assert kind_sed == "KindType01_0103"


# ──────────── oa_firm_registry ────────────


class TestFirmRegistry:
    def test_supported_sites(self):
        assert "金诚同达OA" in SUPPORTED_SITES
        assert len(SUPPORTED_SITES) >= 1

    def test_get_adapter_class(self):
        cls = get_adapter_class("金诚同达OA")
        assert cls is JTNAdapter

    def test_get_adapter_class_unsupported(self):
        with pytest.raises(ValueError, match="不支持"):
            get_adapter_class("不存在的律所")

    def test_create_adapter(self):
        adapter = create_adapter("金诚同达OA", "test_acc", "fake_secret")  # pragma: allowlist secret
        assert isinstance(adapter, JTNAdapter)
        assert adapter._account == "test_acc"
        assert adapter._password == "fake_secret"  # pragma: allowlist secret

    def test_create_adapter_unsupported(self):
        with pytest.raises(ValueError, match="不支持"):
            create_adapter("不存在的律所", "test_acc", "fake_secret")  # pragma: allowlist secret
