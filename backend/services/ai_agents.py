"""LLM tutor / NPC / scenario generation.  OWNER: Person 1 (GenAI).

Thin wrapper around the LangGraph agent system in backend/agents/. Routers
pass a raw challenge dict (still holding the answer key -- these functions
are the last checkpoint before it gets stripped) plus request details;
these functions build the AgentState, run the graph, and hand back either
a validated response model's dict or a plain (text, source) shape,
matching what each route already returns.

Every path here falls back to authored content -- never raises -- so a
Groq outage degrades gracefully instead of 500ing. The schema-level
answer-leak guard lives in agents/schemas.py; `_contains_correct_answer`
below is a second, content-based check on top of it (catches the model
stating the right answer in its own words, not just a letter/pattern).
"""
import hashlib
import re

from ..agents.graph import run_agent
from ..agents.schemas import (
    DialogueOption,
    HintResponse,
    NPCResponse,
    ScenarioResponse,
    TutorResponse,
    lesson_facts_from_challenge,
)
from ..agents.state import new_state


def _thread_id(kind: str, student_id: str, identity: str) -> str:
    raw = f'{kind}:{student_id or "anonymous"}:{identity}'.encode()
    return f'{kind}-{hashlib.sha256(raw).hexdigest()[:24]}'


def _normalise(value: str) -> str:
    return re.sub(r'[^a-z0-9]', '', value.casefold())


def _contains_correct_answer(text: str, raw_challenge: dict) -> bool:
    correct = next(
        option['text'] for option in raw_challenge['options']
        if option['id'] == raw_challenge['answer']
    )
    answer = _normalise(correct)
    return len(answer) >= 3 and answer in _normalise(text)


async def npc_dialogue(npc_id: str, student_id: str, raw_challenge: dict, dialogue_data: dict) -> dict:
    facts = lesson_facts_from_challenge(raw_challenge)
    options = [DialogueOption.model_validate(o) for o in dialogue_data['options']]
    fallback = NPCResponse(
        npc_id=npc_id, npc_name=dialogue_data['npc_name'],
        message=dialogue_data['message'], source='authored-fallback', options=options,
    )
    state = new_state(
        'dialogue', student_id or 'anonymous', mission_id=facts.mission_id,
        npc_id=npc_id, lesson_facts=facts, npc_options=options,
    )
    result = await run_agent(state, _thread_id('dialogue', student_id, npc_id))
    response = result.get('npc_result')
    if not isinstance(response, NPCResponse):
        response = fallback
    elif response.source == 'ai' and _contains_correct_answer(response.message, raw_challenge):
        response = fallback
    return response.model_dump()


async def hint(mission_id: str, question_id: str, student_id: str, level: int, raw_challenge: dict) -> dict:
    facts = lesson_facts_from_challenge(raw_challenge)
    fallback = HintResponse(hint=raw_challenge['hints'][level - 1], source='authored-fallback', level=level)
    state = new_state(
        'hint', student_id or 'anonymous', mission_id=mission_id, question_id=question_id,
        lesson_facts=facts, hint_level=level, hints_used=level - 1,
    )
    result = await run_agent(state, _thread_id('hint', student_id, mission_id))
    response = result.get('hint_result')
    if not isinstance(response, HintResponse):
        response = fallback
    elif response.source == 'ai' and _contains_correct_answer(response.hint, raw_challenge):
        response = fallback
    return {'hint': response.hint, 'source': response.source}


async def explain(mission_id: str, raw_challenge: dict) -> dict:
    facts = lesson_facts_from_challenge(raw_challenge)
    fallback = TutorResponse(message=raw_challenge['lesson'], source='authored-fallback')
    state = new_state('explain', 'anonymous', mission_id=mission_id, lesson_facts=facts)
    result = await run_agent(state, _thread_id('explain', 'anonymous', mission_id))
    response = result.get('tutor_result')
    if not isinstance(response, TutorResponse):
        response = fallback
    elif response.source == 'ai' and _contains_correct_answer(response.message, raw_challenge):
        response = fallback
    return response.model_dump()


async def ask(mission_id: str, student_id: str, message: str, raw_challenge: dict) -> dict:
    facts = lesson_facts_from_challenge(raw_challenge)
    fallback = TutorResponse(
        message='I can help you work it out, but I cannot reveal the quiz answer. Which step feels unclear?',
        source='authored-fallback',
    )
    state = new_state(
        'ask', student_id, mission_id=mission_id, question_id=facts.question_id,
        lesson_facts=facts, user_message=message,
    )
    result = await run_agent(state, _thread_id('ask', student_id, mission_id))
    response = result.get('tutor_result')
    if not isinstance(response, TutorResponse):
        response = fallback
    elif response.source == 'ai' and _contains_correct_answer(response.message, raw_challenge):
        response = fallback
    return response.model_dump()


async def generate_scenario(mission_id: str, student_id: str, npc_id: str, difficulty: int, raw_challenge: dict) -> dict:
    facts = lesson_facts_from_challenge(raw_challenge)
    fallback = ScenarioResponse(
        mission_id=facts.mission_id, mission_title=facts.title, objective=facts.context,
        difficulty=difficulty, npc_id=npc_id, source='authored-fallback',
    )
    state = new_state(
        'scenario', student_id, mission_id=mission_id, npc_id=npc_id,
        lesson_facts=facts, difficulty_hint=difficulty,
    )
    result = await run_agent(state, _thread_id('scenario', student_id, mission_id))
    response = result.get('scenario_result')
    if not isinstance(response, ScenarioResponse):
        response = fallback
    elif response.source == 'ai' and (
        _contains_correct_answer(response.mission_title, raw_challenge)
        or _contains_correct_answer(response.objective, raw_challenge)
    ):
        response = fallback
    return response.model_dump()
