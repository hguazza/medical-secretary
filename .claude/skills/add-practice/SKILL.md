---
name: add-practice
description: Use when onboarding a new practice or changing one, such as hours, providers, visit types, booking window, escalation routing, greeting or enabled playbooks, including "set up a new clinic", "Dr. X left" or "they're closed Fridays now". Creates or edits practices/<id>.yaml and validates it.
metadata:
  owner: medical-secretary
---

Each practice is a single YAML template in `practices/`, and the code never changes per practice. A workflow that's needed a second time should become a playbook in `skills/`, not more YAML.

1. Copy the closest existing file: `cp practices/pediatrics-burlington.yaml practices/<new-id>.yaml`. The `id` must match the file name, in lowercase with hyphens.
2. Fill in every field. Put times in quotes (`"08:00"`), because YAML otherwise misreads them. Leave a closed day out of `hours`. Provider ids look like `dr-lastname`. Visit type codes are short slugs.
3. Map each escalation `reason` (clinical, billing, records, scheduling) to the team that handles it at this practice, and set `default_team`.
4. Validate it: `uv run python -c "from medical_secretary.config import load_practice; print(load_practice('<new-id>').name)"`.
5. Add `<new-id>` to `PRACTICES` in `tests/evals/conftest.py` if it should be covered by evals, then run `make evals`.
6. Try it: `PRACTICE_ID=<new-id> make console-text`.
7. Add a line under `[Unreleased]` in the changelog, then commit with `feat(practice): add <new-id>`.

If a provider has left, remove them from `providers`. Don't keep stale entries; the agent must never offer someone who no longer works there.
