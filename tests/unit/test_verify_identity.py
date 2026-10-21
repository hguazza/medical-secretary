from datetime import date

from medical_secretary.config import Settings, load_practice
from medical_secretary.ehr.mock import Faults
from medical_secretary.session_state import VerifiedCaller, new_call_state
from medical_secretary.tasks.verify_identity import check_identity


def _state(faults: Faults | None = None):
    return new_call_state(
        load_practice("pediatrics-burlington"),
        Settings(_env_file=None),  # pyright: ignore[reportCallIssue]
        date(2026, 11, 2),
        faults,
    )


async def test_check_identity_match() -> None:
    result = await check_identity(_state(), "emma johnson", "2018-03-05")
    assert isinstance(result, VerifiedCaller) and result.patient_id == "pat-001"


async def test_submit_identity_rejects_non_iso_date() -> None:
    result = await check_identity(_state(), "Emma Johnson", "March fifth 2018")
    assert isinstance(result, str) and result.startswith("ERROR bad_date")


async def test_check_identity_no_match() -> None:
    result = await check_identity(_state(), "Emma Jonson", "2018-03-05")
    assert result == "NO_MATCH"


async def test_check_identity_system_failure() -> None:
    state = _state(Faults(fail_ops={"lookup_patient"}))
    result = await check_identity(state, "Emma Johnson", "2018-03-05")
    assert isinstance(result, str) and result.startswith("ERROR unavailable")
    assert state.tool_failures == 1
