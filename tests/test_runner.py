"""Tests for Runner — dry-run, retry, phase skipping, state persistence."""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from utils.runner import Runner, Phase, TransientError
from utils.state import StateStore, OrgState, PhaseStatus


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_store(tmp_path):
    store = StateStore(tmp_path / "state")
    store.init(dry_run=False)
    return store


def make_org():
    return OrgState(
        username="test@example.com",
        instance_url="https://test.salesforce.com",
        alias="test",
        org_id="00D000000000001",
    )


def make_phase(name="test_phase", side_effect=None):
    phase = MagicMock(spec=Phase)
    phase.name = name
    phase.description = f"Test phase {name}"
    if side_effect:
        phase.run.side_effect = side_effect
    return phase


TOKEN = {"access_token": "fake_token", "instance_url": "https://test.salesforce.com"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_calls_phase_run_with_dry_run_true(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org
        phase = make_phase()

        runner = Runner(store)
        runner.run_for_org([phase], org, TOKEN, dry_run=True)

        phase.run.assert_called_once_with(TOKEN, org, dry_run=True)

    def test_dry_run_does_not_write_state_file(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org
        phase = make_phase()

        runner = Runner(store)
        runner.run_for_org([phase], org, TOKEN, dry_run=True)

        # Phase record should not be marked DONE (no state mutation in dry-run)
        record = org.get_phase("test_phase")
        assert record.status != PhaseStatus.DONE


class TestRetry:
    def test_transient_error_retries(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org
        # Fail twice then succeed
        phase = make_phase(side_effect=[TransientError("flaky"), TransientError("flaky"), None])

        runner = Runner(store)
        ok = runner.run_for_org([phase], org, TOKEN)

        assert ok is True
        assert phase.run.call_count == 3

    def test_transient_error_fails_after_max_retries(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org
        phase = make_phase(side_effect=TransientError("always fails"))

        runner = Runner(store)
        ok = runner.run_for_org([phase], org, TOKEN)

        assert ok is False
        assert phase.run.call_count == 3  # MAX_RETRIES

    def test_permanent_error_no_retry(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org
        phase = make_phase(side_effect=Exception("permanent"))

        runner = Runner(store)
        ok = runner.run_for_org([phase], org, TOKEN)

        assert ok is False
        assert phase.run.call_count == 1  # no retry for non-transient


class TestPhaseSkipping:
    def test_done_phase_is_skipped(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org
        # Pre-mark phase as done
        org.get_phase("p1").status = PhaseStatus.DONE
        phase = make_phase("p1")

        runner = Runner(store)
        runner.run_for_org([phase], org, TOKEN)

        phase.run.assert_not_called()

    def test_force_phase_reruns_done_phase(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org
        org.get_phase("p1").status = PhaseStatus.DONE
        phase = make_phase("p1")

        runner = Runner(store)
        runner.run_for_org([phase], org, TOKEN, force_phases={"p1"})

        phase.run.assert_called_once()

    def test_stops_on_failure_not_running_later_phases(self, tmp_path):
        store = make_store(tmp_path)
        org = make_org()
        store.state.orgs[org.username] = org

        p1 = make_phase("p1", side_effect=Exception("fail"))
        p2 = make_phase("p2")

        runner = Runner(store)
        ok = runner.run_for_org([p1, p2], org, TOKEN)

        assert ok is False
        p2.run.assert_not_called()


class TestStateStore:
    def test_save_and_reload(self, tmp_path):
        store = StateStore(tmp_path / "state")
        store.init()
        store.add_org("u@x.com", "https://x.com", "x", "00D1")
        org = store.state.orgs["u@x.com"]
        rec = org.get_phase("auth")
        rec.status = PhaseStatus.DONE
        store.save()

        store2 = StateStore(tmp_path / "state")
        store2.load()
        assert store2.state.orgs["u@x.com"].phases["auth"].status == PhaseStatus.DONE

    def test_exists_false_before_init(self, tmp_path):
        store = StateStore(tmp_path / "new_state")
        assert store.exists() is False

    def test_exists_true_after_init(self, tmp_path):
        store = StateStore(tmp_path / "new_state")
        store.init()
        assert store.exists() is True
