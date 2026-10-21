"""Turn EHR data into text a TTS engine reads naturally."""

from __future__ import annotations

from datetime import date, datetime

from medical_secretary.config import Practice
from medical_secretary.ehr.models import Appointment, Slot


def speakable_date(d: date) -> str:
    return f"{d:%A, %B} {d.day}"


def speakable_time(dt: datetime) -> str:
    hour = dt.hour % 12 or 12
    return f"{hour}:{dt:%M} {'AM' if dt.hour < 12 else 'PM'}"


def _provider_name(practice: Practice, practitioner_id: str) -> str:
    provider = practice.provider(practitioner_id)
    return provider.name if provider else "a provider"


def describe_slot(slot: Slot, practice: Practice) -> str:
    return (
        f"{speakable_date(slot.start.date())} at {speakable_time(slot.start)} "
        f"with {_provider_name(practice, slot.practitioner_id)}"
    )


def describe_appointment(appt: Appointment, practice: Practice) -> str:
    visit = practice.visit_type(appt.visit_type)
    label = visit.label if visit else appt.visit_type
    return (
        f"{label} on {speakable_date(appt.start.date())} at {speakable_time(appt.start)} "
        f"with {_provider_name(practice, appt.practitioner_id)}"
    )
