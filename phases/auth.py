"""Auth phase — validate org credentials are alive."""
from __future__ import annotations

import requests

from utils.runner import Phase, TransientError
from utils.state import OrgState


class AuthPhase(Phase):
    name = "auth"
    description = "Validate org credentials are alive"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        if dry_run:
            return

        url = f"{token_info['instance_url']}/services/data/v61.0/"
        headers = {"Authorization": f"Bearer {token_info['access_token']}"}

        try:
            resp = requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.ConnectionError as e:
            raise TransientError(f"Connection error: {e}") from e

        if resp.status_code == 401:
            raise Exception("Token is expired or invalid. Re-run `sf org login web` for this org.")
        if resp.status_code >= 500:
            raise TransientError(f"Org returned {resp.status_code} — may be temporarily unavailable.")
        if resp.status_code >= 400:
            raise Exception(f"Org returned unexpected status {resp.status_code}: {resp.text[:200]}")
