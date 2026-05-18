"""Target phase — create activation targets."""
from __future__ import annotations

import requests

from utils.config_loader import ConfigLoader
from utils.runner import Phase, TransientError
from utils.state import OrgState


class TargetPhase(Phase):
    name = "target"
    description = "Create activation targets"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        config_loader = ConfigLoader()
        target_names = config_loader.get_all_entity_names("targets")

        if not target_names:
            print("    No targets defined in override_config.yaml — skipping.")
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        for name in target_names:
            entity_config = config_loader.get_entity_config("targets", name)

            if dry_run:
                print(f"    [dry-run] Would create target: {name}")
                continue

            url = f"{token_info['instance_url']}/services/data/v66.0/ssot/activation-targets"
            try:
                resp = requests.post(url, headers=headers, json=entity_config, timeout=30)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error creating target {name}: {e}") from e

            if resp.status_code in (200, 201):
                result = resp.json()
                print(f"    ✓ Created target: {result.get('name', name)}")
            elif resp.status_code == 409:
                print(f"    ~ Target '{name}' already exists — skipping.")
            elif resp.status_code >= 500:
                raise TransientError(f"Server error {resp.status_code} creating target {name}")
            else:
                raise Exception(
                    f"Failed to create target '{name}': "
                    f"HTTP {resp.status_code} — {resp.text[:300]}"
                )
