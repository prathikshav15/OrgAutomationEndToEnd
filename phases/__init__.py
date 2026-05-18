"""Phase registry — returns all phases in execution order."""
from __future__ import annotations

from typing import List

from utils.runner import Phase

from phases.auth import AuthPhase
from phases.preflight import PreflightPhase
from phases.datastream import DatastreamPhase
from phases.dmo import DMOPhase
from phases.segment import SegmentPhase
from phases.target import TargetPhase
from phases.activation import ActivationPhase
from phases.dcr import DCRPhase


def all_phases() -> List[Phase]:
    return [
        AuthPhase(),
        PreflightPhase(),
        DatastreamPhase(),
        DMOPhase(),
        SegmentPhase(),
        TargetPhase(),
        ActivationPhase(),
        DCRPhase(),
    ]
