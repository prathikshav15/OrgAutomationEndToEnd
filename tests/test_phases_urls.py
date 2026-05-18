"""Tests that every phase uses the correct v66.0 endpoint URLs and field names."""
import re
import inspect
from pathlib import Path

PHASES_DIR = Path(__file__).parent.parent / "phases"
UTILS_DIR = Path(__file__).parent.parent / "utils"


def _source(filename):
    return (PHASES_DIR / filename).read_text()


def _utils_source(filename):
    return (UTILS_DIR / filename).read_text()


class TestAPIVersions:
    def test_no_v61_anywhere(self):
        for f in list(PHASES_DIR.glob("*.py")) + list(UTILS_DIR.glob("*.py")):
            src = f.read_text()
            assert "v61.0" not in src, f"{f.name} still references v61.0"

    def test_v66_used_in_datastream(self):
        assert "v66.0" in _source("datastream.py")

    def test_v66_used_in_dmo(self):
        assert "v66.0" in _source("dmo.py")

    def test_v66_used_in_segment(self):
        assert "v66.0" in _source("segment.py")

    def test_v66_used_in_activation(self):
        assert "v66.0" in _source("activation.py")

    def test_v66_used_in_target(self):
        assert "v66.0" in _source("target.py")

    def test_v66_used_in_auth(self):
        assert "v66.0" in _source("auth.py")

    def test_v66_used_in_preflight(self):
        assert "v66.0" in _source("preflight.py")

    def test_v66_used_in_dcr(self):
        assert "v66.0" in _source("dcr.py")

    def test_v66_used_in_api_utils(self):
        assert "v66.0" in _utils_source("api.py")


class TestEndpointPaths:
    def test_datastream_uses_hyphenated_path(self):
        src = _source("datastream.py")
        assert "/ssot/data-streams" in src
        assert "/ssot/datastreams" not in src

    def test_dmo_uses_hyphenated_path(self):
        src = _source("dmo.py")
        assert "/ssot/data-model-objects" in src
        assert "/ssot/dataModelObjects" not in src
        assert "/ssot/datamodel-objects" not in src

    def test_segment_path_correct(self):
        assert "/ssot/segments" in _source("segment.py")

    def test_activation_path_correct(self):
        assert "/ssot/activations" in _source("activation.py")

    def test_target_path_correct(self):
        assert "/ssot/activation-targets" in _source("target.py")


class TestPhaseRegistry:
    def test_all_phases_importable(self):
        from phases import all_phases
        phases = all_phases()
        assert len(phases) == 9

    def test_phase_order(self):
        from phases import all_phases
        names = [p.name for p in all_phases()]
        assert names == [
            "auth", "preflight", "datastream", "dmo",
            "dmo_mapping", "segment", "target", "activation", "dcr_install"
        ]

    def test_dmo_mapping_uses_correct_endpoint(self):
        src = _source("dmo_mapping.py")
        assert "/ssot/data-model-object-mappings" in src
        assert "v66.0" in src

    def test_all_phases_have_name_and_description(self):
        from phases import all_phases
        for phase in all_phases():
            assert phase.name, f"{type(phase).__name__} has no name"
            assert phase.description, f"{type(phase).__name__} has no description"
