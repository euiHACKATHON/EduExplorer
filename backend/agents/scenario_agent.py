"""Scenario Agent — owns POST /ai/generate-scenario.

Generates the narrative framing around an authored mission — title,
objective, which NPC delivers it — based on the student's current
difficulty bucket. It never sees the graded question or hints (only
`title`/`subject`/`context` from LessonFacts get used), and
`ScenarioResponse` structurally has no field that could carry an answer, so
this agent cannot leak graded content regardless of what the model does.
"""

import os
from typing import Optional

from langchain_groq import ChatGroq
from pydantic import BaseModel

from .schemas import LessonFacts, ScenarioResponse
from .state import AgentState

_llm: Optional[ChatGroq] = None


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7,  # a bit more creative latitude than the Tutor agent
        )
    return _llm


class _ScenarioDraft(BaseModel):
    mission_title: str
    objective: str


_SCENARIO_SYSTEM_PROMPT = (
    "You are a narrative designer for a Mars colony educational game aimed "
    "at ages 10-14. Given a mission's subject and setting context, write a "
    "short in-universe mission title and a one-sentence objective framed as "
    "an urgent colony task. Do not mention numbers, quantities, or any "
    "specific science facts — that content is handled elsewhere. Keep the "
    "tone adventurous but age-appropriate."
)

_DIFFICULTY_FLAVOR = {
    1: "This is a remedial retry — keep the framing simple and encouraging.",
    2: "This is a standard-difficulty mission.",
    3: "This is an advanced mission — raise the stakes in the framing.",
}


async def generate_scenario(
    lesson_facts: LessonFacts, npc_id: str, difficulty: int
) -> ScenarioResponse:
    """Returns a validated ScenarioResponse, falling back to the authored
    title/context verbatim if no API key is set or generation fails."""

    fallback = ScenarioResponse(
        mission_id=lesson_facts.mission_id,
        mission_title=lesson_facts.title,
        objective=lesson_facts.context,
        difficulty=difficulty,
        npc_id=npc_id,
        source="authored-fallback",
    )

    if not os.getenv("GROQ_API_KEY"):
        return fallback

    try:
        structured_llm = _get_llm().with_structured_output(_ScenarioDraft)
        draft: _ScenarioDraft = await structured_llm.ainvoke(
            [
                ("system", _SCENARIO_SYSTEM_PROMPT),
                (
                    "human",
                    f"Subject: {lesson_facts.subject}\n"
                    f"Setting context: {lesson_facts.context}\n"
                    f"{_DIFFICULTY_FLAVOR.get(difficulty, _DIFFICULTY_FLAVOR[2])}",
                ),
            ]
        )
        return ScenarioResponse(
            mission_id=lesson_facts.mission_id,
            mission_title=draft.mission_title,
            objective=draft.objective,
            difficulty=difficulty,
            npc_id=npc_id,
            source="ai",
        )
    except Exception:
        return fallback


async def scenario_node(state: AgentState) -> AgentState:
    """LangGraph node — handles request_type == 'scenario'."""

    if state.get("lesson_facts") is None:
        raise ValueError("scenario_node requires state['lesson_facts'] to be set")
    if state.get("npc_id") is None:
        raise ValueError("scenario_node requires state['npc_id'] to be set")

    # Person 2's hook: replace this stub default with the real mastery-derived
    # difficulty once GET /student/{id}/next-challenge exists.
    difficulty = state.get("difficulty_hint") or 2

    state["scenario_result"] = await generate_scenario(
        state["lesson_facts"], state["npc_id"], difficulty
    )
    return state
