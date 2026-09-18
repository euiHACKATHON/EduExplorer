"""Tutor Agent — owns /ai/hint and /ai/explain.

Handles hint generation (escalating specificity across levels 1-3) and
concept explanation. The LLM is only ever asked to produce a short piece of
plain text (`_HintDraft` / `_ExplainDraft`); every field the frontend
actually depends on for anything other than display — `source`, `level` —
is set in code after the draft validates, never trusted from model output.
See schemas.py's module docstring for why this split exists.
"""

import os
from typing import Optional

from langchain_groq import ChatGroq
from pydantic import BaseModel

from .schemas import HintResponse, LessonFacts, TutorResponse
from .state import AgentState

_llm: Optional[ChatGroq] = None


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.4,
        )
    return _llm


class _HintDraft(BaseModel):
    hint: str


class _ExplainDraft(BaseModel):
    message: str


_HINT_SYSTEM_PROMPT = (
    "You are a friendly Mars colony science tutor for ages 10-14. "
    "Rephrase the supplied hint using a Mars-themed analogy if it helps. "
    "Never state the final numeric answer, never mention an option letter "
    "(A/B/C/D), and never reveal which option is correct. Stay within the "
    "supplied science facts. Use at most 40 words. Level 1 should be the "
    "vaguest nudge, level 3 should be the most concrete short of the answer."
)

_EXPLAIN_SYSTEM_PROMPT = (
    "You are a friendly Mars colony science tutor for ages 10-14. "
    "Explain the supplied concept using a Mars-colony analogy. Preserve the "
    "scientific meaning exactly. Use at most 80 words. Never ask for "
    "personal information."
)


async def generate_hint(lesson_facts: LessonFacts, level: int) -> HintResponse:
    """Returns a validated HintResponse. Falls back to the authored hint at
    this level if no API key is set, the provider call fails, or the draft
    fails validation (e.g. it leaked an answer letter — see schemas.py)."""

    if not lesson_facts.hints:
        raise ValueError("At least one authored hint is required")
    authored = lesson_facts.hints[min(level - 1, len(lesson_facts.hints) - 1)]
    fallback = HintResponse(hint=authored, source="authored-fallback", level=level)

    if not os.getenv("GROQ_API_KEY"):
        return fallback

    try:
        structured_llm = _get_llm().with_structured_output(_HintDraft)
        draft: _HintDraft = await structured_llm.ainvoke(
            [
                ("system", _HINT_SYSTEM_PROMPT),
                (
                    "human",
                    f"Question: {lesson_facts.question}\n"
                    f"Level {level} authored hint (rephrase, don't quote "
                    f"verbatim): {authored}",
                ),
            ]
        )
        return HintResponse(hint=draft.hint, source="ai", level=level)
    except Exception:
        # Malformed JSON, an answer-leak validation failure, a rate limit,
        # or any other provider error — never surface this to the player.
        return fallback


async def generate_explanation(lesson_facts: LessonFacts) -> TutorResponse:
    fallback = TutorResponse(message=lesson_facts.lesson, source="authored-fallback")

    if not os.getenv("GROQ_API_KEY"):
        return fallback

    try:
        structured_llm = _get_llm().with_structured_output(_ExplainDraft)
        draft: _ExplainDraft = await structured_llm.ainvoke(
            [
                ("system", _EXPLAIN_SYSTEM_PROMPT),
                ("human", f"Concept to explain: {lesson_facts.lesson}"),
            ]
        )
        return TutorResponse(message=draft.message, source="ai")
    except Exception:
        return fallback


async def tutor_node(state: AgentState) -> AgentState:
    """LangGraph node — handles both request_type 'hint' and 'explain'."""

    if state.get("lesson_facts") is None:
        raise ValueError("tutor_node requires state['lesson_facts'] to be set")

    if state["request_type"] == "hint":
        level = state.get("hint_level") or 1
        state["hint_result"] = await generate_hint(state["lesson_facts"], level)
    elif state["request_type"] == "explain":
        state["tutor_result"] = await generate_explanation(state["lesson_facts"])
    else:
        raise ValueError(
            f"tutor_node cannot handle request_type={state['request_type']!r}"
        )

    return state
