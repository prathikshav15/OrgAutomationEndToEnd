"""
runner.py — Phase runner with resume, retry, and dry-run support.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import List, Optional, Set

from rich.console import Console
from rich.panel import Panel

from utils.state import OrgState, PhaseStatus, StateStore

console = Console()

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class TransientError(Exception):
    """Raise this from a phase to trigger an automatic retry."""


class Phase:
    name: str
    description: str

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        raise NotImplementedError


class Runner:
    def __init__(self, store: StateStore):
        self.store = store

    def run_for_org(
        self,
        phases: List[Phase],
        org: OrgState,
        token_info: dict,
        dry_run: bool = False,
        force_phases: Optional[Set[str]] = None,
    ) -> bool:
        """
        Run all phases for a single org.
        Returns True if all phases completed successfully.
        """
        console.print(
            Panel(
                f"[bold cyan]{org.username}[/bold cyan]\n{org.instance_url}",
                title="Provisioning org",
                expand=False,
            )
        )

        all_ok = True
        for phase in phases:
            record = org.get_phase(phase.name)

            # Skip already done phases unless forced
            if record.status == PhaseStatus.DONE and (
                force_phases is None or phase.name not in force_phases
            ):
                console.print(f"  [dim]✓ {phase.name} — skipped (already done)[/dim]")
                continue

            if dry_run:
                console.print(f"  [yellow]~ {phase.name} — dry run (would execute)[/yellow]")
                continue

            # Run with retries
            success = self._run_phase(phase, org, token_info, record, dry_run)
            self.store.save()

            if not success:
                all_ok = False
                console.print(
                    f"  [red]✗ {phase.name} failed — stopping for this org.[/red]\n"
                    f"  [dim]Re-run to resume from this phase.[/dim]"
                )
                break

        return all_ok

    def _run_phase(self, phase: Phase, org: OrgState, token_info: dict, record, dry_run: bool) -> bool:
        for attempt in range(1, MAX_RETRIES + 1):
            record.status = PhaseStatus.IN_PROGRESS
            record.attempt = attempt
            record.started_at = datetime.utcnow().isoformat()
            self.store.save()

            try:
                phase.run(token_info, org, dry_run=dry_run)
                record.status = PhaseStatus.DONE
                record.last_error = None
                record.finished_at = datetime.utcnow().isoformat()
                console.print(f"  [green]✓ {phase.name}[/green]")
                return True

            except TransientError as e:
                record.last_error = str(e)
                if attempt < MAX_RETRIES:
                    console.print(
                        f"  [yellow]⟳ {phase.name} — transient error, retrying "
                        f"({attempt}/{MAX_RETRIES})...[/yellow]"
                    )
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    record.status = PhaseStatus.FAILED
                    record.finished_at = datetime.utcnow().isoformat()
                    console.print(f"  [red]✗ {phase.name} — {e}[/red]")
                    return False

            except Exception as e:
                record.status = PhaseStatus.FAILED
                record.last_error = str(e)
                record.finished_at = datetime.utcnow().isoformat()
                console.print(f"  [red]✗ {phase.name} — {e}[/red]")
                return False

        return False
