"""Preflight phase — verify Data Cloud is enabled and accessible."""
from __future__ import annotations

import requests

from utils.runner import Phase, TransientError
from utils.state import OrgState


class PreflightPhase(Phase):
    name = "preflight"
    description = "Verify Data Cloud is enabled and accessible"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        if dry_run:
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        # Check if Data Cloud (SSOT) API is accessible
        url = f"{token_info['instance_url']}/services/data/v61.0/ssot/"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.ConnectionError as e:
            raise TransientError(f"Connection error: {e}") from e

        if resp.status_code == 404:
            raise Exception(
                "Data Cloud is not enabled on this org. "
                "Enable it via Setup → Data Cloud Setup."
            )
        if resp.status_code == 401:
            raise Exception("Token expired. Re-authenticate with `sf org login web`.")
        if resp.status_code >= 500:
            raise TransientError(f"Server error {resp.status_code} — retrying...")
        # 200 or 405 (method not allowed on root) both mean DC is accessible
