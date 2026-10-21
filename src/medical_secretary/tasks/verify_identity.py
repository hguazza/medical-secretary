"""Collect and verify the patient's identity (name + date of birth)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

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


@dataclass
class IdentityResult:
    caller: VerifiedCaller | None
    attempts: int


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


class VerifyIdentityTask(AgentTask[IdentityResult]):
    MAX_ATTEMPTS = 2

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
        if isinstance(result, VerifiedCaller):
            self._attempts += 1
            self.complete(IdentityResult(result, self._attempts))
            return None
        if result == "NO_MATCH":
            self._attempts += 1
            if self._attempts >= self.MAX_ATTEMPTS:
                self.complete(IdentityResult(None, self._attempts))
                return None
            return "NO_MATCH: no patient matched. Ask the caller to spell the last name and repeat the date of birth."
        if state.tool_failures >= MAX_TOOL_FAILURES:
            self.complete(IdentityResult(None, self._attempts))
            return None
        return result
