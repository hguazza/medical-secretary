from datetime import date

from medical_secretary.config import Settings, load_practice
from medical_secretary.ehr.mock import Faults
from medical_secretary.session_state import VerifiedCaller, new_call_state
from medical_secretary.tasks.verify_identity import (
    IdentityResult,
    check_identity,
    decide_identity,
)


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


_CALLER = VerifiedCaller("pat-001", "Emma Johnson", date(2018, 3, 5))


def test_decide_verified_completes() -> None:
    decision = decide_identity(_CALLER, attempts=0, tool_failures=0)
    assert decision.text is None
    assert decision.final == IdentityResult(_CALLER, "verified")


def test_decide_first_miss_continues() -> None:
    decision = decide_identity("NO_MATCH", attempts=0, tool_failures=0)
    assert decision.attempts == 1
    assert decision.final is None
    assert decision.text is not None and decision.text.startswith("NO_MATCH")


def test_decide_second_miss_is_no_match() -> None:
    decision = decide_identity("NO_MATCH", attempts=1, tool_failures=0)
    assert decision.final == IdentityResult(None, "no_match")
    assert decision.text is None


def test_decide_first_system_failure_continues() -> None:
    decision = decide_identity("ERROR unavailable: x", attempts=0, tool_failures=1)
    assert decision.final is None
    assert decision.text == "ERROR unavailable: x"
    assert decision.attempts == 0


def test_decide_second_system_failure_is_system_error() -> None:
    decision = decide_identity("ERROR unavailable: x", attempts=0, tool_failures=2)
    assert decision.final == IdentityResult(None, "system_error")


def test_decide_bad_date_never_counts() -> None:
    decision = decide_identity("ERROR bad_date: x", attempts=1, tool_failures=0)
    assert decision.final is None and decision.attempts == 1
    assert decision.text == "ERROR bad_date: x"
