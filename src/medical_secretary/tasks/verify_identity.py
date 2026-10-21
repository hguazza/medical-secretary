"""Collect and verify the patient's identity (name + date of birth)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from livekit.agents import (
    NOT_GIVEN,
    AgentTask,
    ChatContext,
    NotGivenOr,
    RunContext,
    function_tool,
)

from medical_secretary.prompts import BASE_RULES
from medical_secretary.session_state import CallState, VerifiedCaller
from medical_secretary.tools.resilience import MAX_TOOL_FAILURES, ToolFailure, guarded

INSTRUCTIONS = f"""{BASE_RULES}

# Your task: verify the patient
Collect the patient's full name and date of birth. The caller may be a parent calling for a child; you need the patient's details, not the caller's. Read the date of birth back and get a yes, then call submit_identity. Do nothing else until the patient is verified."""


@dataclass(frozen=True)
class IdentityResult:
    caller: VerifiedCaller | None
    outcome: Literal["verified", "no_match", "system_error"]


@dataclass(frozen=True)
class IdentityDecision:
    attempts: int
    text: str | None  # tool output when the task continues
    final: IdentityResult | None  # set when the task is complete


async def check_identity(
    state: CallState, full_name: str, birth_date: str
) -> VerifiedCaller | str:
    try:
        dob = date.fromisoformat(birth_date)
    except ValueError:
        return "ERROR bad_date: birth_date must be YYYY-MM-DD. Ask the caller to repeat the date of birth."
    patient = await guarded(
        state,
        "lookup_patient",
        state.ehr.lookup_patient(full_name, dob),
        timeout_s=state.settings.ehr_timeout_s,
    )
    if isinstance(patient, ToolFailure):
        return patient.message(state)
    if patient is None:
        return "NO_MATCH"
    return VerifiedCaller(patient.id, patient.full_name, patient.birth_date)


MAX_ATTEMPTS = 2


def decide_identity(
    result: VerifiedCaller | str, attempts: int, tool_failures: int
) -> IdentityDecision:
    """Pure decision for one submit_identity call: complete the task or continue."""
    if isinstance(result, VerifiedCaller):
        return IdentityDecision(attempts + 1, None, IdentityResult(result, "verified"))
    if result == "NO_MATCH":
        attempts += 1
        if attempts >= MAX_ATTEMPTS:
            return IdentityDecision(attempts, None, IdentityResult(None, "no_match"))
        return IdentityDecision(
            attempts,
            "NO_MATCH: no patient matched. Ask the caller to spell the last name and repeat the date of birth.",
            None,
        )
    if not result.startswith("ERROR bad_date") and tool_failures >= MAX_TOOL_FAILURES:
        return IdentityDecision(attempts, None, IdentityResult(None, "system_error"))
    return IdentityDecision(attempts, result, None)


class VerifyIdentityTask(AgentTask[IdentityResult]):
    def __init__(self, chat_ctx: NotGivenOr[ChatContext] = NOT_GIVEN) -> None:
        super().__init__(instructions=INSTRUCTIONS, chat_ctx=chat_ctx)
        self._attempts = 0

    async def on_enter(self) -> None:
        self.session.generate_reply(
            instructions="Say you'll first verify the patient, and ask for the patient's full name and date of birth."
        )

    @function_tool
    async def submit_identity(
        self, context: RunContext[CallState], full_name: str, birth_date: str
    ) -> str | None:
        """Look up the patient. Call only after the caller gave both the full name and the date of birth and confirmed the date you read back.

        Args:
            full_name: The patient's first and last name.
            birth_date: The patient's date of birth as YYYY-MM-DD.
        """
        state = context.userdata
        result = await check_identity(state, full_name, birth_date)
        decision = decide_identity(result, self._attempts, state.tool_failures)
        self._attempts = decision.attempts
        if decision.final is not None:
            self.complete(decision.final)
        return decision.text
