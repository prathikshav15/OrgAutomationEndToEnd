"""Segment phase — create Data Cloud segments."""
from __future__ import annotations

import requests

from utils.config_loader import ConfigLoader
from utils.runner import Phase, TransientError
from utils.state import OrgState


class SegmentPhase(Phase):
    name = "segment"
    description = "Create Data Cloud segments"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        config_loader = ConfigLoader()
        segment_names = config_loader.get_all_entity_names("segments")

        if not segment_names:
            print("    No segments defined in override_config.yaml — skipping.")
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        for name in segment_names:
            entity_config = config_loader.get_entity_config("segments", name)

            if dry_run:
                print(f"    [dry-run] Would create segment: {name}")
                continue

            url = f"{token_info['instance_url']}/services/data/v61.0/ssot/segments"
            try:
                resp = requests.post(url, headers=headers, json=entity_config, timeout=30)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error creating segment {name}: {e}") from e

            if resp.status_code in (200, 201):
                result = resp.json()
                print(f"    ✓ Created segment: {result.get('developerName', name)}")
            elif resp.status_code == 409:
                print(f"    ~ Segment '{name}' already exists — skipping.")
            elif resp.status_code >= 500:
                raise TransientError(f"Server error {resp.status_code} creating segment {name}")
            else:
                raise Exception(
                    f"Failed to create segment '{name}': "
                    f"HTTP {resp.status_code} — {resp.text[:300]}"
                )
