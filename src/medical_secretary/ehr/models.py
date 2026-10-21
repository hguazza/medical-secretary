"""Subset of FHIR R4 resources the agent needs. Datetimes are practice-local, naive."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel


class Patient(BaseModel):
    id: str
    given_name: str
    family_name: str
    birth_date: date
    phone: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.family_name}"


class Practitioner(BaseModel):
    id: str
    name: str
    specialty: str
    active: bool = True


class Slot(BaseModel):
    id: str
    practitioner_id: str
    start: datetime
    end: datetime
    status: Literal["free", "busy"] = "free"


class Appointment(BaseModel):
    id: str
    patient_id: str
    practitioner_id: str
    slot_id: str
    start: datetime
    visit_type: str
    status: Literal["booked", "cancelled"] = "booked"


class EHRError(Exception):
    """Raised by EHR clients. `code` is machine-readable; see CONTEXT.md."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
