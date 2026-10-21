# 0002. Multi-agent handoff with a VerifyIdentity task

- Status: Accepted
- Date: 2026-10-21

## Context
One large prompt covering triage, scheduling and escalation increases latency and tool misuse. OhMD's product hinges on clean escalation with context.

## Decision
Separate `FrontDeskAgent`, `SchedulingAgent`, `HumanHandoffAgent`. Handoffs happen when a `@function_tool` returns a new `Agent`; conversation history is carried with `chat_ctx.copy(exclude_instructions=True)`. Identity verification is an `AgentTask[IdentityResult]` awaited in `SchedulingAgent.on_enter`. Session state is `CallState` userdata. Tool logic lives in pure functions (`scheduling_ops.py`).

## Consequences
Small focused prompts and tool sets; handoffs are assertable in tests (`contains_agent_handoff`). More wiring; returning to a previous agent is manual (not needed in v0).
