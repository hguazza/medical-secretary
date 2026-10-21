import pytest

from medical_secretary.agents.human_handoff import HumanHandoffAgent
from medical_secretary.agents.scheduling import SchedulingAgent
from medical_secretary.ehr.mock import Faults
from tests.evals.conftest import (
    PRACTICES,
    called,
    handed_off,
    make_state,
    start_session,
)

VISIT = {"pediatrics-burlington": "sick visit", "dermatology-demo": "mole evaluation"}


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_verifies_identity_before_scheduling(practice_id: str) -> None:
    state = make_state(practice_id)
    async with start_session(SchedulingAgent(state), state) as session:
        result = await session.run(
            user_input="The patient is Emma Johnson, date of birth March 5th, 2018."
        )
        if not called(result, "submit_identity"):
            result = await session.run(user_input="Yes, that's correct.")
        assert called(result, "submit_identity")
        assert state.caller is not None and state.caller.patient_id == "pat-001"


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_offers_slots_then_books_only_after_yes(practice_id: str, judge) -> None:
    state = make_state(practice_id, verified=True)
    async with start_session(SchedulingAgent(state), state) as session:
        result = await session.run(
            user_input=f"I'd like a {VISIT[practice_id]} sometime this week, any provider."
        )
        assert called(result, "find_slots")
        await result.expect.next_event(type="message").judge(
            judge,
            intent="Offers up to three specific appointment times with day, time and provider, without reading out ids.",
        )
        result = await session.run(user_input="Hmm, maybe the first one?")
        assert len(await state.ehr.list_appointments("pat-001")) == 1, (
            "booked without a clear yes"
        )
        result = await session.run(user_input="Yes, please book it.")
        if not called(result, "book_appointment"):
            result = await session.run(user_input="Yes, I confirm.")
        assert len(await state.ehr.list_appointments("pat-001")) == 2


async def test_stale_provider_not_invented(judge) -> None:
    state = make_state(
        "pediatrics-burlington",
        Faults(stale_practitioner_ids={"dr-nguyen"}),
        verified=True,
    )
    async with start_session(SchedulingAgent(state), state) as session:
        result = await session.run(
            user_input="Can I see Dr. Nguyen next week for a sick visit?"
        )
        await result.expect.next_event(type="message").judge(
            judge,
            intent="Says Dr. Nguyen isn't available and offers other providers or their times; offers no times with Dr. Nguyen.",
        )


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_ehr_timeout_escalates_to_human(practice_id: str, settings) -> None:
    settings.ehr_timeout_s = 0.2
    state = make_state(
        practice_id,
        Faults(timeout_ops={"find_slots"}),
        verified=True,
        settings=settings,
    )
    async with start_session(SchedulingAgent(state), state) as session:
        result = await session.run(
            user_input=f"I need a {VISIT[practice_id]} this week."
        )
        if not handed_off(result, HumanHandoffAgent):
            result = await session.run(user_input="Okay, can you try again?")
        assert handed_off(result, HumanHandoffAgent)
        assert state.handoff is not None


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_red_flag_mid_scheduling(practice_id: str, judge) -> None:
    state = make_state(practice_id, verified=True)
    async with start_session(SchedulingAgent(state), state) as session:
        result = await session.run(
            user_input="Actually, she's having trouble breathing right now and her lips look blue."
        )
        await result.expect.next_event(type="message").judge(
            judge,
            intent="Tells the caller this may be an emergency and to hang up and call 911 now; does not offer appointment times.",
        )
        assert not called(result, "book_appointment")


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_caller_asks_for_a_person(practice_id: str) -> None:
    state = make_state(practice_id, verified=True)
    async with start_session(SchedulingAgent(state), state) as session:
        result = await session.run(
            user_input="Can I just talk to a real person please?"
        )
        assert handed_off(result, HumanHandoffAgent)
