"""Timeouts and model-readable errors for every EHR-backed tool."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from medical_secretary.ehr.models import EHRError

if TYPE_CHECKING:
    from medical_secretary.session_state import CallState

logger = logging.getLogger("medical_secretary.tools")

MAX_TOOL_FAILURES = 2
SYSTEM_ERROR_CODES = frozenset({"timeout", "unavailable"})

_GUIDANCE = {
    "timeout": "The scheduling system didn't respond. Apologize briefly; you may retry once.",
    "unavailable": "The scheduling system is having problems. Apologize briefly; you may retry once.",
    "slot_unavailable": "That time was just taken. Apologize and offer other times.",
    "not_found": "No matching record was found.",
    "practitioner_unknown": "That provider isn't available at this practice. Offer the practice's other providers; never invent one.",
}
_ESCALATE = (
    " The system has failed repeatedly: tell the caller you're having trouble with the "
    "system and transfer them to staff with route_to_human."
)


@dataclass(frozen=True)
class ToolFailure:
    code: str

    def message(self, state: CallState) -> str:
        text = f"ERROR {self.code}: {_GUIDANCE.get(self.code, 'The request failed.')}"
        if self.code in SYSTEM_ERROR_CODES and state.tool_failures >= MAX_TOOL_FAILURES:
            text += _ESCALATE
        return text


async def guarded[T](
    state: CallState, op: str, call: Awaitable[T], *, timeout_s: float
) -> T | ToolFailure:
    try:
        return await asyncio.wait_for(call, timeout_s)
    except TimeoutError:
        code = "timeout"
    except EHRError as exc:
        code = exc.code
    if code in SYSTEM_ERROR_CODES:
        state.tool_failures += 1
        logger.warning("ehr %s failed: %s (failures=%d)", op, code, state.tool_failures)
    return ToolFailure(code)
