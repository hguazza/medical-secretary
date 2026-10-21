"""First agent on every call: triage, practice info and routing."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from livekit.agents import Agent, RunContext, function_tool

from medical_secretary.agents.human_handoff import HumanHandoffAgent
from medical_secretary.agents.scheduling import SchedulingAgent
from medical_secretary.handoff import AgentHandoffReason
from medical_secretary.prompts import build_instructions, practice_facts
from medical_secretary.session_state import CallState

ROLE_TEMPLATE = """\
# Your role: front desk
Greet callers, check for emergencies first, then find out what they need.
- Appointments (book, move, check, cancel): call route_to_scheduling right away, without asking follow-up questions first; the scheduling agent gathers the details. A caller who mentions a mild, ordinary symptom (a cough, a rash, a sore throat) while asking to be seen wants a sick visit: route to scheduling, do not transfer to staff.
- Hours, address, phone or which providers work here: call get_practice_info.
- Anything else (prescription refills, billing, test results, records, new patients): call route_to_human right away (reason out_of_scope); do not ask whether they want to be transferred.
- If the caller asks for a person, is distressed, or describes worrying symptoms or asks a clinical question about them, call route_to_human (reason clinical and priority urgent for distress or symptoms).
- To transfer, call route_to_human in this same turn and say nothing before it: never tell the caller you are connecting them without calling it. The transfer message, including acknowledging a worried caller, is spoken for you."""


def practice_info(state: CallState, topic: str) -> str:
    p = state.practice
    if topic == "address":
        return f"{p.name} is at {p.address}."
    if topic == "phone":
        return f"The practice phone number is {p.phone}."
    if topic == "providers":
        return (
            "Providers: "
            + "; ".join(f"{x.name}, {x.specialty}" for x in p.providers)
            + "."
        )
    facts = practice_facts(p, state.today)
    return next(line for line in facts.splitlines() if line.startswith("- Hours:"))[2:]


class FrontDeskAgent(Agent):
    SKILLS: tuple[str, ...] = ("escalation-rules",)

    def __init__(self, state: CallState, skills: Sequence[str] | None = None) -> None:
        role = ROLE_TEMPLATE.format(out_of_scope=state.practice.out_of_scope_message)
        chosen = self.SKILLS if skills is None else tuple(skills)
        super().__init__(instructions=build_instructions(role, state, chosen))

    @function_tool
    async def route_to_scheduling(
        self, context: RunContext[CallState], reason: str
    ) -> SchedulingAgent:
        """Hand the caller to scheduling for booking, rescheduling, checking or cancelling appointments.

        Args:
            reason: What the caller wants, in a few words.
        """
        context.userdata.intent = f"scheduling: {reason}"
        return SchedulingAgent(
            context.userdata, chat_ctx=self.chat_ctx.copy(exclude_instructions=True)
        )

    @function_tool
    async def route_to_human(
        self,
        context: RunContext[CallState],
        reason: AgentHandoffReason,
        priority: Literal["routine", "urgent"],
        summary: str,
    ) -> HumanHandoffAgent:
        """Transfer the caller to practice staff.

        Args:
            reason: clinical for symptoms, distress or clinical questions; caller_request when they ask for a person; out_of_scope for requests you don't handle.
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

    @function_tool
    async def get_practice_info(
        self,
        context: RunContext[CallState],
        topic: Literal["hours", "address", "phone", "providers"],
    ) -> str:
        """Look up practice hours, address, phone number or providers.

        Args:
            topic: Which fact the caller asked about.
        """
        return practice_info(context.userdata, topic)
