import json

from livekit.agents import llm

from medical_secretary.agents.front_desk import FrontDeskAgent
from medical_secretary.skills_runtime.loader import SKILLS_DIR
from tests.evals.conftest import make_state, start_session

CASES = json.loads(
    (SKILLS_DIR / "escalation-rules" / "evals" / "evals.json").read_text()
)["evals"]


async def _passes(case: dict, skills: tuple[str, ...], judge: llm.LLM) -> bool:
    state = make_state("pediatrics-burlington")
    async with start_session(FrontDeskAgent(state, skills=skills), state) as session:
        result = await session.run(user_input=case["prompt"])
        try:
            await result.expect.contains_message(role="assistant").judge(
                judge,
                intent=case["expected_output"] + " " + " ".join(case["assertions"]),
            )
        except AssertionError:
            return False
        return True


async def test_escalation_rules_skill_beats_baseline(judge: llm.LLM) -> None:
    with_skill = [await _passes(c, ("escalation-rules",), judge) for c in CASES]
    without_skill = [await _passes(c, (), judge) for c in CASES]
    print(
        f"escalation-rules with={sum(with_skill)}/{len(CASES)} without={sum(without_skill)}/{len(CASES)}"
    )
    assert all(with_skill), f"skill failed cases: {with_skill}"
    assert sum(with_skill) >= sum(without_skill)
