"""Per-call state stored as AgentSession userdata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from medical_secretary.config import Practice, Settings
from medical_secretary.ehr.base import EHRClient
from medical_secretary.ehr.mock import Faults, MockEHR

if TYPE_CHECKING:
    from medical_secretary.handoff import HandoffSummary


@dataclass
class VerifiedCaller:
    patient_id: str
    full_name: str
    birth_date: date


@dataclass
class CallState:
    practice: Practice
    ehr: EHRClient
    settings: Settings
    today: date
    caller: VerifiedCaller | None = None
    intent: str | None = None
    actions_taken: list[str] = field(default_factory=list)
    tool_failures: int = 0
    handoff: HandoffSummary | None = None

    def record(self, action: str) -> None:
        self.actions_taken.append(action)


def new_call_state(
    practice: Practice, settings: Settings, today: date, faults: Faults | None = None
) -> CallState:
    return CallState(
        practice=practice,
        ehr=MockEHR(practice, today, faults),
        settings=settings,
        today=today,
    )
