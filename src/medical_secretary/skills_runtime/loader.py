"""Load agentskills.io-format skills and render them into agent instructions."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from medical_secretary.config import REPO_ROOT

SKILLS_DIR = REPO_ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SkillError(ValueError):
    pass


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: Path


def _split_frontmatter(text: str, path: Path) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        raise SkillError(f"{path}: missing YAML frontmatter")
    end = text.find("\n---", 4)
    if end == -1:
        raise SkillError(f"{path}: unterminated YAML frontmatter")
    meta = yaml.safe_load(text[4:end]) or {}
    if not isinstance(meta, dict):
        raise SkillError(f"{path}: frontmatter must be a mapping")
    return meta, text[end + 4 :].strip()


def parse_skill(skill_dir: Path) -> Skill:
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        raise SkillError(f"skill '{skill_dir.name}' not found at {path}")
    meta, body = _split_frontmatter(path.read_text(), path)

    name = meta.get("name")
    if (
        not isinstance(name, str)
        or not (1 <= len(name) <= 64)
        or not NAME_RE.match(name)
    ):
        raise SkillError(f"{path}: invalid name {name!r}")
    if name != skill_dir.name:
        raise SkillError(
            f"{path}: name '{name}' must match directory '{skill_dir.name}'"
        )

    description = meta.get("description")
    if not isinstance(description, str) or not (1 <= len(description) <= 1024):
        raise SkillError(f"{path}: description must be 1-1024 characters")

    compatibility = meta.get("compatibility")
    if compatibility is not None and (
        not isinstance(compatibility, str) or not (1 <= len(compatibility) <= 500)
    ):
        raise SkillError(f"{path}: compatibility must be 1-500 characters")

    metadata = meta.get("metadata")
    if metadata is not None and (
        not isinstance(metadata, dict)
        or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()
        )
    ):
        raise SkillError(f"{path}: metadata must map strings to strings")

    return Skill(name=name, description=description, body=body, path=skill_dir)


def load_skills(names: Iterable[str], skills_dir: Path = SKILLS_DIR) -> list[Skill]:
    return [parse_skill(skills_dir / name) for name in names]


def render_skills(skills: Sequence[Skill]) -> str:
    return "\n\n".join(f"## Playbook: {s.name}\n\n{s.body}" for s in skills)
