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


@asynccontextmanager
async def start_session(
    agent: Agent, state: CallState
) -> AsyncIterator[AgentSession[CallState]]:
    async with (
        inference.LLM(model=state.settings.llm_model) as agent_llm,
        AgentSession[CallState](llm=agent_llm, userdata=state) as session,
    ):
        await session.start(agent)
        # let an on_enter AgentTask take over the activity before the first run()
        await asyncio.sleep(1)
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
