# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Project scaffold: uv, ruff, pyright, pytest, Makefile, CI, ADRs 0001–0003.
- Practice templates (pediatrics, dermatology) with validated schema and env-based settings.
- FHIR-shaped mock EHR with deterministic seed data and fault injection (latency, timeouts, outages, stale providers, no slots).
- Runtime Agent Skills loader (agentskills.io spec validation) and the escalation-rules and scheduling-policy playbooks with evals.
- Call state, structured handoff summary, EHR resilience wrapper (timeouts, failure counting, escalation hint) and speakable formatting.
- Scheduling agent (find, book, list, reschedule, cancel) with VerifyIdentity task, confirmation guard and escalation on repeated EHR failures.
- Instruction builder (voice rules, practice facts, playbooks) and LLM-independent scheduling operations with confirmation and ownership guards.
- Human Handoff agent publishing a structured summary (room data topic "handoff") and the LiveKit eval harness.
- Front Desk agent: red-flag triage, practice info, routing to Scheduling or staff; runtime-skill A/B eval.
- Simulated-caller scenarios (anxious parent, rambler, emergency, bad connection, interrupter) and an on-demand Evals workflow.
- AgentServer entrypoint with LiveKit Inference STT/LLM/TTS, turn detector, noise cancellation and per-room practice selection via job metadata.
- Dev Agent Skills (livekit-dev, run-evals, release, add-practice) with trigger eval queries; LiveKit official skills installed via lk skills install.
- README with demo script, architecture diagram and known limitations.
