"""DMO phase — create Data Model Objects (custom DMOs)."""
from __future__ import annotations

import json

import requests

from utils.config_loader import ConfigLoader
from utils.runner import Phase, TransientError
from utils.state import OrgState


class DMOPhase(Phase):
    name = "dmo"
    description = "Create Data Model Objects (DMOs)"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        config_loader = ConfigLoader()
        dmo_names = config_loader.get_all_entity_names("dmos")

        if not dmo_names:
            print("    No DMOs defined in override_config.yaml — skipping.")
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        for name in dmo_names:
            entity_config = config_loader.get_entity_config("dmos", name)

            if dry_run:
                print(f"    [dry-run] Would create DMO: {name}")
                print(f"    Payload: {json.dumps(entity_config, indent=6)}")
                continue

            url = f"{token_info['instance_url']}/services/data/v61.0/ssot/dataModelObjects"
            try:
                resp = requests.post(url, headers=headers, json=entity_config, timeout=30)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error creating DMO {name}: {e}") from e

            if resp.status_code in (200, 201):
                result = resp.json()
                print(f"    ✓ Created DMO: {result.get('developerName', name)}")
            elif resp.status_code == 409:
                print(f"    ~ DMO '{name}' already exists — skipping.")
            elif resp.status_code >= 500:
                raise TransientError(f"Server error {resp.status_code} creating DMO {name}")
            else:
                raise Exception(
                    f"Failed to create DMO '{name}': "
                    f"HTTP {resp.status_code} — {resp.text[:300]}"
                )
