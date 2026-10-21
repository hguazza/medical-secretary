# AGENTS.md

LiveKit Agents (Python) voice front desk. Read `CONTEXT.md` for domain terms and
`docs/superpowers/specs/` for the design.

## Commands

- `make install` · `make check` (ruff + pyright + unit tests) · `make evals` (LLM, costs money)
- `make console-text` / `make console` — talk to the agent locally via `lk agent console`
- `lk agent debugger start` / `say "..."` / `restart` / `stop` — turn-by-turn debugging
- `make simulate` — `lk agent simulate text --scenarios scenarios.yaml` on LiveKit Cloud
- `lk docs` — search current LiveKit docs before guessing at an API

## Conventions

- Conventional Commits; SemVer; update `CHANGELOG.md` `[Unreleased]` with every behavior change.
- Release only through the `release` skill (`.claude/skills/release`).
- Unit tests never hit an LLM or network; LLM tests are marked `evals`.
- Every observed agent failure becomes an eval or scenario before it is fixed.
- Agent behavior changes: write the eval/scenario first, then change prompts/tools.
- Architecture decisions go in `docs/adr/NNNN-title.md`.
