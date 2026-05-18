"""CSV Ingest phase — upload a local CSV file into an existing Data Cloud DLO.

Data Cloud has two distinct API surfaces:

  1. SSOT API  (v66.0)  — schema management (datastreams, DMOs, segments …)
  2. Ingest API (v1)    — bulk data upload into DLOs

This phase uses the Ingest API to push CSV rows into a DLO that was already
created by the DatastreamPhase.  The 3-step Ingest API flow:

  Step 1  POST  {instance_url}/api/v1/ingest/jobs
              → creates a job, returns jobId
  Step 2  PUT   {instance_url}/api/v1/ingest/jobs/{jobId}/batches
              → streams the CSV body (text/csv, raw bytes)
  Step 3  PATCH {instance_url}/api/v1/ingest/jobs/{jobId}
              → commit  {"state": "UploadComplete"}

Run AFTER: datastream (which creates the DLO the data lands in)
Docs: https://developer.salesforce.com/docs/atlas.en-us.c360a_api.meta/c360a_api/c360a_api_ingest_api_intro.htm
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from utils.config_loader import ConfigLoader
from utils.runner import Phase, TransientError
from utils.state import OrgState


class CSVIngestPhase(Phase):
    name = "csv_ingest"
    description = "Upload CSV file(s) into Data Cloud DLOs via the Ingest API"

    # ------------------------------------------------------------------ run --

    def run(self, token_info: dict, org: OrgState, dry_run: bool = False) -> None:
        config_loader = ConfigLoader()
        job_names = config_loader.get_all_entity_names("csv_ingests")

        if not job_names:
            print("    No csv_ingests defined in override_config.yaml — skipping.")
            return

        for name in job_names:
            cfg = config_loader.get_entity_config("csv_ingests", name)
            self._process_job(name, cfg, token_info, dry_run)

    # --------------------------------------------------------- single upload --

    def _process_job(
        self,
        name: str,
        cfg: dict,
        token_info: dict,
        dry_run: bool,
    ) -> None:
        object_name = cfg["objectApiName"]          # DLO developer name
        operation   = cfg.get("operation", "upsert")  # upsert | insert | delete
        csv_path    = Path(cfg["csvFilePath"]).expanduser()

        if not csv_path.exists():
            raise FileNotFoundError(
                f"CSV file not found for ingest job '{name}': {csv_path}"
            )

        if dry_run:
            row_count = sum(1 for _ in csv_path.open()) - 1  # minus header
            print(f"    [dry-run] Would ingest '{name}':")
            print(f"      object  : {object_name}")
            print(f"      operation: {operation}")
            print(f"      file    : {csv_path}  ({row_count} data rows)")
            return

        instance_url = token_info["instance_url"]
        access_token = token_info["access_token"]

        headers_json = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # ── Step 1: Create the ingest job ────────────────────────────────────
        job_payload = {
            "object": object_name,
            "sourceName": cfg.get("sourceName", object_name),
            "operation": operation,
        }
        create_url = f"{instance_url}/api/v1/ingest/jobs"
        try:
            resp = requests.post(
                create_url, headers=headers_json, json=job_payload, timeout=30
            )
        except requests.exceptions.ConnectionError as e:
            raise TransientError(f"Connection error creating ingest job '{name}': {e}") from e

        if resp.status_code not in (200, 201):
            raise Exception(
                f"Failed to create ingest job '{name}': "
                f"HTTP {resp.status_code} — {resp.text[:400]}"
            )

        job_id = resp.json()["id"]
        print(f"    ✓ Created ingest job: {job_id}  (object={object_name})")

        # ── Step 2: Upload the CSV batch ─────────────────────────────────────
        batch_url = f"{instance_url}/api/v1/ingest/jobs/{job_id}/batches"
        headers_csv = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "text/csv",
        }
        csv_bytes = csv_path.read_bytes()
        try:
            resp = requests.put(
                batch_url, headers=headers_csv, data=csv_bytes, timeout=120
            )
        except requests.exceptions.ConnectionError as e:
            raise TransientError(
                f"Connection error uploading CSV for job '{job_id}': {e}"
            ) from e

        if resp.status_code not in (200, 201, 204):
            raise Exception(
                f"Failed to upload CSV batch for job '{job_id}': "
                f"HTTP {resp.status_code} — {resp.text[:400]}"
            )
        print(f"    ✓ Uploaded CSV  : {csv_path.name}  ({len(csv_bytes):,} bytes)")

        # ── Step 3: Commit the job ───────────────────────────────────────────
        close_url = f"{instance_url}/api/v1/ingest/jobs/{job_id}"
        try:
            resp = requests.patch(
                close_url,
                headers=headers_json,
                json={"state": "UploadComplete"},
                timeout=30,
            )
        except requests.exceptions.ConnectionError as e:
            raise TransientError(
                f"Connection error committing ingest job '{job_id}': {e}"
            ) from e

        if resp.status_code not in (200, 201, 204):
            raise Exception(
                f"Failed to commit ingest job '{job_id}': "
                f"HTTP {resp.status_code} — {resp.text[:400]}"
            )

        state = resp.json().get("state", "committed")
        print(f"    ✓ Job committed : {job_id}  (state={state})")
        print(f"    ℹ  Data processes asynchronously — check the org for ingestion status.")
