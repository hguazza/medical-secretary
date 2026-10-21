import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "release", ROOT / ".claude/skills/release/scripts/release.py"
)
assert _spec and _spec.loader
release = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(release)

CHANGELOG = """# Changelog

## [Unreleased]

### Added

- Thing one.

## [0.0.1] - 2026-01-01

- Old.
"""


@pytest.mark.parametrize(
    ("version", "part", "expected"),
    [
        ("0.0.0", "minor", "0.1.0"),
        ("0.1.3", "patch", "0.1.4"),
        ("0.9.1", "major", "1.0.0"),
        ("1.2.3", "minor", "1.3.0"),
    ],
)
def test_bump(version: str, part: str, expected: str) -> None:
    assert release.bump(version, part) == expected


def test_bump_rejects_bad_input() -> None:
    with pytest.raises(ValueError):
        release.bump("1.2", "minor")
    with pytest.raises(ValueError):
        release.bump("1.2.3", "huge")


def test_roll_changelog_moves_unreleased() -> None:
    out = release.roll_changelog(CHANGELOG, "0.1.0", "2026-10-21")
    assert (
        "## [Unreleased]\n\n## [0.1.0] - 2026-10-21\n\n### Added\n\n- Thing one." in out
    )
    assert "## [0.0.1] - 2026-01-01" in out


def test_roll_changelog_refuses_empty_unreleased() -> None:
    empty = "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-10-21\n\n- x\n"
    with pytest.raises(ValueError, match="empty"):
        release.roll_changelog(empty, "0.2.0", "2026-11-01")
