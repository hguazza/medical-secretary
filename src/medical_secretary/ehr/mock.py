"""Deterministic in-memory EHR with fault injection for tests and demos."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from medical_secretary.config import Practice
from medical_secretary.ehr.models import (
    Appointment,
    EHRError,
    Patient,
    Practitioner,
    Slot,
)

SLOT_MINUTES = 60

SEED_PATIENTS: list[Patient] = [
    Patient(
        id="pat-001",
        given_name="Emma",
        family_name="Johnson",
        birth_date=date(2018, 3, 5),
    ),
    Patient(
        id="pat-002",
        given_name="Liam",
        family_name="Garcia",
        birth_date=date(2015, 11, 20),
    ),
    Patient(
        id="pat-003",
        given_name="Olivia",
        family_name="Smith",
        birth_date=date(1984, 7, 14),
    ),
]


@dataclass
class Faults:
    latency_s: float = 0.0
    timeout_ops: set[str] = field(default_factory=set)
    fail_ops: set[str] = field(default_factory=set)
    stale_practitioner_ids: set[str] = field(default_factory=set)
    no_slots: bool = False


def _normalize(name: str) -> str:
    return " ".join(name.casefold().split())


class MockEHR:
    def __init__(
        self,
        practice: Practice,
        today: date,
        faults: Faults | None = None,
        patients: list[Patient] | None = None,
    ) -> None:
        self.practice = practice
        self.today = today
        self.faults = faults or Faults()
        self._patients = {p.id: p for p in (patients or SEED_PATIENTS)}
        self._practitioners = {
            p.id: Practitioner(id=p.id, name=p.name, specialty=p.specialty)
            for p in practice.providers
            if p.id not in self.faults.stale_practitioner_ids
        }
        self._slots: dict[str, Slot] = {}
        self._appointments: dict[str, Appointment] = {}
        self._next_appt = 1
        self._generate_slots()
        self._seed_appointment()

    # -- setup -------------------------------------------------------------
    def _generate_slots(self) -> None:
        for offset in range(1, self.practice.booking_window_days + 1):
            day = self.today + timedelta(days=offset)
            hours = self.practice.hours_for(day.weekday())
            if hours is None:
                continue
            close = datetime.combine(day, hours.close)
            for practitioner in self._practitioners.values():
                start = datetime.combine(day, hours.open)
                index = 0
                while start + timedelta(minutes=SLOT_MINUTES) <= close:
                    slot_id = f"{practitioner.id}-{start:%Y%m%d-%H%M}"
                    self._slots[slot_id] = Slot(
                        id=slot_id,
                        practitioner_id=practitioner.id,
                        start=start,
                        end=start + timedelta(minutes=SLOT_MINUTES),
                        status="busy" if index % 3 == 1 else "free",
                    )
                    start += timedelta(minutes=SLOT_MINUTES)
                    index += 1

    def _seed_appointment(self) -> None:
        if "pat-001" not in self._patients:
            return
        free = sorted(
            (s for s in self._slots.values() if s.status == "free"),
            key=lambda s: (s.start, s.practitioner_id),
        )
        if not free:
            return
        slot = free[0]
        slot.status = "busy"
        self._appointments["appt-seed-1"] = Appointment(
            id="appt-seed-1",
            patient_id="pat-001",
            practitioner_id=slot.practitioner_id,
            slot_id=slot.id,
            start=slot.start,
            visit_type=self.practice.visit_types[0].code,
        )

    # -- fault injection ---------------------------------------------------
    async def _enter(self, op: str) -> None:
        if self.faults.latency_s:
            await asyncio.sleep(self.faults.latency_s)
        if op in self.faults.timeout_ops:
            await asyncio.sleep(3600)
        if op in self.faults.fail_ops:
            raise EHRError("unavailable", f"{op} failed (injected)")

    # -- EHRClient ---------------------------------------------------------
    async def lookup_patient(self, full_name: str, birth_date: date) -> Patient | None:
        await self._enter("lookup_patient")
        wanted = _normalize(full_name)
        return next(
            (
                p
                for p in self._patients.values()
                if _normalize(p.full_name) == wanted and p.birth_date == birth_date
            ),
            None,
        )

    async def list_practitioners(self) -> list[Practitioner]:
        await self._enter("list_practitioners")
        return list(self._practitioners.values())

    async def find_slots(
        self, start: date, end: date, practitioner_id: str | None = None
    ) -> list[Slot]:
        await self._enter("find_slots")
        if practitioner_id is not None and practitioner_id not in self._practitioners:
            raise EHRError("practitioner_unknown", practitioner_id)
        if self.faults.no_slots:
            return []
        first = max(start, self.today + timedelta(days=1))
        last = min(end, self.today + timedelta(days=self.practice.booking_window_days))
        return sorted(
            (
                s
                for s in self._slots.values()
                if s.status == "free"
                and first <= s.start.date() <= last
                and (practitioner_id is None or s.practitioner_id == practitioner_id)
            ),
            key=lambda s: (s.start, s.practitioner_id),
        )

    async def book(self, patient_id: str, slot_id: str, visit_type: str) -> Appointment:
        await self._enter("book")
        slot = self._slots.get(slot_id)
        if slot is None or slot.status != "free":
            raise EHRError("slot_unavailable", slot_id)
        slot.status = "busy"
        appt = Appointment(
            id=f"appt-{self._next_appt}",
            patient_id=patient_id,
            practitioner_id=slot.practitioner_id,
            slot_id=slot.id,
            start=slot.start,
            visit_type=visit_type,
        )
        self._next_appt += 1
        self._appointments[appt.id] = appt
        return appt

    async def list_appointments(self, patient_id: str) -> list[Appointment]:
        await self._enter("list_appointments")
        return sorted(
            (
                a
                for a in self._appointments.values()
                if a.patient_id == patient_id and a.status == "booked"
            ),
            key=lambda a: a.start,
        )

    async def reschedule(self, appointment_id: str, new_slot_id: str) -> Appointment:
        await self._enter("reschedule")
        appt = self._appointments.get(appointment_id)
        if appt is None or appt.status != "booked":
            raise EHRError("not_found", appointment_id)
        new_slot = self._slots.get(new_slot_id)
        if new_slot is None or new_slot.status != "free":
            raise EHRError("slot_unavailable", new_slot_id)
        self._slots[appt.slot_id].status = "free"
        new_slot.status = "busy"
        moved = appt.model_copy(
            update={
                "slot_id": new_slot.id,
                "start": new_slot.start,
                "practitioner_id": new_slot.practitioner_id,
            }
        )
        self._appointments[appointment_id] = moved
        return moved

    async def cancel(self, appointment_id: str, reason: str) -> Appointment:
        await self._enter("cancel")
        appt = self._appointments.get(appointment_id)
        if appt is None or appt.status != "booked":
            raise EHRError("not_found", appointment_id)
        self._slots[appt.slot_id].status = "free"
        cancelled = appt.model_copy(update={"status": "cancelled"})
        self._appointments[appointment_id] = cancelled
        return cancelled
