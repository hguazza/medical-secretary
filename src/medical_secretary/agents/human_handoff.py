"""Escalation to practice staff with full context (simulated transfer in v0)."""

from __future__ import annotations

import logging

from livekit.agents import Agent, ChatContext, get_job_context

from medical_secretary.handoff import HandoffSummary, Priority, build_handoff_summary
from medical_secretary.prompts import build_instructions
from medical_secretary.session_state import CallState

logger = logging.getLogger("medical_secretary.handoff")

ROLE = """\
# Your role: transfer to staff
The caller is being transferred to a person at the practice. Your only job is to tell them, in one or two warm sentences, which team will help and that the team will already have the details of this call, then ask them to stay on the line. Whatever the caller says next, including thanks or small talk, answer with that same reassurance: staff will help and already have the details. Never ask whether there is anything else you can help with. Do not ask new questions, do not collect more information, and do not give medical advice. If they mention an emergency, tell them to hang up and call 911."""


async def publish_handoff(summary: HandoffSummary) -> None:
    try:
        ctx = get_job_context()
    except RuntimeError:  # not inside a LiveKit job (tests, scripts)
        return
    await ctx.room.local_participant.publish_data(
        summary.to_json(), topic="handoff", reliable=True
    )


class HumanHandoffAgent(Agent):
    def __init__(
        self,
        state: CallState,
        reason: str,
        priority: Priority,
        summary: str,
        chat_ctx: ChatContext | None = None,
    ) -> None:
        super().__init__(
            instructions=build_instructions(ROLE, state, []), chat_ctx=chat_ctx
        )
        self._reason = reason
        self._priority: Priority = priority
        self._summary = summary

    async def on_enter(self) -> None:
        state: CallState = self.session.userdata
        handoff = build_handoff_summary(
            state, self._reason, self._priority, self._summary
        )
        state.handoff = handoff
        logger.info("human handoff", extra={"handoff": handoff.to_dict()})
        await publish_handoff(handoff)
        self.session.generate_reply(
            instructions=f"Tell the caller you're connecting them with the {handoff.team.replace('-', ' ')} team now."
        )
