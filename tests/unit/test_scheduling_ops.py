from datetime import date

from medical_secretary import scheduling_ops as ops
from medical_secretary.config import Settings, load_practice
from medical_secretary.ehr.mock import Faults
from medical_secretary.session_state import VerifiedCaller, new_call_state

TODAY = date(2026, 11, 2)


def _state(faults: Faults | None = None, verified: bool = True):
    state = new_call_state(
        load_practice("pediatrics-burlington"),
        Settings(_env_file=None),  # pyright: ignore[reportCallIssue]
        TODAY,
        faults,
    )
    if verified:
        state.caller = VerifiedCaller("pat-001", "Emma Johnson", date(2018, 3, 5))
    return state


def _first_slot_id(text: str) -> str:
    return text.split("slot_id=")[1].split(" ")[0]


async def test_find_slots_lists_at_most_three_with_ids() -> None:
    text = await ops.find_slots(_state(), "sick", "2026-11-03", "2026-11-06")
    assert text.startswith("SLOTS:")
    assert text.count("slot_id=") == ops.MAX_OPTIONS
    assert "Dr." in text


async def test_find_slots_requires_verified_caller() -> None:
    text = await ops.find_slots(
        _state(verified=False), "sick", "2026-11-03", "2026-11-06"
    )
    assert text.startswith("ERROR") and "verified" in text


async def test_find_slots_rejects_unknown_visit_type() -> None:
    text = await ops.find_slots(_state(), "massage", "2026-11-03", "2026-11-06")
    assert text.startswith("ERROR") and "well-child" in text


async def test_find_slots_rejects_bad_dates() -> None:
    text = await ops.find_slots(_state(), "sick", "next tuesday", "2026-11-06")
    assert text.startswith("ERROR") and "YYYY-MM-DD" in text


async def test_find_slots_reports_empty_range() -> None:
    text = await ops.find_slots(_state(), "sick", "2027-03-01", "2027-03-05")
    assert text.startswith("ERROR no_slots")
    assert "December 2" in text  # last bookable day = today + 30 days


async def test_find_slots_provider_not_in_practice() -> None:
    text = await ops.find_slots(
        _state(), "sick", "2026-11-03", "2026-11-06", "dr-house"
    )
    assert text.startswith("ERROR") and "Dr. Priya Patel" in text


async def test_find_slots_stale_provider() -> None:
    state = _state(Faults(stale_practitioner_ids={"dr-nguyen"}))
    text = await ops.find_slots(state, "sick", "2026-11-03", "2026-11-06", "dr-nguyen")
    assert text.startswith("ERROR practitioner_unknown")


async def test_find_slots_timeout_message() -> None:
    state = _state(Faults(timeout_ops={"find_slots"}))
    state.settings.ehr_timeout_s = 0.01
    text = await ops.find_slots(state, "sick", "2026-11-03", "2026-11-06")
    assert text.startswith("ERROR timeout")
    assert state.tool_failures == 1


async def test_book_requires_confirmation() -> None:
    state = _state()
    slot_id = _first_slot_id(
        await ops.find_slots(state, "sick", "2026-11-03", "2026-11-06")
    )
    text = await ops.book(state, slot_id, "sick", caller_confirmed=False)
    assert text.startswith("ERROR") and "read back" in text
    assert len(await state.ehr.list_appointments("pat-001")) == 1


async def test_book_success_records_action() -> None:
    state = _state()
    slot_id = _first_slot_id(
        await ops.find_slots(state, "sick", "2026-11-03", "2026-11-06")
    )
    text = await ops.book(state, slot_id, "sick", caller_confirmed=True)
    assert text.startswith("BOOKED:") and "Sick visit" in text
    assert state.actions_taken and state.actions_taken[-1].startswith("booked")


async def test_book_unavailable_slot_message() -> None:
    state = _state()
    slot_id = _first_slot_id(
        await ops.find_slots(state, "sick", "2026-11-03", "2026-11-06")
    )
    await ops.book(state, slot_id, "sick", caller_confirmed=True)
    text = await ops.book(state, slot_id, "sick", caller_confirmed=True)
    assert text.startswith("ERROR slot_unavailable") and "just taken" in text


async def test_list_appointments() -> None:
    text = await ops.list_appointments(_state())
    assert text.startswith("APPOINTMENTS:") and "appointment_id=appt-seed-1" in text


async def test_cancel_rejects_foreign_appointment() -> None:
    state = _state()
    other = await state.ehr.book(
        "pat-002",
        _first_slot_id(await ops.find_slots(state, "sick", "2026-11-03", "2026-11-06")),
        "sick",
    )
    text = await ops.cancel(state, other.id, "no longer needed", caller_confirmed=True)
    assert text.startswith("ERROR") and "not one of this patient's" in text
    assert len(await state.ehr.list_appointments("pat-002")) == 1


async def test_cancel_and_reschedule_success() -> None:
    state = _state()
    slot_id = _first_slot_id(
        await ops.find_slots(state, "sick", "2026-11-10", "2026-11-12")
    )
    moved = await ops.reschedule(state, "appt-seed-1", slot_id, caller_confirmed=True)
    assert moved.startswith("RESCHEDULED:")
    cancelled = await ops.cancel(
        state, "appt-seed-1", "feeling better", caller_confirmed=True
    )
    assert cancelled.startswith("CANCELLED:")


async def test_reschedule_and_cancel_require_confirmation() -> None:
    state = _state()
    assert (
        await ops.cancel(state, "appt-seed-1", "x", caller_confirmed=False)
    ).startswith("ERROR not_confirmed")
    assert (
        await ops.reschedule(state, "appt-seed-1", "any", caller_confirmed=False)
    ).startswith("ERROR not_confirmed")
