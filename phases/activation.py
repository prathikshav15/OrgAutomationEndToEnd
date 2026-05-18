"""Activation phase — create data activations."""
from __future__ import annotations

import requests

from utils.config_loader import ConfigLoader
from utils.runner import Phase, TransientError
from utils.state import OrgState


class ActivationPhase(Phase):
    name = "activation"
    description = "Create data activations"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        config_loader = ConfigLoader()
        activation_names = config_loader.get_all_entity_names("activations")

        if not activation_names:
            print("    No activations defined in override_config.yaml — skipping.")
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        for name in activation_names:
            entity_config = config_loader.get_entity_config("activations", name)

            if dry_run:
                print(f"    [dry-run] Would create activation: {name}")
                continue

            url = f"{token_info['instance_url']}/services/data/v66.0/ssot/activations"
            try:
                resp = requests.post(url, headers=headers, json=entity_config, timeout=30)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error creating activation {name}: {e}") from e

            if resp.status_code in (200, 201):
                result = resp.json()
                print(f"    ✓ Created activation: {result.get('name', name)}")
            elif resp.status_code == 409:
                print(f"    ~ Activation '{name}' already exists — skipping.")
            elif resp.status_code >= 500:
                raise TransientError(f"Server error {resp.status_code} creating activation {name}")
            else:
                raise Exception(
                    f"Failed to create activation '{name}': "
                    f"HTTP {resp.status_code} — {resp.text[:300]}"
                )
