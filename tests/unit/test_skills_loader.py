from pathlib import Path

import pytest

from medical_secretary.skills_runtime.loader import (
    SKILLS_DIR,
    SkillError,
    load_skills,
    parse_skill,
    render_skills,
)


def _make(
    tmp_path: Path, dirname: str, frontmatter: str, body: str = "Do the thing."
) -> Path:
    skill_dir = tmp_path / dirname
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n{body}\n")
    return skill_dir


def test_parse_valid_skill(tmp_path: Path) -> None:
    d = _make(tmp_path, "my-skill", "name: my-skill\ndescription: Use when testing.")
    skill = parse_skill(d)
    assert skill.name == "my-skill"
    assert skill.description == "Use when testing."
    assert skill.body == "Do the thing."


@pytest.mark.parametrize(
    "name",
    ["My-Skill", "-skill", "skill-", "my--skill", "a" * 65, "my_skill"],
)
def test_invalid_names_rejected(tmp_path: Path, name: str) -> None:
    d = _make(tmp_path, "dir", f"name: '{name}'\ndescription: x")
    with pytest.raises(SkillError):
        parse_skill(d)


def test_name_must_match_directory(tmp_path: Path) -> None:
    d = _make(tmp_path, "other", "name: my-skill\ndescription: x")
    with pytest.raises(SkillError, match="directory"):
        parse_skill(d)


def test_description_required_and_bounded(tmp_path: Path) -> None:
    d = _make(tmp_path, "a-skill", "name: a-skill")
    with pytest.raises(SkillError, match="description"):
        parse_skill(d)
    d2 = _make(tmp_path, "b-skill", f"name: b-skill\ndescription: '{'x' * 1025}'")
    with pytest.raises(SkillError, match="description"):
        parse_skill(d2)


def test_missing_frontmatter_rejected(tmp_path: Path) -> None:
    d = tmp_path / "c-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("no frontmatter here")
    with pytest.raises(SkillError, match="frontmatter"):
        parse_skill(d)


def test_metadata_must_be_string_map(tmp_path: Path) -> None:
    d = _make(
        tmp_path, "d-skill", "name: d-skill\ndescription: x\nmetadata:\n  version: 1"
    )
    with pytest.raises(SkillError, match="metadata"):
        parse_skill(d)


def test_render_skills() -> None:
    assert render_skills([]) == ""
    skills = load_skills(["escalation-rules"])
    rendered = render_skills(skills)
    assert rendered.startswith("## Playbook: escalation-rules")
    assert "911" in rendered


@pytest.mark.parametrize("name", ["escalation-rules", "scheduling-policy"])
def test_bundled_runtime_skills_are_valid(name: str) -> None:
    skill = parse_skill(SKILLS_DIR / name)
    assert skill.name == name
    assert (SKILLS_DIR / name / "evals" / "evals.json").is_file()


def test_unknown_skill_raises() -> None:
    with pytest.raises(SkillError, match="not found"):
        load_skills(["nope-skill"])
