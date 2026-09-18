"""NPC Agent — owns /ai/dialogue.

Generates in-character crewmate dialogue. Each NPC has a distinct persona
(instead of the one-size-fits-all instruction string main.py's generate()
uses today). Only the `message` text is ever LLM-generated — `options`
(the START_CHALLENGE / EXPLAIN game-logic actions) stay authored and are
passed straight through from public/mock/dialogue_{npc_id}.json, never
produced by the model, since they drive real navigation in the frontend.
"""

import os
from typing import Optional

from langchain_groq import ChatGroq
from pydantic import BaseModel

from .schemas import DialogueOption, LessonFacts, NPCResponse
from .state import AgentState, Turn

_llm: Optional[ChatGroq] = None


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.6,
        )
    return _llm


class _NPCDraft(BaseModel):
    message: str


# One persona per crewmate, matching the npc_id/npc_name pairs already in
# public/mock/dialogue_*.json. Add new crewmates here as the roster grows —
# this is the only place a new NPC's voice needs to be defined.
NPC_PERSONAS: dict[str, dict[str, str]] = {
    "scientist_01": {
        "name": "Dr. Sara",
        "voice": (
            "a warm, curious planetary scientist who gets excited about "
            "physics and often relates problems back to real rover "
            "engineering challenges."
        ),
    },
    "engineer_01": {
        "name": "Engineer Kai",
        "voice": (
            "a practical, upbeat colony engineer who talks in terms of "
            "power budgets, systems, and getting things fixed before "
            "nightfall."
        ),
    },
    "botanist_01": {
        "name": "Dr. Noor",
        "voice": (
            "a gentle, encouraging botanist who cares deeply about the "
            "greenhouse and ties science back to keeping living things "
            "alive on Mars."
        ),
    },
}

_NPC_SYSTEM_PROMPT_TEMPLATE = (
    "You are {name}, {voice} You are a crewmate NPC in a Mars colony "
    "educational game for ages 10-14. Stay fully in character. Give a short "
    "mission briefing that sets up the science problem without revealing "
    "the answer or any option letter. Use at most 60 words. Never ask for "
    "personal information."
)

_CONTINUE_SYSTEM_SUFFIX = (
    " The player has already spoken with you before — continue the "
    "conversation naturally in character, referencing the mission if "
    "relevant, still without revealing the answer."
)


def _format_history(history: list[Turn]) -> list[tuple[str, str]]:
    messages: list[tuple[str, str]] = []
    for turn in history:
        role = "assistant" if turn["role"] == "npc" else "human"
        messages.append((role, turn["content"]))
    return messages


async def generate_npc_message(
    npc_id: str, lesson_facts: LessonFacts, conversation_history: list[Turn]
) -> tuple[str, str]:
    """Returns (message, source). Falls back to a plain authored briefing
    line if no API key is set, generation fails, or validation fails (e.g.
    the draft leaked an answer letter)."""

    persona = NPC_PERSONAS.get(npc_id)
    fallback_message = (
        f"{persona['name'] if persona else 'Your crewmate'} needs your help "
        f"with: {lesson_facts.context}"
    )

    if persona is None or not os.getenv("GROQ_API_KEY"):
        return fallback_message, "authored-fallback"

    system_prompt = _NPC_SYSTEM_PROMPT_TEMPLATE.format(
        name=persona["name"], voice=persona["voice"]
    )
    if conversation_history:
        system_prompt += _CONTINUE_SYSTEM_SUFFIX

    try:
        structured_llm = _get_llm().with_structured_output(_NPCDraft)
        messages: list[tuple[str, str]] = [("system", system_prompt)]
        messages.extend(_format_history(conversation_history))
        messages.append(
            (
                "human",
                f"Mission context: {lesson_facts.context}\n"
                f"Underlying lesson: {lesson_facts.lesson}",
            )
        )
        draft: _NPCDraft = await structured_llm.ainvoke(messages)
        return draft.message, "ai"
    except Exception:
        return fallback_message, "authored-fallback"


async def generate_npc_response(
    npc_id: str,
    lesson_facts: LessonFacts,
    options: list[DialogueOption],
    conversation_history: list[Turn],
) -> NPCResponse:
    persona = NPC_PERSONAS.get(npc_id)
    if persona is None:
        raise ValueError(f"Unknown npc_id: {npc_id!r}")

    message, source = await generate_npc_message(npc_id, lesson_facts, conversation_history)
    try:
        return NPCResponse(
            npc_id=npc_id,
            npc_name=persona["name"],
            message=message,
            source=source,
            options=options,
        )
    except ValueError:
        # Validation failed on the generated message (e.g. leaked an answer
        # letter despite instructions) — hard-fall-back to authored text.
        return NPCResponse(
            npc_id=npc_id,
            npc_name=persona["name"],
            message=f"{persona['name']} needs your help with: {lesson_facts.context}",
            source="authored-fallback",
            options=options,
        )


async def npc_node(state: AgentState) -> AgentState:
    """LangGraph node — handles request_type == 'dialogue'."""

    if state.get("npc_id") is None:
        raise ValueError("npc_node requires state['npc_id'] to be set")
    if state.get("lesson_facts") is None:
        raise ValueError("npc_node requires state['lesson_facts'] to be set")

    result = await generate_npc_response(
        state["npc_id"],
        state["lesson_facts"],
        state.get("npc_options", []),
        state.get("conversation_history", []),
    )
    state["npc_result"] = result
    state["conversation_history"] = [
        *state.get("conversation_history", []),
        {"role": "npc", "content": result.message},
    ][-12:]
    return state
