from datetime import date

from medical_secretary.agents.front_desk import practice_info
from medical_secretary.config import Settings, load_practice
from medical_secretary.session_state import new_call_state


def _state():
    return new_call_state(
        load_practice("dermatology-demo"),
        Settings(_env_file=None),  # pyright: ignore[reportCallIssue]
        date(2026, 11, 2),
    )


def test_practice_info_topics() -> None:
    state = _state()
    assert "45 Church Street" in practice_info(state, "address")
    assert "802-555-0199" in practice_info(state, "phone")
    assert "Saturday: closed" in practice_info(state, "hours")
    assert "Dr. Ana Reyes" in practice_info(state, "providers")
