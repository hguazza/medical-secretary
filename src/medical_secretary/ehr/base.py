"""The contract every EHR integration implements."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from medical_secretary.ehr.models import Appointment, Patient, Practitioner, Slot


class EHRClient(Protocol):
    async def lookup_patient(
        self, full_name: str, birth_date: date
    ) -> Patient | None: ...

    async def list_practitioners(self) -> list[Practitioner]: ...

    async def find_slots(
        self, start: date, end: date, practitioner_id: str | None = None
    ) -> list[Slot]: ...

    async def book(
        self, patient_id: str, slot_id: str, visit_type: str
    ) -> Appointment: ...

    async def list_appointments(self, patient_id: str) -> list[Appointment]: ...

    async def reschedule(
        self, appointment_id: str, new_slot_id: str
    ) -> Appointment: ...

    async def cancel(self, appointment_id: str, reason: str) -> Appointment: ...
