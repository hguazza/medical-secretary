import json
from pathlib import Path

import pytest

from medical_secretary.skills_runtime.loader import parse_skill

DEV_SKILLS = Path(__file__).resolve().parents[2] / ".claude" / "skills"


@pytest.mark.parametrize(
    "name", ["livekit-dev", "run-evals", "release", "add-practice"]
)
def test_dev_skill_valid_with_trigger_queries(name: str) -> None:
    skill = parse_skill(DEV_SKILLS / name)
    assert skill.description.lower().startswith("use ")
    queries = json.loads(
        (DEV_SKILLS / name / "evals" / "trigger_queries.json").read_text()
    )
    assert sum(q["should_trigger"] for q in queries) >= 4
    assert sum(not q["should_trigger"] for q in queries) >= 4
