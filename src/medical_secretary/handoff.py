"""Structured context handed to practice staff on escalation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from medical_secretary.config import Practice
    from medical_secretary.session_state import CallState

Priority = Literal["routine", "urgent"]

# Reasons the agents may pass to route_to_human. A closed set, so a model
# cannot invent a reason that silently falls through to the default team.
AgentHandoffReason = Literal[
    "clinical", "billing", "records", "scheduling", "caller_request", "out_of_scope"
]
SchedulingHandoffReason = Literal[AgentHandoffReason, "system_error"]
HandoffReason = Literal[SchedulingHandoffReason, "identity_not_verified"]


@dataclass
class HandoffSummary:
    caller_name: str | None
    verified: bool
    intent: str | None
    actions_taken: list[str]
    reason: HandoffReason
    priority: Priority
    team: str
    summary: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


def build_handoff_summary(
    state: CallState, reason: HandoffReason, priority: Priority, summary: str
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


def transfer_announcement(summary: HandoffSummary, practice: Practice) -> str:
    """Instructions for what the caller hears when the transfer happens.

    The routing agent says nothing before transferring, so this is the only
    place the caller is told; keeping it here means saying "I'm connecting
    you" and actually connecting are one step.
    """
    team = summary.team.replace("-", " ")
    parts: list[str] = []
    if summary.priority == "urgent":
        parts.append(
            "Start with one short, warm sentence acknowledging that the caller is worried."
        )
    if summary.reason == "out_of_scope":
        parts.append(f'Say: "{practice.out_of_scope_message}"')
    parts.append(f"Tell the caller you're connecting them with the {team} team now.")
    return " ".join(parts)
