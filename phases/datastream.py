"""Datastream phase — create Data Cloud data streams from config."""
from __future__ import annotations

import json

import requests

from utils.config_loader import ConfigLoader
from utils.runner import Phase, TransientError
from utils.state import OrgState


class DatastreamPhase(Phase):
    name = "datastream"
    description = "Create Data Cloud data streams"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        config_loader = ConfigLoader()
        datastream_names = config_loader.get_all_entity_names("datastreams")

        if not datastream_names:
            print("    No datastreams defined in override_config.yaml — skipping.")
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        for name in datastream_names:
            entity_config = config_loader.get_entity_config("datastreams", name)

            if dry_run:
                print(f"    [dry-run] Would create datastream: {name}")
                print(f"    Payload: {json.dumps(entity_config, indent=6)}")
                continue

            url = f"{token_info['instance_url']}/services/data/v66.0/ssot/data-streams"
            try:
                resp = requests.post(url, headers=headers, json=entity_config, timeout=30)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error creating datastream {name}: {e}") from e

            if resp.status_code in (200, 201):
                result = resp.json()
                print(f"    ✓ Created datastream: {result.get('name', name)}")
            elif resp.status_code == 409:
                print(f"    ~ Datastream '{name}' already exists — skipping.")
            elif resp.status_code >= 500:
                raise TransientError(f"Server error {resp.status_code} creating datastream {name}")
            else:
                raise Exception(
                    f"Failed to create datastream '{name}': "
                    f"HTTP {resp.status_code} — {resp.text[:300]}"
                )
