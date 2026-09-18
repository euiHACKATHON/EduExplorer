"""Shared LangGraph state for the Supervisor → Tutor/Scenario/NPC graph.

One AgentState flows through every node. The Supervisor reads `request_type`
to decide which node(s) to invoke; each agent node reads only the slice of
state it needs and writes its result to `result`.
"""

from typing import Literal, Optional, TypedDict

from .schemas import DialogueOption, HintResponse, LessonFacts, NPCResponse, ScenarioResponse, TutorResponse

RequestType = Literal["dialogue", "explain", "hint", "scenario"]

# A turn of conversation, stored so multi-turn NPC dialogue has context
# across separate HTTP requests once the checkpointer is wired in (Step 7).
class Turn(TypedDict):
    role: Literal["npc", "student"]
    content: str


class AgentState(TypedDict, total=False):
    # --- identity / routing -------------------------------------------------
    request_type: RequestType
    student_id: str
    mission_id: Optional[str]
    npc_id: Optional[str]
    question_id: Optional[str]

    # --- inputs --------------------------------------------------------------
    # Populated via schemas.lesson_facts_from_challenge() — never pass a raw
    # challenge dict here, it may still contain the answer key.
    lesson_facts: Optional[LessonFacts]
    hint_level: Optional[int]          # 1-3, required when request_type == "hint"
    hints_used: int                     # running count for this student+mission

    # The NPC Agent never generates these — they're deterministic, authored
    # game-logic actions (START_CHALLENGE / EXPLAIN) loaded from
    # public/mock/dialogue_{npc_id}.json and passed straight through. Only
    # the `message` field around them is ever LLM-generated.
    npc_options: list[DialogueOption]

    # Person 2's hook: mastery-derived difficulty (0.0-1.0 or a bucketed int).
    # Stubbed to a fixed value until the adaptive-learning endpoint exists.
    difficulty_hint: Optional[int]

    # Person 3's hook: RAG-retrieved supporting material, if/when the
    # curriculum service exists. Until then this stays empty and agents fall
    # back to `lesson_facts` alone.
    retrieved_context: list[str]

    # Multi-turn NPC conversation history, persisted across calls via the
    # graph's in-memory checkpointer (keyed by a hashed session identifier).
    conversation_history: list[Turn]

    # --- output ---------------------------------------------------------------
    # Exactly one of these is populated, depending on request_type. Kept as
    # separate optional fields (rather than one `Any`) so main.py can type-check
    # which response model it's about to serialize.
    npc_result: Optional[NPCResponse]
    tutor_result: Optional[TutorResponse]
    hint_result: Optional[HintResponse]
    scenario_result: Optional[ScenarioResponse]


def new_state(
    request_type: RequestType,
    student_id: str,
    **overrides,
) -> AgentState:
    """Build a fresh AgentState with sane defaults, so call sites in main.py
    don't need to remember every field name and its default."""

    state: AgentState = {
        "request_type": request_type,
        "student_id": student_id,
        "mission_id": None,
        "npc_id": None,
        "question_id": None,
        "lesson_facts": None,
        "hint_level": None,
        "hints_used": 0,
        "npc_options": [],
        "difficulty_hint": None,
        "retrieved_context": [],
        "conversation_history": [],
        "npc_result": None,
        "tutor_result": None,
        "hint_result": None,
        "scenario_result": None,
    }
    state.update(overrides)
    return state
