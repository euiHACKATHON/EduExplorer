"""Structured output schemas for the Tutor / Scenario / NPC agents.

These are deliberately stricter than "whatever the LLM feels like returning."
Two kinds of safety are enforced here, not just in prompt wording:

1. Shape safety — every agent output is validated against a schema before it
   can reach main.py, so a malformed/partial LLM response fails loudly
   instead of silently shipping broken JSON to the Phaser frontend.
2. Content safety — HintResponse and TutorResponse are checked for leaked
   answer keys / option letters, and ScenarioResponse structurally has no
   field that could ever carry the answer (it's just not present on the
   model), so a agent can't leak graded content even if the prompt is
   sloppy or the model ignores an instruction.
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Source = Literal["ai", "authored-fallback"]

# Matches an uppercase option letter immediately followed by ")" or ":"
# (e.g. "C)", "B:") — deliberately case-sensitive and without a "." trigger,
# because lowercase single-letter physics notation like "(a)" or "m×a."
# is common in this domain and would otherwise false-positive constantly.
# "option C" / "answer is C" phrasing is still caught case-insensitively.
_ANSWER_LEAK_PATTERN = re.compile(
    r"\b[ABCD][):]|"
    r"(?i:\b(?:option|answer(?:\s+is)?|correct\s+(?:option|choice)(?:\s+is)?)"
    r"\s*[:=-]?\s*[ABCD]\b)"
)


def _reject_answer_leak(value: str) -> str:
    if _ANSWER_LEAK_PATTERN.search(value):
        raise ValueError(
            "Generated text appears to reveal an answer/option letter; "
            "regenerate or fall back to authored content instead."
        )
    return value


class LessonFacts(BaseModel):
    """The only slice of a challenge's data an agent is ever allowed to see.

    Notably absent: `answer`, `explanation`, and full `options` text — those
    stay server-side in the assessment endpoint. Build this with
    `lesson_facts_from_challenge()` below rather than constructing it from a
    raw challenge dict by hand, so nobody accidentally passes the answer key
    into a prompt.
    """

    mission_id: str
    question_id: str
    title: str
    subject: str
    context: str
    question: str
    lesson: str
    hints: list[str] = Field(min_length=1)


class DialogueOption(BaseModel):
    """Matches the option shape already used in public/mock/dialogue_*.json
    and expected by DialogueUI.js — do not rename these fields."""

    text: str
    action: Literal["START_CHALLENGE", "EXPLAIN"]
    payload: str


class NPCResponse(BaseModel):
    """Output of the NPC Agent — replaces the current inline generate() call
    inside dialogue(). Field names match the existing /ai/dialogue contract
    exactly so main.py can return this model with no reshaping."""

    npc_id: str
    npc_name: str
    message: str
    source: Source
    options: list[DialogueOption]

    @field_validator("message")
    @classmethod
    def no_answer_leak(cls, v: str) -> str:
        return _reject_answer_leak(v)


class TutorResponse(BaseModel):
    """Output of the Tutor Agent's explanation path — matches the existing
    /ai/explain contract ({"message": ..., "source": ...})."""

    message: str
    source: Source

    @field_validator("message")
    @classmethod
    def no_answer_leak(cls, v: str) -> str:
        return _reject_answer_leak(v)


class HintResponse(BaseModel):
    """Output of the Tutor Agent's hint path — matches the existing
    /ai/hint contract ({"hint": ..., "source": ...}), plus internal-only
    fields (`level`, `reveals_answer`) used for validation before main.py
    serializes just `hint`/`source` back to the frontend."""

    hint: str
    source: Source
    level: int = Field(ge=1, le=3)
    reveals_answer: bool = False

    @field_validator("reveals_answer")
    @classmethod
    def must_not_reveal_answer(cls, v: bool) -> bool:
        if v:
            raise ValueError(
                "A hint that reveals the answer must never be constructed; "
                "regenerate at the same level or fall back to authored content."
            )
        return v

    @field_validator("hint")
    @classmethod
    def no_answer_leak(cls, v: str) -> str:
        return _reject_answer_leak(v)


class ScenarioResponse(BaseModel):
    """Output of the Scenario Agent — returned by POST /ai/generate-scenario.
    Deliberately has
    no `answer`/`options` field: the Scenario Agent only wraps an authored
    mission in narrative flavor, it never generates gradable content."""

    mission_id: str
    mission_title: str
    objective: str
    difficulty: int = Field(ge=1, le=3, description="1=remedial, 2=normal, 3=advanced")
    npc_id: str
    source: Source

    @field_validator("mission_title", "objective")
    @classmethod
    def no_answer_leak(cls, v: str) -> str:
        return _reject_answer_leak(v)


def lesson_facts_from_challenge(challenge: dict) -> LessonFacts:
    """Strip a raw challenge dict (as loaded from public/mock/challenge_*.json
    or the /challenges/{id} endpoint) down to the fields an agent is allowed
    to see. Use this everywhere instead of passing `challenge` straight into
    a prompt — it's the single choke point that keeps `answer` and full
    `explanation` text out of every agent's context window."""

    return LessonFacts(
        mission_id=challenge["mission_id"],
        question_id=challenge["question_id"],
        title=challenge["title"],
        subject=challenge["subject"],
        context=challenge["context"],
        question=challenge["question"],
        lesson=challenge["lesson"],
        hints=challenge.get("hints", []),
    )
