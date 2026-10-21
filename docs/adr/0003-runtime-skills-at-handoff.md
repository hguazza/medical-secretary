# 0003. Load runtime skills at handoff, not mid-turn

- Status: Accepted
- Date: 2026-10-21

## Context
Agent Skills enable progressive disclosure, but a `load_skill` tool call inside a voice turn adds an LLM round trip (hundreds of ms) while the caller waits.

## Decision
Each agent declares the runtime skills it uses; when the agent is constructed (at handoff), the skills enabled for the practice are rendered into its instructions. No mid-turn skill tool in v0.

## Consequences
Zero added turn latency; prompts grow by the size of the loaded skills (kept < 5000 tokens each per spec). Revisit with a tool-based loader if skill count grows.
