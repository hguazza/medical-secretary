from datetime import date, datetime

from medical_secretary.config import load_practice
from medical_secretary.ehr.models import Slot
from medical_secretary.formatting import describe_slot, speakable_date, speakable_time


def test_speakable_date_and_time() -> None:
    assert speakable_date(date(2026, 11, 3)) == "Tuesday, November 3"
    assert speakable_time(datetime(2026, 11, 3, 9, 0)) == "9:00 AM"
    assert speakable_time(datetime(2026, 11, 3, 14, 30)) == "2:30 PM"


def test_describe_slot_uses_provider_name() -> None:
    practice = load_practice("pediatrics-burlington")
    slot = Slot(
        id="dr-patel-20261103-0900",
        practitioner_id="dr-patel",
        start=datetime(2026, 11, 3, 9),
        end=datetime(2026, 11, 3, 10),
    )
    assert describe_slot(slot, practice) == (
        "Tuesday, November 3 at 9:00 AM with Dr. Priya Patel"
    )
