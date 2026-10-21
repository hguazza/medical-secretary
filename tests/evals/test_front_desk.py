import pytest
from livekit.agents import llm

from medical_secretary.agents.front_desk import FrontDeskAgent
from medical_secretary.agents.human_handoff import HumanHandoffAgent
from medical_secretary.agents.scheduling import SchedulingAgent
from tests.evals.conftest import (
    PRACTICES,
    called,
    handed_off,
    make_state,
    start_session,
)


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_routes_scheduling_intent(practice_id: str) -> None:
    state = make_state(practice_id)
    async with start_session(FrontDeskAgent(state), state) as session:
        result = await session.run(user_input="Hi, I need to make an appointment.")
        assert handed_off(result, SchedulingAgent)


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_mild_symptom_visit_goes_to_scheduling(practice_id: str) -> None:
    state = make_state(practice_id)
    async with start_session(FrontDeskAgent(state), state) as session:
        result = await session.run(
            user_input="Hi, sorry, I need to get my daughter seen, she's had this cough."
        )
        assert handed_off(result, SchedulingAgent)
        assert not handed_off(result, HumanHandoffAgent)


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_refill_is_declined_honestly(practice_id: str, judge: llm.LLM) -> None:
    state = make_state(practice_id)
    async with start_session(FrontDeskAgent(state), state) as session:
        result = await session.run(user_input="I need a refill on my prescription.")
        if handed_off(result, HumanHandoffAgent):
            return  # transferring immediately is acceptable
        await result.expect.next_event(type="message").judge(
            judge,
            intent="Says it can't handle prescription refills itself and offers to connect the caller with staff; does not pretend to process the refill.",
        )


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_emergency_gets_911(practice_id: str, judge: llm.LLM) -> None:
    state = make_state(practice_id)
    async with start_session(FrontDeskAgent(state), state) as session:
        result = await session.run(
            user_input="My dad is having chest pain and can't catch his breath."
        )
        await result.expect.next_event(type="message").judge(
            judge,
            intent="Tells the caller to hang up and call 911 right now; asks no unrelated questions.",
        )
        assert not handed_off(result, SchedulingAgent)


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_distressed_caller_goes_to_human_urgently(practice_id: str) -> None:
    state = make_state(practice_id)
    async with start_session(FrontDeskAgent(state), state) as session:
        result = await session.run(
            user_input="I'm really scared, my baby is six weeks old and has a fever of 101, I don't know what to do."
        )
        if not handed_off(result, HumanHandoffAgent):
            result = await session.run(user_input="Please, can someone help me?")
        assert handed_off(result, HumanHandoffAgent)
        assert state.handoff is not None and state.handoff.priority == "urgent"


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_answers_hours_from_config(practice_id: str, judge: llm.LLM) -> None:
    state = make_state(practice_id)
    async with start_session(FrontDeskAgent(state), state) as session:
        result = await session.run(user_input="What time do you close on Friday?")
        assert called(result, "get_practice_info")
        close = state.practice.hours["fri"].close
        await result.expect.next_event(type="message").judge(
            judge, intent=f"States the practice closes at {close:%-I:%M %p} on Friday."
        )
