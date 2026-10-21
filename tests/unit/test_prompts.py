from datetime import date

from medical_secretary.config import Settings, load_practice
from medical_secretary.prompts import BASE_RULES, build_instructions
from medical_secretary.session_state import new_call_state


def _state(practice_id: str = "pediatrics-burlington"):
    return new_call_state(
        load_practice(practice_id),
        Settings(_env_file=None),  # pyright: ignore[reportCallIssue]
        date(2026, 11, 2),
    )


def test_instructions_include_rules_facts_role_and_skills() -> None:
    text = build_instructions("ROLE BLOCK", _state(), ["escalation-rules"])
    assert BASE_RULES in text
    assert "Lake Champlain Pediatrics" in text
    assert "Monday, November 2, 2026" in text
    assert "Dr. Priya Patel (id dr-patel," in text
    assert "ROLE BLOCK" in text
    assert "## Playbook: escalation-rules" in text
    assert "## Playbook: scheduling-policy" not in text


def test_skills_not_enabled_for_practice_are_skipped() -> None:
    state = _state()
    state.practice.skills = ["scheduling-policy"]
    text = build_instructions("ROLE", state, ["escalation-rules", "scheduling-policy"])
    assert "## Playbook: escalation-rules" not in text
    assert "## Playbook: scheduling-policy" in text


def test_closed_days_are_listed() -> None:
    text = build_instructions("ROLE", _state("dermatology-demo"), [])
    assert "Saturday: closed" in text
