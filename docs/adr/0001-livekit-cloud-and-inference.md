# 0001. LiveKit Cloud with LiveKit Inference

- Status: Accepted
- Date: 2026-10-21

## Context
v0 must run voice end to end quickly, with minimal key management, and demonstrate LiveKit-native skills.

## Decision
Use LiveKit Cloud for rooms/agents and LiveKit Inference for STT, LLM and TTS, selected by model string (`inference.STT/LLM/TTS`). Model ids live in `Settings`.

## Consequences
One credential set (`LIVEKIT_*`); `lk agent console/dev/simulate/create` work out of the box. Evals call Inference and therefore need credentials and cost money. Moving to direct provider plugins later is a config + import change.
