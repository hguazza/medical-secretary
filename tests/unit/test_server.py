import logging
from datetime import UTC, date, datetime

import pytest

from medical_secretary.config import load_practice
from medical_secretary.server import practice_today, resolve_practice_id


def test_resolve_practice_id_from_metadata() -> None:
    assert (
        resolve_practice_id('{"practice_id": "dermatology-demo"}', "x")
        == "dermatology-demo"
    )


def test_resolve_practice_id_falls_back() -> None:
    assert resolve_practice_id(None, "pediatrics-burlington") == "pediatrics-burlington"
    assert resolve_practice_id("", "a") == "a"
    assert resolve_practice_id("not json", "a") == "a"
    assert resolve_practice_id('{"other": 1}', "a") == "a"
    assert resolve_practice_id("[1, 2]", "a") == "a"


def test_resolve_practice_id_rejects_invalid_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="medical_secretary"):
        assert resolve_practice_id('{"practice_id": "../etc"}', "a") == "a"
        assert resolve_practice_id('{"practice_id": "Bad_ID"}', "a") == "a"
        assert resolve_practice_id('{"practice_id": "-x"}', "a") == "a"
    assert "invalid practice_id" in caplog.text


def test_practice_today_uses_practice_timezone() -> None:
    practice = load_practice("pediatrics-burlington")
    # 02:00 UTC on Nov 3 is still Nov 2 in New York
    assert practice_today(practice, datetime(2026, 11, 3, 2, 0, tzinfo=UTC)) == date(
        2026, 11, 2
    )
