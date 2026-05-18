"""DMO Mapping phase — map DLO fields to DMO fields.

This phase is what actually connects ingested data streams to Data Model Objects.
Without it, data sits in the DLO but never flows into the DMO, and segments
built on the DMO will be empty.

Run AFTER: datastream, dmo
Endpoint: POST /services/data/v66.0/ssot/data-model-object-mappings
"""
from __future__ import annotations

import json

import requests

from utils.config_loader import ConfigLoader
from utils.runner import Phase, TransientError
from utils.state import OrgState


class DMOMappingPhase(Phase):
    name = "dmo_mapping"
    description = "Map DLO fields to DMO fields (connects streams to data model)"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        config_loader = ConfigLoader()
        mapping_names = config_loader.get_all_entity_names("dmo_mappings")

        if not mapping_names:
            print("    No dmo_mappings defined in override_config.yaml — skipping.")
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        for name in mapping_names:
            entity_config = config_loader.get_entity_config("dmo_mappings", name)

            if dry_run:
                print(f"    [dry-run] Would create DMO mapping: {name}")
                print(f"    Payload: {json.dumps(entity_config, indent=6)}")
                continue

            url = f"{token_info['instance_url']}/services/data/v66.0/ssot/data-model-object-mappings"
            try:
                resp = requests.post(url, headers=headers, json=entity_config, timeout=30)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error creating DMO mapping {name}: {e}") from e

            if resp.status_code in (200, 201):
                result = resp.json()
                mapping_name = result.get("developerName") or result.get("name") or name
                print(f"    ✓ Created DMO mapping: {mapping_name}")
            elif resp.status_code == 409:
                print(f"    ~ DMO mapping '{name}' already exists — skipping.")
            elif resp.status_code >= 500:
                raise TransientError(f"Server error {resp.status_code} creating DMO mapping {name}")
            else:
                raise Exception(
                    f"Failed to create DMO mapping '{name}': "
                    f"HTTP {resp.status_code} — {resp.text[:300]}"
                )
