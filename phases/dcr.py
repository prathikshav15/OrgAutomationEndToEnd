"""DCR phase — install and configure the Data Clean Room package."""
from __future__ import annotations

import time

import requests

from utils.runner import Phase, TransientError
from utils.state import OrgState

# Default DCR managed package namespace + version
DCR_PACKAGE_ID = "04t"  # Placeholder — override via config or env var
DCR_NAMESPACE = "dc_clean_room"
INSTALL_POLL_INTERVAL = 10  # seconds
INSTALL_TIMEOUT = 300  # seconds


class DCRPhase(Phase):
    name = "dcr_install"
    description = "Install Data Clean Room managed package"

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        import os
        package_id = os.environ.get("DCR_PACKAGE_ID", "")

        if not package_id:
            print(
                "    DCR_PACKAGE_ID env var not set — skipping Clean Room install.\n"
                "    Set DCR_PACKAGE_ID=04tXXXXXXXXXXXXX to enable this phase."
            )
            return

        if dry_run:
            print(f"    [dry-run] Would install DCR package: {package_id}")
            return

        headers = {
            "Authorization": f"Bearer {token_info['access_token']}",
            "Content-Type": "application/json",
        }

        # Step 1: Submit install request via Tooling API
        install_url = (
            f"{token_info['instance_url']}"
            f"/services/data/v66.0/tooling/sobjects/PackageInstallRequest"
        )
        payload = {
            "SubscriberPackageVersionId": package_id,
            "SecurityType": "Full",
            "NameConflictResolution": "Block",
        }

        try:
            resp = requests.post(install_url, headers=headers, json=payload, timeout=30)
        except requests.exceptions.ConnectionError as e:
            raise TransientError(f"Connection error submitting install request: {e}") from e

        if resp.status_code not in (200, 201):
            raise Exception(
                f"Failed to submit DCR install request: "
                f"HTTP {resp.status_code} — {resp.text[:300]}"
            )

        request_id = resp.json().get("id")
        print(f"    Install request submitted (id={request_id}). Waiting for completion...")

        # Step 2: Poll until complete
        poll_url = (
            f"{token_info['instance_url']}"
            f"/services/data/v66.0/tooling/sobjects/PackageInstallRequest/{request_id}"
        )
        elapsed = 0
        while elapsed < INSTALL_TIMEOUT:
            time.sleep(INSTALL_POLL_INTERVAL)
            elapsed += INSTALL_POLL_INTERVAL

            try:
                poll_resp = requests.get(poll_url, headers=headers, timeout=15)
            except requests.exceptions.ConnectionError as e:
                raise TransientError(f"Connection error polling install status: {e}") from e

            status = poll_resp.json().get("Status", "")
            print(f"    Status: {status} ({elapsed}s elapsed)")

            if status == "SUCCESS":
                print(f"    ✓ DCR package installed successfully.")
                return
            elif status in ("ERROR", "FAILED"):
                errors = poll_resp.json().get("Errors", {}).get("errors", [])
                error_msg = "; ".join(e.get("message", "") for e in errors)
                raise Exception(f"DCR package install failed: {error_msg}")
            # IN_PROGRESS or IN_QUEUE — keep polling

        raise TransientError(
            f"DCR install timed out after {INSTALL_TIMEOUT}s. Re-run to resume polling."
        )
