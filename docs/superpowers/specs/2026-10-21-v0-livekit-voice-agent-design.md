# v0 — LiveKit Voice Front-Desk Agent: Design

- **Status:** Approved (brainstorming), pending written-spec review
- **Date:** 2026-10-21
- **Target release:** `v0.1.0`

## 1. Purpose

A portfolio project demonstrating "AI employee" engineering for physician-practice
patient communication, aligned with the OhMD AI Agent Engineer role. v0 proves
hands-on fluency with **LiveKit Agents**: multi-agent conversation design, tool
use with failure handling, escalation to humans with full context, per-practice
configuration as reusable templates, and systematic evals.

### In scope (v0.1.0)

- Voice channel only, via LiveKit Agents (Python).
- Three agents: **Front Desk**, **Scheduling**, **Human Handoff**, plus a
  reusable **VerifyIdentity** task.
- Mock, FHIR-shaped EHR with fault injection.
- Two practice configs: pediatrics and dermatology.
- Runtime Agent Skills (agentskills.io spec) loaded at handoff.
- Dev Agent Skills for working in the repo.
- Unit tests, LiveKit behavioral evals, simulated-caller runs.
- Changelog, SemVer, CI.

### Out of scope (later versions)

- WhatsApp/chat channel.
- Refills, billing, test results (agent declines honestly and offers a human).
- Real telephony (SIP inbound, warm transfer), real EHR integrations, real PHI.
- Production deployment hardening (v0 may optionally `lk agent create` to Cloud).

## 2. Key decisions

| Decision | Choice | ADR |
|---|---|---|
| Infra & models | LiveKit Cloud + LiveKit Inference (STT/LLM/TTS by model string, one credential set) | 0001 |
| Agent architecture | Multi-agent handoff + `AgentTask` for identity; config-driven per practice | 0002 |
| Runtime skills | Loaded in agent `on_enter` at handoff, not via mid-turn tool calls (latency) | 0003 |
| Language & tooling | Python 3.13, `uv`, `ruff`, `pyright`, `pytest` + `pytest-asyncio` | — |
| Versioning | SemVer from `0.1.0`; Keep a Changelog; Conventional Commits; tags `vX.Y.Z` | — |

Model choices (STT, LLM, TTS, judge LLM) live in config so swapping to direct
provider plugins later is a config change.

## 3. Repository layout

```
medical-secretary/
├── src/medical_secretary/
│   ├── main.py                 # AgentServer entrypoint: Inference STT/LLM/TTS, VAD, turn detector
│   ├── config.py               # pydantic-settings env + practice YAML loader/validation
│   ├── session_state.py        # CallState (session userdata)
│   ├── prompts.py              # shared base instructions (voice style, safety rules)
│   ├── agents/
│   │   ├── front_desk.py
│   │   ├── scheduling.py
│   │   └── human_handoff.py
│   ├── tasks/verify_identity.py
│   ├── tools/resilience.py     # timeout + error→spoken-fallback wrapper, failure counting
│   ├── ehr/
│   │   ├── models.py           # FHIR-shaped Patient, Practitioner, Slot, Appointment
│   │   ├── base.py             # EHRClient Protocol
│   │   └── mock.py             # seeded in-memory MockEHR with fault injection
│   └── skills_runtime/loader.py # parse/validate SKILL.md, render into instructions
├── practices/
│   ├── pediatrics-burlington.yaml
│   └── dermatology-demo.yaml
├── skills/                     # runtime skills (agentskills spec)
│   ├── escalation-rules/       # SKILL.md, references/, evals/
│   └── scheduling-policy/
├── .claude/skills/             # dev skills (agentskills spec)
│   ├── livekit-dev/            # lk CLI workflows (console, dev, simulate, deploy)
│   ├── run-evals/
│   ├── release/                # bump version, roll CHANGELOG, tag
│   └── add-practice/           # scaffold a new practice YAML + checks
├── tests/
│   ├── unit/
│   └── evals/
├── evals/reports/              # simulation run outputs (gitignored except summaries)
├── docs/
│   ├── adr/
│   └── superpowers/specs/
├── CHANGELOG.md  README.md  CONTEXT.md  CLAUDE.md  LICENSE
├── pyproject.toml  uv.lock  Makefile  .env.example  .gitignore
└── .github/workflows/ci.yml
```

LiveKit's official skills are added via `lk skills install` alongside our own
dev skills.

## 4. Components

### 4.1 Config (`config.py`, `practices/*.yaml`)

Environment (`.env.local`, written by `lk app env` / `lk cloud auth`):
`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `PRACTICE_ID`, model
overrides.

Practice YAML (validated by pydantic), minimum fields:

- `id`, `name`, `timezone`, `phone`, `address`, `hours` (per weekday)
- `greeting`, `tone` (short style note)
- `providers` (id, name, specialty, accepts_new_patients)
- `visit_types` (code, label, duration_min, new_patient_allowed)
- `booking_window_days`
- `escalation`: routing rules mapping reason → team, plus urgent contact label
- `skills`: list of runtime skill names to load
- `out_of_scope_message`

The practice is selected per session from job/room metadata, falling back to
`PRACTICE_ID`.

### 4.2 Session state (`CallState`)

Dataclass used as `AgentSession` userdata: `practice`, `ehr`, `caller`
(`VerifiedCaller | None`), `intent`, `actions_taken: list[str]`,
`tool_failures: int`, `handoff: HandoffSummary | None`.

### 4.3 Shared instructions (`prompts.py`)

Spoken style: short sentences, one question at a time, no markdown or lists,
speakable dates and numbers. Safety: no medical advice, no clinical promises,
minimal PHI echo (confirm, don't recite). If uncertain about what was heard,
read it back and confirm. Practice facts only from config — never invent.

### 4.4 Front Desk agent

- `on_enter`: speak practice greeting; load runtime skills listed for the practice
  that apply (`escalation-rules`).
- Red-flag triage first: emergency → tell caller to hang up and dial 911, no
  further workflow. Distressed but non-emergent → handoff with `priority=urgent`.
- Tools:
  - `route_to_scheduling(reason)` → returns `SchedulingAgent` with `chat_ctx`
    carried over (`copy(exclude_instructions=True)`).
  - `route_to_human(reason, priority)` → returns `HumanHandoffAgent`.
  - `get_practice_info(topic)` → hours/address/phone from config only.
- Out-of-scope intents (refills, billing, results): state honestly, use
  `out_of_scope_message`, offer human.

### 4.5 VerifyIdentity task

`AgentTask` returning `VerifiedCaller(patient_id, name, dob)`. Collects full
name and date of birth, calls `ehr.lookup_patient`. Confirms DOB by read-back.
After 2 failed matches, completes with a failure result; the caller agent then
escalates.

### 4.6 Scheduling agent

- `on_enter`: load `scheduling-policy` skill; run `VerifyIdentity` if
  `caller` is unset.
- Tools: `find_slots(visit_type, provider_id?, start_date, end_date)`,
  `book_appointment(slot_id, visit_type)`, `list_appointments()`,
  `reschedule_appointment(appointment_id, new_slot_id)`,
  `cancel_appointment(appointment_id, reason)`, `route_to_human(reason, priority)`.
- Must read back details and get explicit yes before book/reschedule/cancel.
- Unknown/stale provider → say unavailable, offer listed alternatives; never
  fabricate providers or slots.
- No slots in window → offer alternatives (other provider, wider range) or
  handoff.

### 4.7 Human Handoff agent

- Builds `HandoffSummary`: caller (name, verified flag), intent,
  `actions_taken`, escalation reason, priority, suggested team (from practice
  routing rules), short free-text summary.
- Tells caller what happens next.
- v0 transfer is simulated: summary logged as structured JSON and published as a
  room data message (topic `handoff`). Real SIP transfer is roadmap.

### 4.8 Tool resilience (`tools/resilience.py`)

Decorator/wrapper for every EHR-backed tool:

- Timeout per call (default 2.5 s, configurable).
- On timeout/exception: increment `tool_failures`, log, return a short
  structured error string for the model (e.g. `"ERROR: lookup_unavailable"`)
  rather than raising.
- At `tool_failures >= 2`: the error string instructs escalation; agent routes
  to human.
- Slow tools: agent says a short filler ("one moment while I check") before
  awaiting.

### 4.9 EHR (`ehr/`)

`EHRClient` Protocol: `lookup_patient`, `list_practitioners`, `find_slots`,
`book`, `list_appointments`, `reschedule`, `cancel`. Pydantic models shaped after
FHIR R4 resources (subset of fields). `MockEHR`: deterministic seed data per
practice; fault injection flags: `latency_ms`, `fail_next(op)`,
`timeout(op)`, `stale_practitioners` (config lists a provider the EHR doesn't
have), `no_slots`.

### 4.10 Runtime skills (`skills/`, `skills_runtime/loader.py`)

Each skill follows the agentskills.io spec: directory with `SKILL.md`
(frontmatter `name`, `description`, optional fields) and optional
`references/`, `scripts/`, `assets/`, plus our `evals/`. The loader validates
frontmatter (name matches directory, required fields, length limits), and
renders the body into the agent's instructions on `on_enter`. No mid-turn skill
loading in v0 (ADR 0003).

v0 skills: `escalation-rules` (red flags, distress cues, routing), and
`scheduling-policy` (visit-type rules, booking window, new vs existing patient,
confirmation protocol). Practice YAML may override parameters the skill
references.

### 4.11 Dev skills (`.claude/skills/`)

Written per agentskills best practices (focused scope, trigger-optimized
descriptions, scripts for deterministic steps):

- `livekit-dev`: `lk agent console|dev|simulate|create|deploy`, auth, env setup,
  troubleshooting.
- `run-evals`: run unit/eval tiers, interpret failures, add regression case.
- `release`: bump `pyproject.toml` version, roll `[Unreleased]` in CHANGELOG to
  the new version, commit, tag.
- `add-practice`: scaffold and validate a new practice YAML.

## 5. Data flow

```
Caller ─▶ FrontDesk ──red flag──▶ "dial 911" (end workflow)
             │ ├─distress / asks for human / out-of-scope+wants human─▶ HumanHandoff
             │ └─scheduling intent─▶ Scheduling
             │                          ├─ VerifyIdentity (task) ──fail x2──▶ HumanHandoff
             │                          ├─ EHR tools (resilient) ──fail x2──▶ HumanHandoff
             │                          └─ confirm ▶ book/reschedule/cancel ▶ wrap-up
HumanHandoff ─▶ HandoffSummary (log + room data msg) ─▶ "connecting you"
```

## 6. Error handling summary

| Failure | Behavior |
|---|---|
| EHR timeout/error | Spoken graceful message; retry once if sensible; 2 failures → handoff |
| Patient not found | Re-collect once; 2 misses → handoff |
| Stale provider | State unavailable, offer real alternatives |
| No slots | Offer alternatives or handoff |
| ASR uncertainty | Read back and confirm |
| Emergency language | 911 instruction, stop workflow |
| Out-of-scope request | Honest decline + offer human |

## 7. Testing & evals

1. **Unit** (`tests/unit/`, no LLM, every push): practice YAML schema; MockEHR
   determinism and fault flags; skill loader validation; resilience wrapper
   (timeout → error string, failure counting).
2. **Behavioral evals** (`tests/evals/`, LiveKit `AgentSession.run` +
   `result.expect` + `.judge()`, `mock_tools` for faults, `JudgeGroup` for
   full-conversation quality). Parametrized over both practices. Categories:
   routing, safety, scheduling happy path, messy data, ASR robustness, handoff
   quality. Run on demand / PR label.
3. **Simulated callers** (`lk agent simulate text`): personas — anxious parent,
   elderly rambler, bad connection, interrupter. Pre-release; outputs to
   `evals/reports/`, summary in release notes.

Runtime skill evals per agentskills "evaluating skills": each skill's `evals/`
holds trigger/non-trigger prompts and expected behavior, run with vs without
the skill.

Regression rule: every observed failure becomes an eval case before the fix.

## 8. CI

GitHub Actions:

- On push/PR: `uv sync`, `ruff check`, `ruff format --check`, `pyright`, unit
  tests.
- Evals: `workflow_dispatch` or `run-evals` PR label, using LiveKit secrets.
  Required for release, advisory for merges in v0.

## 9. Conventions

- SemVer starting `0.1.0`; while `0.x`, minor = features, patch = fixes.
- `CHANGELOG.md` in Keep a Changelog format with `[Unreleased]`.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`).
- Tags `vX.Y.Z`; the `release` dev skill automates the bump.
- ADRs in `docs/adr/NNNN-title.md` (context, decision, consequences).

## 10. Done criteria for v0.1.0

- `lk agent console` completes the scheduling happy path and one escalation, by
  voice, for both practices.
- Unit tests and evals green.
- `CHANGELOG.md` has a `0.1.0` section; tag `v0.1.0` created.
- README contains demo script, architecture diagram, and dev setup using `lk`.

## 11. Roadmap (not v0.1.0)

- `0.2.0`: Refill Request agent.
- `0.3.0`: SIP inbound + real warm transfer.
- `0.4.0`: WhatsApp chat channel sharing agents/skills.
- Later: FHIR sandbox integration, call analytics (SQL over transcripts), MCP
  server exposing EHR tools.
