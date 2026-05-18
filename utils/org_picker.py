"""
org_picker.py — Multi-org selector using sf CLI.

Shows real usernames + instance URLs so users are never confused by aliases.
Supports:
  - Multi-select from connected orgs
  - Adding a new org (triggers browser login)
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import List

import questionary
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class OrgInfo:
    alias: str
    username: str
    instance_url: str
    org_id: str

    def display_label(self) -> str:
        """Human-readable label shown in the picker."""
        return f"{self.username}  ({self.instance_url})"


def _get_connected_orgs() -> List[OrgInfo]:
    """Run `sf org list --json` and return connected orgs."""
    try:
        result = subprocess.run(
            ["sf", "org", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        data = json.loads(result.stdout)
        orgs = []

        # sf CLI returns nonScratchOrgs + scratchOrgs
        for category in ("nonScratchOrgs", "scratchOrgs"):
            for org in data.get("result", {}).get(category, []):
                if org.get("connectedStatus") == "Connected" or org.get("isConnected"):
                    orgs.append(
                        OrgInfo(
                            alias=org.get("alias", ""),
                            username=org.get("username", ""),
                            instance_url=org.get("instanceUrl", ""),
                            org_id=org.get("orgId", ""),
                        )
                    )
        return orgs
    except Exception as e:
        console.print(f"[red]Failed to list orgs:[/red] {e}")
        return []


def _login_new_org() -> OrgInfo | None:
    """Trigger browser login for a new org and return its info."""
    instance_url = questionary.text(
        "Instance URL for the new org? (e.g. https://orgfarm-xxx.test2.my.pc-rnd.salesforce.com)",
        default="",
    ).ask()

    if not instance_url:
        return None

    alias = questionary.text(
        "Give this org a short alias (e.g. cr-new)?",
        default="new-org",
    ).ask()

    console.print(f"\n[cyan]Opening browser for login...[/cyan]")
    result = subprocess.run(
        ["sf", "org", "login", "web", "--instance-url", instance_url, "--alias", alias],
        timeout=120,
    )

    if result.returncode != 0:
        console.print("[red]Login failed.[/red]")
        return None

    # Fetch the newly added org's details
    result2 = subprocess.run(
        ["sf", "org", "display", "--target-org", alias, "--json"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    data = json.loads(result2.stdout).get("result", {})
    return OrgInfo(
        alias=alias,
        username=data.get("username", ""),
        instance_url=data.get("instanceUrl", instance_url),
        org_id=data.get("id", ""),
    )


def pick_orgs() -> List[OrgInfo]:
    """
    Interactive multi-org picker.

    Shows connected orgs with real usernames + URLs.
    Returns the list of OrgInfo objects the user selected.
    """
    console.print("\n[bold cyan]Fetching connected orgs...[/bold cyan]")
    orgs = _get_connected_orgs()

    if orgs:
        # Show a summary table first
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("#", width=3, justify="right")
        table.add_column("Username")
        table.add_column("Instance URL")
        table.add_column("Alias")
        for i, org in enumerate(orgs, 1):
            table.add_row(str(i), org.username, org.instance_url, org.alias or "—")
        console.print(table)

    ADD_NEW = "__add_new__"

    choices = [
        questionary.Choice(title=org.display_label(), value=org) for org in orgs
    ] + [
        questionary.Choice(title="➕  Add new org (opens browser login)", value=ADD_NEW)
    ]

    selected = questionary.checkbox(
        "Select orgs to provision: (space to toggle, enter to confirm)",
        choices=choices,
    ).ask()

    if selected is None:
        return []

    # Handle "add new org"
    result_orgs: List[OrgInfo] = []
    needs_new = ADD_NEW in selected
    result_orgs = [s for s in selected if s != ADD_NEW]

    if needs_new:
        new_org = _login_new_org()
        if new_org:
            result_orgs.append(new_org)
            console.print(f"[green]✓ Added {new_org.username}[/green]")

    return result_orgs


def get_token_for_org(org: OrgInfo) -> dict:
    """
    Fetch a live access token for the org using sf CLI.
    Returns dict with access_token + instance_url.
    """
    result = subprocess.run(
        ["sf", "org", "display", "--target-org", org.username, "--json"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    data = json.loads(result.stdout).get("result", {})
    return {
        "access_token": data["accessToken"],
        "instance_url": data["instanceUrl"],
    }
