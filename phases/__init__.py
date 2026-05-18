"""Phase registry — returns all phases in execution order."""
from __future__ import annotations

from typing import List

from utils.runner import Phase

from phases.auth import AuthPhase
from phases.preflight import PreflightPhase
from phases.datastream import DatastreamPhase
from phases.dmo import DMOPhase
from phases.dmo_mapping import DMOMappingPhase
from phases.segment import SegmentPhase
from phases.target import TargetPhase
from phases.activation import ActivationPhase
from phases.dcr import DCRPhase
from phases.csv_ingest import CSVIngestPhase


def all_phases() -> List[Phase]:
    return [
        AuthPhase(),
        PreflightPhase(),
        DatastreamPhase(),
        DMOPhase(),
        DMOMappingPhase(),   # maps DLO → DMO so data flows into the model
        SegmentPhase(),
        TargetPhase(),
        ActivationPhase(),
        DCRPhase(),
        CSVIngestPhase(),    # upload CSV data into the DLO via Ingest API
    ]
