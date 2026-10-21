"""Structured context handed to practice staff on escalation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from medical_secretary.session_state import CallState

Priority = Literal["routine", "urgent"]


@dataclass
class HandoffSummary:
    caller_name: str | None
    verified: bool
    intent: str | None
    actions_taken: list[str]
    reason: str
    priority: Priority
    team: str
    summary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def build_handoff_summary(
    state: CallState, reason: str, priority: Priority, summary: str
) -> HandoffSummary:
    return HandoffSummary(
        caller_name=state.caller.full_name if state.caller else None,
        verified=state.caller is not None,
        intent=state.intent,
        actions_taken=list(state.actions_taken),
        reason=reason,
        priority=priority,
        team=state.practice.team_for(reason),
        summary=summary,
    )
