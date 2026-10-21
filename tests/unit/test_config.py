from pathlib import Path
from typing import Any

import pytest
import yaml

from medical_secretary.config import (
    PracticeNotFoundError,
    Settings,
    available_practices,
    load_practice,
)


def _minimal(practice_id: str = "tiny") -> dict[str, Any]:
    return {
        "id": practice_id,
        "name": "Tiny Clinic",
        "timezone": "America/New_York",
        "phone": "802-555-0100",
        "address": "1 Main St, Burlington, VT",
        "hours": {"mon": {"open": "09:00", "close": "17:00"}},
        "greeting": "Thanks for calling Tiny Clinic.",
        "tone": "warm",
        "providers": [{"id": "dr-a", "name": "Dr. A", "specialty": "Family"}],
        "visit_types": [{"code": "sick", "label": "Sick visit", "duration_min": 20}],
        "booking_window_days": 14,
        "escalation": {"default_team": "front-desk", "urgent_contact": "the nurse"},
        "out_of_scope_message": "I can't help with that yet.",
    }


def _write(tmp_path: Path, name: str, data: dict[str, Any]) -> None:
    (tmp_path / f"{name}.yaml").write_text(yaml.safe_dump(data))


@pytest.mark.parametrize("practice_id", ["pediatrics-burlington", "dermatology-demo"])
def test_bundled_practices_load(practice_id: str) -> None:
    practice = load_practice(practice_id)
    assert practice.id == practice_id
    assert practice.providers
    assert practice.visit_types
    assert "escalation-rules" in practice.skills


def test_available_practices_lists_yaml_files() -> None:
    assert {"pediatrics-burlington", "dermatology-demo"} <= set(available_practices())


def test_unknown_practice_error_lists_available() -> None:
    with pytest.raises(PracticeNotFoundError, match="dermatology-demo"):
        load_practice("does-not-exist")


def test_id_must_match_filename(tmp_path: Path) -> None:
    _write(tmp_path, "a", _minimal("b"))
    with pytest.raises(ValueError, match="does not match"):
        load_practice("a", practices_dir=tmp_path)


def test_invalid_weekday_rejected(tmp_path: Path) -> None:
    data = _minimal()
    data["hours"] = {"funday": {"open": "09:00", "close": "17:00"}}
    _write(tmp_path, "tiny", data)
    with pytest.raises(ValueError):
        load_practice("tiny", practices_dir=tmp_path)


def test_close_before_open_rejected(tmp_path: Path) -> None:
    data = _minimal()
    data["hours"] = {"mon": {"open": "17:00", "close": "09:00"}}
    _write(tmp_path, "tiny", data)
    with pytest.raises(ValueError, match="close must be after open"):
        load_practice("tiny", practices_dir=tmp_path)


def test_invalid_timezone_rejected(tmp_path: Path) -> None:
    data = _minimal()
    data["timezone"] = "Mars/Olympus"
    _write(tmp_path, "tiny", data)
    with pytest.raises(ValueError, match="timezone"):
        load_practice("tiny", practices_dir=tmp_path)


def test_lookups_and_routing() -> None:
    practice = load_practice("pediatrics-burlington")
    assert practice.provider("dr-patel") is not None
    assert practice.provider("dr-nobody") is None
    assert practice.visit_type("sick") is not None
    assert practice.team_for("clinical") == "nurse-line"
    assert practice.team_for("unknown-reason") == practice.escalation.default_team
    assert practice.hours_for(6) is None  # Sunday closed


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("PRACTICE_ID", "EHR_TIMEOUT_S", "LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
    assert settings.practice_id == "pediatrics-burlington"
    assert settings.ehr_timeout_s == 2.5
    assert settings.llm_model == "openai/gpt-4.1-mini"
