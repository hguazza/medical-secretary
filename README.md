# medical-secretary

Voice AI front desk for physician practices, built with [LiveKit Agents](https://docs.livekit.io/agents/).
Status: pre-release (`0.x`). See [CHANGELOG](CHANGELOG.md) and the
[v0 design](docs/superpowers/specs/2026-10-21-v0-livekit-voice-agent-design.md).

## Quick start

    brew install livekit-cli
    lk cloud auth
    lk app env -w            # writes .env.local
    make install
    make console-text        # talk to the agent by typing
