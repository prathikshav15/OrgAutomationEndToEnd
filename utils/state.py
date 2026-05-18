"""
state.py — Phase run state persistence.

Saves progress to .cdp-setup/state.json so runs can resume after failure.
"""
from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


class PhaseStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseRecord:
    status: PhaseStatus = PhaseStatus.PENDING
    attempt: int = 0
    last_error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


@dataclass
class OrgState:
    username: str
    instance_url: str
    alias: str
    org_id: str
    phases: Dict[str, PhaseRecord] = field(default_factory=dict)

    def get_phase(self, name: str) -> PhaseRecord:
        if name not in self.phases:
            self.phases[name] = PhaseRecord()
        return self.phases[name]


@dataclass
class RunState:
    run_id: str
    created_at: str
    schema_version: int = 1
    dry_run: bool = False
    data_sources: list = field(default_factory=list)
    orgs: Dict[str, OrgState] = field(default_factory=dict)  # keyed by username


class StateStore:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_path = self.state_dir / "state.json"
        self._state: Optional[RunState] = None

    def init(self, dry_run: bool = False, data_sources: list = None) -> RunState:
        """Create a new run state."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state = RunState(
            run_id=str(uuid.uuid4()),
            created_at=datetime.utcnow().isoformat(),
            dry_run=dry_run,
            data_sources=data_sources or [],
        )
        self.save()
        return self._state

    def load(self) -> RunState:
        """Load existing state from disk."""
        with open(self.state_path) as f:
            raw = json.load(f)

        orgs = {}
        for username, org_data in raw.get("orgs", {}).items():
            phases = {}
            for phase_name, phase_data in org_data.get("phases", {}).items():
                phases[phase_name] = PhaseRecord(
                    status=PhaseStatus(phase_data["status"]),
                    attempt=phase_data.get("attempt", 0),
                    last_error=phase_data.get("last_error"),
                    started_at=phase_data.get("started_at"),
                    finished_at=phase_data.get("finished_at"),
                )
            orgs[username] = OrgState(
                username=org_data["username"],
                instance_url=org_data["instance_url"],
                alias=org_data.get("alias", ""),
                org_id=org_data.get("org_id", ""),
                phases=phases,
            )

        self._state = RunState(
            run_id=raw["run_id"],
            created_at=raw["created_at"],
            schema_version=raw.get("schema_version", 1),
            dry_run=raw.get("dry_run", False),
            data_sources=raw.get("data_sources", []),
            orgs=orgs,
        )
        return self._state

    def save(self) -> None:
        """Atomically write state to disk."""
        if self._state is None:
            return

        raw = {
            "run_id": self._state.run_id,
            "created_at": self._state.created_at,
            "schema_version": self._state.schema_version,
            "dry_run": self._state.dry_run,
            "data_sources": self._state.data_sources,
            "orgs": {},
        }

        for username, org in self._state.orgs.items():
            raw["orgs"][username] = {
                "username": org.username,
                "instance_url": org.instance_url,
                "alias": org.alias,
                "org_id": org.org_id,
                "phases": {
                    name: {
                        "status": rec.status.value,
                        "attempt": rec.attempt,
                        "last_error": rec.last_error,
                        "started_at": rec.started_at,
                        "finished_at": rec.finished_at,
                    }
                    for name, rec in org.phases.items()
                },
            }

        # Atomic write — write to temp file then rename
        self.state_dir.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.state_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(raw, f, indent=2)
            os.replace(tmp_path, self.state_path)
        except Exception:
            os.unlink(tmp_path)
            raise

    @property
    def state(self) -> RunState:
        return self._state

    def exists(self) -> bool:
        return self.state_path.exists()

    def add_org(self, username: str, instance_url: str, alias: str, org_id: str) -> OrgState:
        org = OrgState(
            username=username,
            instance_url=instance_url,
            alias=alias,
            org_id=org_id,
        )
        self._state.orgs[username] = org
        self.save()
        return org
