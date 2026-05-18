"""Tests for ConfigLoader — merge logic, missing file handling, entity lookup."""
import pytest
import tempfile
import os
from pathlib import Path
from utils.config_loader import ConfigLoader


# ── Fixtures ──────────────────────────────────────────────────────────────────

BASE_YAML = """\
defaults:
  api_version: "v66.0"
datastreams:
  base:
    dataSpaceName: "default"
    dataAccessMode: "INGEST"
    refreshConfig:
      frequency:
        frequencyType: "BATCH"
      refreshMode: "UPSERT"
dmos:
  base:
    dataSpaceName: "default"
    objectType: "Custom"
    objectCategory: "Profile"
segments:
  base:
    segmentType: "Ui"
    segmentOnApiName: "UnifiedIndividual__dlm"
    publishSchedule: "TwentyFour"
activations:
  base:
    refreshType: "FULL"
    dataSpaceName: "default"
"""

OVERRIDE_YAML = """\
datastreams:
  contacts_stream:
    label: "CRM Contacts"
    connectorInfo:
      connectorType: "SalesforceDotCom"
dmos:
  contact_dmo:
    name: "ContactUnified__dlm"
    label: "Contact Unified"
segments:
  seg1:
    displayName: "Segment One"
    dataSpaceName: "default"
activations:
  act1:
    name: "Activation_1"
    segmentApiName: "seg1"
"""


@pytest.fixture
def config_loader(tmp_path):
    base = tmp_path / "base_config.yaml"
    override = tmp_path / "override_config.yaml"
    base.write_text(BASE_YAML)
    override.write_text(OVERRIDE_YAML)
    return ConfigLoader(str(base), str(override))


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestGetAllEntityNames:
    def test_returns_override_keys(self, config_loader):
        names = config_loader.get_all_entity_names("datastreams")
        assert names == ["contacts_stream"]

    def test_returns_empty_for_missing_type(self, config_loader):
        names = config_loader.get_all_entity_names("nonexistent")
        assert names == []

    def test_multiple_segments(self, config_loader):
        names = config_loader.get_all_entity_names("segments")
        assert "seg1" in names


class TestGetEntityConfig:
    def test_base_defaults_present(self, config_loader):
        cfg = config_loader.get_entity_config("datastreams", "contacts_stream")
        # base default must be inherited
        assert cfg["dataSpaceName"] == "default"
        assert cfg["dataAccessMode"] == "INGEST"

    def test_override_wins_over_base(self, config_loader):
        cfg = config_loader.get_entity_config("datastreams", "contacts_stream")
        assert cfg["label"] == "CRM Contacts"
        assert cfg["connectorInfo"]["connectorType"] == "SalesforceDotCom"

    def test_deep_merge_preserves_nested(self, config_loader):
        cfg = config_loader.get_entity_config("datastreams", "contacts_stream")
        # refreshConfig comes entirely from base (not in override)
        assert cfg["refreshConfig"]["refreshMode"] == "UPSERT"
        assert cfg["refreshConfig"]["frequency"]["frequencyType"] == "BATCH"

    def test_dmo_correct_fields(self, config_loader):
        cfg = config_loader.get_entity_config("dmos", "contact_dmo")
        assert cfg["objectType"] == "Custom"
        assert cfg["objectCategory"] == "Profile"
        assert cfg["name"] == "ContactUnified__dlm"

    def test_segment_type_case(self, config_loader):
        cfg = config_loader.get_entity_config("segments", "seg1")
        # Must be "Ui" not "UI" — case-sensitive per MCP server
        assert cfg["segmentType"] == "Ui"

    def test_activation_refresh_type(self, config_loader):
        cfg = config_loader.get_entity_config("activations", "act1")
        # Must be "FULL" not "FULL_REFRESH"
        assert cfg["refreshType"] == "FULL"

    def test_raises_for_unknown_entity(self, config_loader):
        with pytest.raises((ValueError, KeyError)):
            config_loader.get_entity_config("datastreams", "does_not_exist")

    def test_raises_for_unknown_type(self, config_loader):
        with pytest.raises((ValueError, KeyError)):
            config_loader.get_entity_config("unknown_type", "something")


class TestMissingOverrideFile:
    def test_graceful_empty_when_no_override(self, tmp_path):
        base = tmp_path / "base_config.yaml"
        base.write_text(BASE_YAML)
        loader = ConfigLoader(str(base), str(tmp_path / "nonexistent.yaml"))
        assert loader.get_all_entity_names("datastreams") == []

    def test_graceful_empty_when_no_base(self, tmp_path):
        override = tmp_path / "override_config.yaml"
        override.write_text(OVERRIDE_YAML)
        loader = ConfigLoader(str(tmp_path / "nonexistent.yaml"), str(override))
        # base missing → no entity types known
        assert loader.get_available_entity_types() == []
