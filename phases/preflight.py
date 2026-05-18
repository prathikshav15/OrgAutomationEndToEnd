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

        # Try several Data Cloud endpoints — if ANY responds, DC is enabled.
        # We use real DC endpoints that return data when DC is enabled.
        candidates = [
            "/services/data/v66.0/ssot/data-model-objects",
            "/services/data/v66.0/ssot/segments",
            "/services/data/v66.0/ssot/data-streams",
        ]

        last_error = None
        for path in candidates:
            url = f"{token_info['instance_url']}{path}"
            try:
                resp = requests.get(url, headers=headers, timeout=15)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error: {e}") from e

            # Any 2xx, 3xx, or 4xx (auth/permission related but not 404) means
            # the endpoint exists → Data Cloud is enabled.
            if resp.status_code == 401:
                raise Exception("Token expired. Re-authenticate with `sf org login web`.")
            if resp.status_code >= 500:
                raise TransientError(f"Server error {resp.status_code} — retrying...")
            if resp.status_code != 404:
                # 200, 400, 403 etc all confirm the endpoint is registered
                return
            last_error = f"{path} → 404"

        raise Exception(
            "Data Cloud APIs returned 404 for all probes. "
            "Verify Data Cloud is provisioned in this org. "
            f"(last probe: {last_error})"
        )
