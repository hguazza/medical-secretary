#!/usr/bin/env python3
"""Bump the SemVer version in pyproject.toml and roll CHANGELOG.md [Unreleased].

Usage: release.py {major|minor|patch} [--date YYYY-MM-DD] [--dry-run]
Prints the new version. Does not commit or tag; the skill does that.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
UNRELEASED = "## [Unreleased]"


def bump(version: str, part: str) -> str:
    match = SEMVER.match(version)
    if not match:
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {version!r}")
    major, minor, patch = (int(x) for x in match.groups())
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"part must be major, minor or patch, got {part!r}")


def roll_changelog(text: str, version: str, day: str) -> str:
    start = text.find(UNRELEASED)
    if start == -1:
        raise ValueError("CHANGELOG.md has no '## [Unreleased]' section")
    body_start = start + len(UNRELEASED)
    next_section = text.find("\n## [", body_start)
    body_end = len(text) if next_section == -1 else next_section
    body = text[body_start:body_end].strip()
    if not body:
        raise ValueError("[Unreleased] is empty; nothing to release")
    rolled = f"{UNRELEASED}\n\n## [{version}] - {day}\n\n{body}\n"
    rest = text[body_end:].lstrip("\n")
    return text[:start] + rolled + ("\n" + rest if rest else "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("part", choices=["major", "minor", "patch"])
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    pyproject = ROOT / "pyproject.toml"
    changelog = ROOT / "CHANGELOG.md"
    py_text = pyproject.read_text()
    match = VERSION_LINE.search(py_text)
    if not match:
        print("error: no version line in pyproject.toml", file=sys.stderr)
        return 1
    try:
        new_version = bump(match.group(1), args.part)
        new_changelog = roll_changelog(changelog.read_text(), new_version, args.date)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not args.dry_run:
        pyproject.write_text(
            VERSION_LINE.sub(f'version = "{new_version}"', py_text, count=1)
        )
        changelog.write_text(new_changelog)
    print(new_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
