import pytest

from medical_secretary.agents.human_handoff import HumanHandoffAgent
from tests.evals.conftest import PRACTICES, make_state, start_session


@pytest.mark.parametrize("practice_id", PRACTICES)
async def test_handoff_records_summary_and_reassures(practice_id: str, judge) -> None:
    state = make_state(practice_id, verified=True)
    state.intent = "scheduling"
    agent = HumanHandoffAgent(
        state,
        reason="clinical",
        priority="urgent",
        summary="Parent worried about a fever of 102 for two days.",
    )
    async with start_session(agent, state) as session:
        result = await session.run(user_input="Okay, thank you.")
        assert state.handoff is not None
        assert state.handoff.team == state.practice.team_for("clinical")
        assert state.handoff.priority == "urgent"
        await result.expect.next_event(type="message").judge(
            judge,
            intent="Briefly reassures the caller that staff will help and have the details; does not ask new questions or give medical advice.",
        )
