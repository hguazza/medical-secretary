import asyncio
from datetime import date

import pytest

from medical_secretary.config import Settings, load_practice
from medical_secretary.ehr.models import EHRError
from medical_secretary.session_state import new_call_state
from medical_secretary.tools.resilience import MAX_TOOL_FAILURES, ToolFailure, guarded


def _state():
    practice = load_practice("pediatrics-burlington")
    return new_call_state(practice, Settings(_env_file=None), date(2026, 11, 2))  # pyright: ignore[reportCallIssue]


async def _ok() -> int:
    return 42


async def _hang() -> int:
    await asyncio.sleep(10)
    return 0


async def _raise(code: str) -> int:
    raise EHRError(code)


async def test_success_passes_through() -> None:
    state = _state()
    assert await guarded(state, "op", _ok(), timeout_s=1) == 42
    assert state.tool_failures == 0


async def test_timeout_counts_as_system_failure() -> None:
    state = _state()
    result = await guarded(state, "find_slots", _hang(), timeout_s=0.01)
    assert result == ToolFailure("timeout")
    assert isinstance(result, ToolFailure)
    assert state.tool_failures == 1
    assert "retry once" in result.message(state)


async def test_unavailable_counts_and_escalates_after_max() -> None:
    state = _state()
    for _ in range(MAX_TOOL_FAILURES):
        result = await guarded(state, "find_slots", _raise("unavailable"), timeout_s=1)
    assert isinstance(result, ToolFailure)
    assert state.tool_failures == MAX_TOOL_FAILURES
    assert "route_to_human" in result.message(state)


async def test_business_errors_do_not_count() -> None:
    state = _state()
    result = await guarded(state, "book", _raise("slot_unavailable"), timeout_s=1)
    assert result == ToolFailure("slot_unavailable")
    assert isinstance(result, ToolFailure)
    assert state.tool_failures == 0
    assert "just taken" in result.message(state)


async def _boom() -> int:
    raise RuntimeError("boom")


async def test_unexpected_exception_is_unavailable() -> None:
    state = _state()
    result = await guarded(state, "find_slots", _boom(), timeout_s=1)
    assert result == ToolFailure("unavailable")
    assert state.tool_failures == 1


async def test_cancellation_is_not_swallowed() -> None:
    state = _state()
    task = asyncio.ensure_future(guarded(state, "op", _hang(), timeout_s=5))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert state.tool_failures == 0
