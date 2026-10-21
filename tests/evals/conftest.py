"""Shared fixtures for LLM-backed evals. Run with `make evals`."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date

import pytest
from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, inference, llm
from livekit.agents.voice.run_result import RunResult

from medical_secretary.config import Settings, load_practice
from medical_secretary.ehr.mock import Faults
from medical_secretary.session_state import CallState, VerifiedCaller, new_call_state

load_dotenv(".env.local")

EVAL_TODAY = date(2026, 11, 2)  # Monday; pins relative dates so evals stay stable
PRACTICES = ["pediatrics-burlington", "dermatology-demo"]


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    skip = pytest.mark.skip(
        reason="LIVEKIT_API_KEY not set; evals need LiveKit Inference"
    )
    for item in items:
        if "tests/evals/" in str(item.fspath).replace(os.sep, "/"):
            item.add_marker(pytest.mark.evals)
            if not os.getenv("LIVEKIT_API_KEY"):
                item.add_marker(skip)


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
async def judge(settings: Settings) -> AsyncIterator[llm.LLM]:
    async with inference.LLM(model=settings.judge_model) as judge_llm:
        yield judge_llm


def make_state(
    practice_id: str,
    faults: Faults | None = None,
    verified: bool = False,
    settings: Settings | None = None,
) -> CallState:
    state = new_call_state(
        load_practice(practice_id), settings or Settings(), EVAL_TODAY, faults
    )
    if verified:
        state.caller = VerifiedCaller("pat-001", "Emma Johnson", date(2018, 3, 5))
    return state


async def wait_for_on_enter(
    session: AgentSession[CallState], timeout_s: float = 30.0
) -> None:
    """Wait until the agent's on_enter speech (and any AgentTask it started) is done.

    Speech is created asynchronously after start(), so require the session to
    stay free of pending speech for a short settle period before the first run().
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    idle_since: float | None = None
    await asyncio.sleep(0.5)
    while loop.time() < deadline:
        speech = session.current_speech
        if speech is not None and not speech.done():
            idle_since = None
            await asyncio.wait_for(
                speech.wait_for_playout(), max(deadline - loop.time(), 0.1)
            )
            continue
        now = loop.time()
        idle_since = now if idle_since is None else idle_since
        if now - idle_since >= 0.5:
            return
        await asyncio.sleep(0.1)


@asynccontextmanager
async def start_session(
    agent: Agent, state: CallState
) -> AsyncIterator[AgentSession[CallState]]:
    async with (
        inference.LLM(model=state.settings.llm_model) as agent_llm,
        AgentSession[CallState](llm=agent_llm, userdata=state) as session,
    ):
        await session.start(agent)
        # let on_enter speech / an on_enter AgentTask settle before the first run()
        await wait_for_on_enter(session)
        yield session


def called(result: RunResult, name: str) -> bool:
    try:
        result.expect.contains_function_call(name=name)
    except AssertionError:
        return False
    return True


def handed_off(result: RunResult, agent_type: type[Agent]) -> bool:
    try:
        result.expect.contains_agent_handoff(new_agent_type=agent_type)
    except AssertionError:
        return False
    return True
