import json
from datetime import date

from medical_secretary.config import Settings, load_practice
from medical_secretary.handoff import build_handoff_summary
from medical_secretary.session_state import VerifiedCaller, new_call_state


def _state():
    practice = load_practice("pediatrics-burlington")
    return new_call_state(practice, Settings(_env_file=None), date(2026, 11, 2))  # pyright: ignore[reportCallIssue]


def test_summary_for_unverified_caller_uses_default_team() -> None:
    state = _state()
    summary = build_handoff_summary(
        state, "caller_request", "routine", "Wants a person."
    )
    assert summary.verified is False and summary.caller_name is None
    assert summary.team == "front-desk"


def test_summary_routes_clinical_and_copies_actions() -> None:
    state = _state()
    state.caller = VerifiedCaller("pat-001", "Emma Johnson", date(2018, 3, 5))
    state.intent = "scheduling"
    state.record("booked appt-1")
    summary = build_handoff_summary(state, "clinical", "urgent", "Infant fever.")
    assert summary.team == "nurse-line"
    assert summary.caller_name == "Emma Johnson" and summary.verified
    assert summary.actions_taken == ["booked appt-1"]
    state.record("later action")
    assert summary.actions_taken == ["booked appt-1"]  # snapshot, not alias
    payload = json.loads(summary.to_json())
    assert payload["priority"] == "urgent" and payload["intent"] == "scheduling"
