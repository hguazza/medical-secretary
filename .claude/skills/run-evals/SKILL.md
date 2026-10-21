---
name: run-evals
description: Use when testing agent behavior, adding a regression case, interpreting a failing eval, or checking whether a prompt, tool or playbook change made the agent better or worse. Covers unit tests, LiveKit LLM-judged evals, runtime-skill A/B evals and simulated callers, even if the user only says "did that break anything".
metadata:
  owner: medical-secretary
---

There are three tiers, from cheapest to most expensive. Run the cheapest tier that can catch the problem.

1. `make test` runs the unit tests. They use no LLM and no network, and cover config, the mock EHR, the skill loader, resilience and `scheduling_ops`. Run them on every change.
2. `make evals` (`pytest -m evals`) runs LiveKit `AgentSession.run`, `result.expect` and `.judge()` against both practices. It needs `.env.local` and costs inference. To run a subset: `uv run pytest -m evals tests/evals/test_scheduling.py -k stale -v -s`.
3. `make simulate` runs whole conversations from `scenarios.yaml`. Use it before releases.

## Adding a regression case
- Reproduce the failure first, with `lk agent debugger` (see livekit-dev).
- Add the smallest eval that fails for the current code. Put it in the existing `tests/evals/test_<agent>.py`, use `make_state(...)` with `Faults(...)` to inject EHR problems, and pin dates with `EVAL_TODAY`.
- Assert facts with code where you can (`called`, `handed_off`, EHR state). Use `.judge(intent=...)` only for wording and tone, and write the intent as an observable behavior.
- Fix the root cause, then run the whole eval tier again.

## Runtime skills
`tests/evals/test_runtime_skills.py` runs every case in each skill's `evals/evals.json` with and without the skill (escalation-rules against Front Desk, scheduling-policy against Scheduling with a verified caller). Cases must be self-contained single prompts. When you edit a playbook in `skills/`, rerun it. The skill must pass all its cases and must not do worse than the baseline.

## Reading a failure
- A judge failure: print the transcript with `-s` and decide whether the agent was wrong or the intent was too strict. Fix whichever is wrong, and say which in the commit message.
- A flaky case: run it 3 times. If it passes only sometimes, tighten the prompt or tool description rather than loosening the test.
