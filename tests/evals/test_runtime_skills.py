import json
from collections.abc import Callable
from typing import Any

import pytest
from livekit.agents import Agent, llm

from medical_secretary.agents.front_desk import FrontDeskAgent
from medical_secretary.agents.scheduling import SchedulingAgent
from medical_secretary.session_state import CallState
from medical_secretary.skills_runtime.loader import SKILLS_DIR
from tests.evals.conftest import final_message, make_state, start_session

# skill name -> (builds the agent the skill is meant for, whether the caller is verified)
AgentFactory = Callable[[CallState, tuple[str, ...]], Agent]
TARGETS: dict[str, tuple[AgentFactory, bool]] = {
    "escalation-rules": (lambda s, skills: FrontDeskAgent(s, skills=skills), False),
    "scheduling-policy": (
        lambda s, skills: SchedulingAgent(s, skills=skills),
        True,
    ),
}


def _cases(skill: str) -> list[dict[str, Any]]:
    path = SKILLS_DIR / skill / "evals" / "evals.json"
    return json.loads(path.read_text())["evals"]


async def _passes(
    skill: str, case: dict[str, Any], skills: tuple[str, ...], judge: llm.LLM
) -> bool:
    factory, verified = TARGETS[skill]
    state = make_state("pediatrics-burlington", verified=verified)
    async with start_session(factory(state, skills), state) as session:
        result = await session.run(user_input=case["prompt"])
        intent = case["expected_output"] + " " + " ".join(case["assertions"])
        try:
            if verified:
                # tool-using agent: the first message may be a holding phrase
                await final_message(result).judge(judge, intent=intent)
            else:
                await result.expect.contains_message(role="assistant").judge(
                    judge, intent=intent
                )
        except AssertionError:
            return False
        return True


@pytest.mark.parametrize("skill", sorted(TARGETS))
async def test_runtime_skill_beats_baseline(skill: str, judge: llm.LLM) -> None:
    cases = _cases(skill)
    assert len(cases) >= 2
    with_skill = [await _passes(skill, c, (skill,), judge) for c in cases]
    without_skill = [await _passes(skill, c, (), judge) for c in cases]
    print(
        f"{skill} with={sum(with_skill)}/{len(cases)} without={sum(without_skill)}/{len(cases)}"
    )
    assert all(with_skill), f"skill failed cases: {with_skill}"
    assert sum(with_skill) >= sum(without_skill)
