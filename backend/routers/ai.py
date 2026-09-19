"""Thin wrappers over the GenAI agent system.  ROUTER: backend engineer.
LOGIC: Person 1, in services/ai_agents.py + agents/.
"""
from fastapi import APIRouter, HTTPException

from ..config import MISSION_NPCS
from ..schemas import AskTutor, Hint, Mission, ScenarioRequest
from ..database import connect
from ..services import adaptive, ai_agents, curriculum
router = APIRouter(prefix='/ai', tags=['ai'])


@router.get('/dialogue')
async def dialogue(npc_id: str, student_id: str = ''):
    dialogue_data = curriculum.npc_dialogue(npc_id)
    raw_challenge = curriculum.challenge(dialogue_data['options'][0]['payload'])
    return await ai_agents.npc_dialogue(npc_id, student_id, raw_challenge, dialogue_data)


@router.post('/hint')
async def hint(payload: Hint):
    raw_challenge = curriculum.challenge(payload.mission_id)
    if raw_challenge['question_id'] != payload.question_id:
        raise HTTPException(400, 'Question does not match mission')

    with connect() as db:
        level = adaptive.hint_level(
            db,
            payload.student_id,
            payload.mission_id,
            'numerical',
            time_seconds=0,
            explicit_request=True,
        )

    return await ai_agents.hint(
        payload.mission_id,
        payload.question_id,
        payload.student_id,
        level,
        raw_challenge,
    )


@router.post('/explain')
async def explain(payload: Mission):
    raw_challenge = curriculum.challenge(payload.mission_id)
    return await ai_agents.explain(payload.mission_id, raw_challenge)


@router.post('/tutor')
async def tutor(payload: Mission):
    """Additive alias for teammates following the agent implementation plan."""
    raw_challenge = curriculum.challenge(payload.mission_id)
    return await ai_agents.explain(payload.mission_id, raw_challenge)


@router.post('/ask')
async def ask(payload: AskTutor):
    raw_challenge = curriculum.challenge(payload.mission_id)
    return await ai_agents.ask(payload.mission_id, payload.student_id, payload.message, raw_challenge)


@router.post('/generate-scenario')
async def generate_scenario(payload: ScenarioRequest):
    raw_challenge = curriculum.challenge(payload.mission_id)
    npc_id = payload.npc_id or MISSION_NPCS[payload.mission_id]
    return await ai_agents.generate_scenario(
        payload.mission_id, payload.student_id, npc_id, payload.difficulty, raw_challenge,
    )
