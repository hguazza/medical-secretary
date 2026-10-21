"""Scheduling tool logic, independent of LiveKit so it is unit-testable.

Every function returns text for the LLM: success prefixes (SLOTS:, BOOKED:, ...)
or an `ERROR ...` line with guidance on what to tell the caller.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from medical_secretary.ehr.models import Appointment
from medical_secretary.formatting import (
    describe_appointment,
    describe_slot,
    speakable_date,
)
from medical_secretary.tools.resilience import ToolFailure, guarded

if TYPE_CHECKING:
    from medical_secretary.session_state import CallState

MAX_OPTIONS = 3
_NOT_VERIFIED = "ERROR not_verified: the patient must be verified before scheduling."
_NEEDS_CONFIRMATION = (
    "ERROR not_confirmed: read back the details to the caller and wait for a clear yes, "
    "then call again with caller_confirmed=true."
)


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


async def _own_appointment(state: CallState, appointment_id: str) -> Appointment | str:
    assert state.caller is not None
    appts = await guarded(
        state,
        "list_appointments",
        state.ehr.list_appointments(state.caller.patient_id),
        timeout_s=state.settings.ehr_timeout_s,
    )
    if isinstance(appts, ToolFailure):
        return appts.message(state)
    match = next((a for a in appts if a.id == appointment_id), None)
    if match is None:
        return "ERROR not_found: that is not one of this patient's upcoming appointments. Call list_appointments."
    return match


async def find_slots(
    state: CallState,
    visit_type: str,
    start_date: str,
    end_date: str,
    provider_id: str | None = None,
) -> str:
    if state.caller is None:
        return _NOT_VERIFIED
    practice = state.practice
    if practice.visit_type(visit_type) is None:
        codes = ", ".join(v.code for v in practice.visit_types)
        return f"ERROR unknown_visit_type: use one of: {codes}."
    if provider_id and practice.provider(provider_id) is None:
        names = ", ".join(f"{p.name} (id {p.id})" for p in practice.providers)
        return f"ERROR unknown_provider: this practice's providers are {names}."
    start, end = _parse_date(start_date), _parse_date(end_date)
    if start is None or end is None:
        return "ERROR bad_date: start_date and end_date must be YYYY-MM-DD."

    slots = await guarded(
        state,
        "find_slots",
        state.ehr.find_slots(start, end, provider_id),
        timeout_s=state.settings.ehr_timeout_s,
    )
    if isinstance(slots, ToolFailure):
        return slots.message(state)
    if not slots:
        last = state.today + timedelta(days=practice.booking_window_days)
        return (
            "ERROR no_slots: no openings in that range. Bookable dates are tomorrow "
            f"through {speakable_date(last)}. Offer another provider or a wider range, "
            "or offer staff help."
        )
    state.record(f"searched {visit_type} slots {start}..{end}")
    lines = [
        f"- slot_id={s.id} : {describe_slot(s, practice)}" for s in slots[:MAX_OPTIONS]
    ]
    return "SLOTS: offer these to the caller (never read slot ids):\n" + "\n".join(
        lines
    )


async def book(
    state: CallState, slot_id: str, visit_type: str, caller_confirmed: bool
) -> str:
    if state.caller is None:
        return _NOT_VERIFIED
    if not caller_confirmed:
        return _NEEDS_CONFIRMATION
    if state.practice.visit_type(visit_type) is None:
        return "ERROR unknown_visit_type."
    appt = await guarded(
        state,
        "book",
        state.ehr.book(state.caller.patient_id, slot_id, visit_type),
        timeout_s=state.settings.ehr_timeout_s,
    )
    if isinstance(appt, ToolFailure):
        return appt.message(state)
    state.record(f"booked {appt.id}")
    return f"BOOKED: {describe_appointment(appt, state.practice)}. Confirm it to the caller once."


async def list_appointments(state: CallState) -> str:
    if state.caller is None:
        return _NOT_VERIFIED
    appts = await guarded(
        state,
        "list_appointments",
        state.ehr.list_appointments(state.caller.patient_id),
        timeout_s=state.settings.ehr_timeout_s,
    )
    if isinstance(appts, ToolFailure):
        return appts.message(state)
    if not appts:
        return "APPOINTMENTS: none upcoming."
    lines = [
        f"- appointment_id={a.id} : {describe_appointment(a, state.practice)}"
        for a in appts
    ]
    return "APPOINTMENTS:\n" + "\n".join(lines)


async def reschedule(
    state: CallState, appointment_id: str, new_slot_id: str, caller_confirmed: bool
) -> str:
    if state.caller is None:
        return _NOT_VERIFIED
    if not caller_confirmed:
        return _NEEDS_CONFIRMATION
    own = await _own_appointment(state, appointment_id)
    if isinstance(own, str):
        return own
    moved = await guarded(
        state,
        "reschedule",
        state.ehr.reschedule(appointment_id, new_slot_id),
        timeout_s=state.settings.ehr_timeout_s,
    )
    if isinstance(moved, ToolFailure):
        return moved.message(state)
    state.record(f"rescheduled {appointment_id}")
    return f"RESCHEDULED: {describe_appointment(moved, state.practice)}."


async def cancel(
    state: CallState, appointment_id: str, reason: str, caller_confirmed: bool
) -> str:
    if state.caller is None:
        return _NOT_VERIFIED
    if not caller_confirmed:
        return _NEEDS_CONFIRMATION
    own = await _own_appointment(state, appointment_id)
    if isinstance(own, str):
        return own
    cancelled = await guarded(
        state,
        "cancel",
        state.ehr.cancel(appointment_id, reason),
        timeout_s=state.settings.ehr_timeout_s,
    )
    if isinstance(cancelled, ToolFailure):
        return cancelled.message(state)
    state.record(f"cancelled {appointment_id}")
    return f"CANCELLED: {describe_appointment(cancelled, state.practice)}."
