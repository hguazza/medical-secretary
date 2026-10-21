"""LiveKit AgentServer: builds the voice pipeline and starts the Front Desk."""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    STTContextOptions,
    TurnHandlingOptions,
    inference,
    room_io,
)
from livekit.plugins import ai_coustics

from medical_secretary.agents.front_desk import FrontDeskAgent
from medical_secretary.config import Practice, Settings, load_practice
from medical_secretary.session_state import CallState, new_call_state

load_dotenv(".env.local")
logger = logging.getLogger("medical_secretary")


def resolve_practice_id(metadata: str | None, default: str) -> str:
    if not metadata:
        return default
    try:
        data = json.loads(metadata)
    except json.JSONDecodeError:
        return default
    if isinstance(data, dict) and isinstance(data.get("practice_id"), str):
        return data["practice_id"]
    return default


def practice_today(practice: Practice, now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(ZoneInfo(practice.timezone)).date()


server = AgentServer()


@server.rtc_session(agent_name="medical-secretary")
async def entrypoint(ctx: JobContext) -> None:
    settings = Settings()
    practice = load_practice(
        resolve_practice_id(ctx.job.metadata, settings.practice_id)
    )
    state = new_call_state(practice, settings, practice_today(practice))
    ctx.log_context_fields = {"room": ctx.room.name, "practice": practice.id}

    session = AgentSession[CallState](
        stt=inference.STT(model=settings.stt_model, language="en"),
        stt_context_options=STTContextOptions(
            keyterms=[practice.name, *(p.name for p in practice.providers)],
            keyterm_detection={"enabled": True},
        ),
        llm=inference.LLM(model=settings.llm_model),
        tts=inference.TTS(model=settings.tts_model, voice=settings.tts_voice),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            preemptive_generation={"enabled": True},
        ),
        userdata=state,
    )

    await session.start(
        agent=FrontDeskAgent(state),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            ),
        ),
    )
    await ctx.connect()
    session.generate_reply(
        instructions=f'Greet the caller by saying: "{practice.greeting}"'
    )
