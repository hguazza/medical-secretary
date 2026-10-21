import asyncio
from datetime import date, timedelta

import pytest

from medical_secretary.config import load_practice
from medical_secretary.ehr.mock import Faults, MockEHR
from medical_secretary.ehr.models import EHRError

TODAY = date(2026, 11, 2)  # a Monday


def make_ehr(practice_id: str = "pediatrics-burlington", **faults: object) -> MockEHR:
    return MockEHR(load_practice(practice_id), TODAY, Faults(**faults))  # type: ignore[arg-type]


async def test_lookup_patient_normalizes_name() -> None:
    ehr = make_ehr()
    patient = await ehr.lookup_patient("  emma   JOHNSON ", date(2018, 3, 5))
    assert patient is not None and patient.id == "pat-001"


async def test_lookup_patient_wrong_dob_returns_none() -> None:
    ehr = make_ehr()
    assert await ehr.lookup_patient("Emma Johnson", date(2018, 3, 6)) is None


async def test_slots_only_on_open_days_within_window() -> None:
    ehr = make_ehr("dermatology-demo")
    slots = await ehr.find_slots(TODAY, TODAY + timedelta(days=60))
    days = {s.start.date() for s in slots}
    assert all(d.weekday() < 5 for d in days)  # closed weekends
    assert max(days) <= TODAY + timedelta(days=45)
    assert all(s.status == "free" for s in slots)


async def test_find_slots_clamps_past_and_window() -> None:
    ehr = make_ehr()
    past = await ehr.find_slots(TODAY - timedelta(days=10), TODAY)
    assert past == []
    far = await ehr.find_slots(TODAY + timedelta(days=100), TODAY + timedelta(days=120))
    assert far == []


async def test_find_slots_filters_by_practitioner_and_sorts() -> None:
    ehr = make_ehr()
    slots = await ehr.find_slots(TODAY, TODAY + timedelta(days=3), "dr-patel")
    assert slots and all(s.practitioner_id == "dr-patel" for s in slots)
    assert [s.start for s in slots] == sorted(s.start for s in slots)


async def test_find_slots_unknown_practitioner_raises() -> None:
    ehr = make_ehr()
    with pytest.raises(EHRError) as exc:
        await ehr.find_slots(TODAY, TODAY + timedelta(days=3), "dr-who")
    assert exc.value.code == "practitioner_unknown"


async def test_book_twice_fails() -> None:
    ehr = make_ehr()
    slot = (await ehr.find_slots(TODAY, TODAY + timedelta(days=3)))[0]
    appt = await ehr.book("pat-001", slot.id, "sick")
    assert appt.status == "booked" and appt.slot_id == slot.id
    with pytest.raises(EHRError) as exc:
        await ehr.book("pat-002", slot.id, "sick")
    assert exc.value.code == "slot_unavailable"
    with pytest.raises(EHRError):
        await ehr.book("pat-001", "no-such-slot", "sick")


async def test_seeded_appointment_for_emma() -> None:
    ehr = make_ehr()
    appts = await ehr.list_appointments("pat-001")
    assert [a.id for a in appts] == ["appt-seed-1"]


async def test_reschedule_frees_old_slot() -> None:
    ehr = make_ehr()
    old = (await ehr.list_appointments("pat-001"))[0]
    new_slot = (await ehr.find_slots(TODAY, TODAY + timedelta(days=7)))[-1]
    moved = await ehr.reschedule(old.id, new_slot.id)
    assert moved.slot_id == new_slot.id
    free_ids = {s.id for s in await ehr.find_slots(TODAY, TODAY + timedelta(days=30))}
    assert old.slot_id in free_ids
    assert new_slot.id not in free_ids


async def test_cancel_frees_slot_and_unknown_raises() -> None:
    ehr = make_ehr()
    appt = (await ehr.list_appointments("pat-001"))[0]
    cancelled = await ehr.cancel(appt.id, "feeling better")
    assert cancelled.status == "cancelled"
    assert await ehr.list_appointments("pat-001") == []
    with pytest.raises(EHRError) as exc:
        await ehr.cancel("appt-nope", "x")
    assert exc.value.code == "not_found"


async def test_stale_practitioner_missing_from_ehr() -> None:
    ehr = make_ehr(stale_practitioner_ids={"dr-nguyen"})
    ids = {p.id for p in await ehr.list_practitioners()}
    assert "dr-nguyen" not in ids
    with pytest.raises(EHRError) as exc:
        await ehr.find_slots(TODAY, TODAY + timedelta(days=3), "dr-nguyen")
    assert exc.value.code == "practitioner_unknown"


async def test_fail_ops_raise_unavailable() -> None:
    ehr = make_ehr(fail_ops={"find_slots"})
    with pytest.raises(EHRError) as exc:
        await ehr.find_slots(TODAY, TODAY + timedelta(days=3))
    assert exc.value.code == "unavailable"


async def test_timeout_ops_hang() -> None:
    ehr = make_ehr(timeout_ops={"lookup_patient"})
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(
            ehr.lookup_patient("Emma Johnson", date(2018, 3, 5)), 0.05
        )


async def test_no_slots_fault() -> None:
    ehr = make_ehr(no_slots=True)
    assert await ehr.find_slots(TODAY, TODAY + timedelta(days=30)) == []


async def test_deterministic_slot_ids() -> None:
    a = await make_ehr().find_slots(TODAY, TODAY + timedelta(days=5))
    b = await make_ehr().find_slots(TODAY, TODAY + timedelta(days=5))
    assert [s.id for s in a] == [s.id for s in b]
