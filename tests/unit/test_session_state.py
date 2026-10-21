from datetime import date

from medical_secretary.config import Settings, load_practice
from medical_secretary.ehr.mock import Faults, MockEHR
from medical_secretary.session_state import new_call_state


def test_new_call_state_wires_mock_ehr_with_faults() -> None:
    practice = load_practice("pediatrics-burlington")
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    state = new_call_state(practice, settings, date(2026, 11, 2), Faults(no_slots=True))
    assert isinstance(state.ehr, MockEHR)
    assert state.ehr.faults.no_slots
    assert state.caller is None and state.tool_failures == 0


def test_record_appends_actions() -> None:
    practice = load_practice("pediatrics-burlington")
    state = new_call_state(practice, Settings(_env_file=None), date(2026, 11, 2))  # pyright: ignore[reportCallIssue]
    state.record("looked up slots")
    assert state.actions_taken == ["looked up slots"]
