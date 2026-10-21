"""Book, reschedule and cancel appointments for a verified patient."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from livekit.agents import Agent, ChatContext, RunContext, function_tool

from medical_secretary import scheduling_ops as ops
from medical_secretary.agents.human_handoff import HumanHandoffAgent
from medical_secretary.prompts import build_instructions
from medical_secretary.session_state import CallState
from medical_secretary.tasks.verify_identity import VerifyIdentityTask

ROLE = """\
# Your role: scheduling
You help a verified patient book, reschedule, check or cancel appointments. Use the tools for every fact about availability or appointments. Convert dates the caller says into YYYY-MM-DD using today's date, and when the caller names a visit type and a time frame such as this week or next week, call find_slots right away instead of asking to confirm the dates. If a provider the caller names is not in the practice facts or find_slots reports the provider is unavailable, say so and offer the other providers. Before calling a scheduling tool, say one short holding phrase such as "One moment while I check." Before booking, rescheduling or cancelling, read back the details and set caller_confirmed to true only after a clear yes. If the caller asks for a person, call route_to_human right away; do not ask why or try to help first. For anything else that isn't scheduling, also call route_to_human."""


class SchedulingAgent(Agent):
    SKILLS: tuple[str, ...] = ("escalation-rules", "scheduling-policy")

    def __init__(
        self,
        state: CallState,
        chat_ctx: ChatContext | None = None,
        skills: Sequence[str] | None = None,
    ) -> None:
        self._state = state
        self._skills = self.SKILLS if skills is None else tuple(skills)
        super().__init__(instructions=self._compose(), chat_ctx=chat_ctx)

    def _compose(self) -> str:
        instructions = build_instructions(ROLE, self._state, self._skills)
        caller = self._state.caller
        if caller is None:
            return instructions
        return (
            f"{instructions}\n\n# Verified patient\n"
            f"{caller.full_name} (id {caller.patient_id}) is already verified. "
            "Do not ask for their name or date of birth again."
        )

    async def on_enter(self) -> None:
        state: CallState = self.session.userdata
        state.intent = state.intent or "scheduling"
        if state.caller is None:
            result = await VerifyIdentityTask(
                chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
            )
            if result.caller is None:
                if result.outcome == "system_error":
                    state.record("identity lookup unavailable")
                    reason = "system_error"
                    summary = "The scheduling system was unavailable during identity lookup; the caller was not verified."
                else:
                    state.record("identity not verified")
                    reason = "identity_not_verified"
                    summary = "Could not verify the patient's identity by name and date of birth."
                self.session.update_agent(
                    HumanHandoffAgent(
                        state,
                        reason=reason,
                        priority="routine",
                        summary=summary,
                        chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
                    )
                )
                return
            state.caller = result.caller
            state.record(f"verified {result.caller.patient_id}")
            await self.update_instructions(self._compose())
        self.session.generate_reply(
            instructions="The patient is verified. Continue with what the caller wants to schedule; if unclear, ask."
        )

    @function_tool
    async def find_slots(
        self,
        context: RunContext[CallState],
        visit_type: str,
        start_date: str,
        end_date: str,
        provider_id: str | None = None,
    ) -> str:
        """Find open appointment times.

        Args:
            visit_type: Visit type code from the practice facts.
            start_date: First acceptable date, YYYY-MM-DD.
            end_date: Last acceptable date, YYYY-MM-DD.
            provider_id: Provider id from the practice facts, only if the caller asked for one.
        """
        return await ops.find_slots(
            context.userdata, visit_type, start_date, end_date, provider_id
        )

    @function_tool
    async def book_appointment(
        self,
        context: RunContext[CallState],
        slot_id: str,
        visit_type: str,
        caller_confirmed: bool,
    ) -> str:
        """Book a slot returned by find_slots.

        Args:
            slot_id: The slot_id from find_slots.
            visit_type: Visit type code.
            caller_confirmed: True only after you read back the details and the caller clearly said yes.
        """
        return await ops.book(context.userdata, slot_id, visit_type, caller_confirmed)

    @function_tool
    async def list_appointments(self, context: RunContext[CallState]) -> str:
        """List the verified patient's upcoming appointments."""
        return await ops.list_appointments(context.userdata)

    @function_tool
    async def reschedule_appointment(
        self,
        context: RunContext[CallState],
        appointment_id: str,
        new_slot_id: str,
        caller_confirmed: bool,
    ) -> str:
        """Move an existing appointment to a new slot.

        Args:
            appointment_id: The appointment_id from list_appointments.
            new_slot_id: The slot_id from find_slots.
            caller_confirmed: True only after read-back and a clear yes.
        """
        return await ops.reschedule(
            context.userdata, appointment_id, new_slot_id, caller_confirmed
        )

    @function_tool
    async def cancel_appointment(
        self,
        context: RunContext[CallState],
        appointment_id: str,
        reason: str,
        caller_confirmed: bool,
    ) -> str:
        """Cancel an existing appointment.

        Args:
            appointment_id: The appointment_id from list_appointments.
            reason: The caller's reason, in a few words.
            caller_confirmed: True only after read-back and a clear yes.
        """
        return await ops.cancel(
            context.userdata, appointment_id, reason, caller_confirmed
        )

    @function_tool
    async def route_to_human(
        self,
        context: RunContext[CallState],
        reason: str,
        priority: Literal["routine", "urgent"],
        summary: str,
    ) -> HumanHandoffAgent:
        """Transfer the caller to practice staff.

        Args:
            reason: One of clinical, billing, records, scheduling, caller_request, system_error, out_of_scope.
            priority: urgent for distress or worrying symptoms, otherwise routine.
            summary: Two sentences for staff: who is calling, what they need, what was already done.
        """
        context.userdata.record(f"escalated: {reason}")
        return HumanHandoffAgent(
            context.userdata,
            reason,
            priority,
            summary,
            chat_ctx=self.chat_ctx.copy(exclude_instructions=True),
        )
