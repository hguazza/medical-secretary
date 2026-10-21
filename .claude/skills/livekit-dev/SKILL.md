---
name: livekit-dev
description: Use when running, debugging, talking to, simulating or deploying this repo's voice agent with the LiveKit CLI (lk), including "try the agent", "why did it say that", "test it by voice", "deploy to cloud", or setting up LiveKit credentials. Covers lk agent console, debugger, dev, simulate, create/deploy and lk app env.
metadata:
  owner: medical-secretary
---

The agent entrypoint is `src/agent.py`, which loads `medical_secretary.server`. The practice comes from `PRACTICE_ID` or from the job metadata `{"practice_id": "..."}`.

## Setup (once)
- `lk cloud auth` (the user runs it, because it opens a browser), then `lk app env -w` to write `.env.local`.
- `uv run python src/agent.py download-files` to fetch the turn detector and noise cancellation models.

## Talk to it
- By text, quickly: `make console-text`. By voice: `make console`. To change practice: `PRACTICE_ID=dermatology-demo make console-text`.
- Turn by turn, with tool calls visible: `lk agent debugger start`, then `lk agent debugger say "..." --logs`. After every code edit run `lk agent debugger restart`, because a running session keeps the old code. Finish with `lk agent debugger stop`.

## Diagnose
- Run `lk agent dev --log-level DEBUG` and use the Agent Console in LiveKit Cloud for turn-taking, interruptions and speech-recognition problems, which text mode can't show.
- Check whether the failure is in the prompt, the tool description, the tool logic (`scheduling_ops.py`, unit-testable) or the EHR data, before changing anything.
- Every real failure becomes an eval in `tests/evals/` or a scenario in `scenarios.yaml` before the fix (see the run-evals skill).

## Simulate and deploy
- `make simulate` runs `scenarios.yaml` on LiveKit Cloud, which costs inference. Use `lk agent simulate list` and `lk agent simulate view` to inspect runs.
- The first deploy is `lk agent create`; later ones are `lk agent deploy`. Stream logs with `lk agent logs`.
- For API questions, use `lk docs` rather than guessing.
