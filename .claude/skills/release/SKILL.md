---
name: release
description: Use when cutting a release, bumping the version, tagging, or preparing release notes for this repo, including requests like "ship 0.2", "tag a new version" or "update the changelog for release". Handles SemVer bump, CHANGELOG roll and git tag.
metadata:
  owner: medical-secretary
---

Releases follow SemVer and Keep a Changelog. While the version is 0.x, a minor bump means new features and a patch bump means fixes only.

1. Make sure the tree is clean and on `main`: `git status --porcelain` prints nothing.
2. Make sure checks pass: `make check`. For a minor or major release, also run `make evals` and `make simulate`, and paste the simulation pass counts into the release notes.
3. Look at `## [Unreleased]` in `CHANGELOG.md`. If an entry is missing for a merged change, add it now, using the sections Added, Changed, Fixed, Removed and Security.
4. Preview the change: `uv run python .claude/skills/release/scripts/release.py <part> --dry-run`
5. Apply it: `uv run python .claude/skills/release/scripts/release.py <part>`. It prints the new version.
6. `uv lock`, then `git add pyproject.toml uv.lock CHANGELOG.md` and `git commit -m "chore(release): v<version>"`.
7. Tag it: `git tag -a v<version> -m "v<version>"`. Push only when the user asks.

If the script says `[Unreleased] is empty`, stop: there is nothing to release.
