"""Thin wrappers over the GenAI agent system.  ROUTER: backend engineer.
LOGIC: Person 1, in services/ai_agents.py + agents/.

Every route calls rate_limit.check() first -- these are the endpoints that
cost real money per call. See services/rate_limit.py and
deps.ai_rate_limit_key for how the limit is keyed and configured.
"""
from fastapi import APIRouter, HTTPException, Request

from ..config import MISSION_NPCS
from ..deps import ai_rate_limit_key
from ..schemas import AskTutor, Hint, Mission, ScenarioRequest
from ..services import ai_agents, curriculum, rate_limit

router = APIRouter(prefix='/ai', tags=['ai'])


@router.get('/dialogue')
async def dialogue(npc_id: str, request: Request, student_id: str = ''):
    rate_limit.check(ai_rate_limit_key(student_id, request))
    dialogue_data = curriculum.npc_dialogue(npc_id)
    raw_challenge = curriculum.challenge(dialogue_data['options'][0]['payload'])
    return await ai_agents.npc_dialogue(npc_id, student_id, raw_challenge, dialogue_data)


@router.post('/hint')
async def hint(payload: Hint, request: Request):
    rate_limit.check(ai_rate_limit_key(payload.student_id, request))
    raw_challenge = curriculum.challenge(payload.mission_id)
    if raw_challenge['question_id'] != payload.question_id:
        raise HTTPException(400, 'Question does not match mission')
    return await ai_agents.hint(
        payload.mission_id, payload.question_id, payload.student_id, payload.level, raw_challenge,
    )


@router.post('/explain')
async def explain(payload: Mission, request: Request):
    # Mission has no student_id field -- falls back to IP-based limiting.
    rate_limit.check(ai_rate_limit_key(None, request))
    raw_challenge = curriculum.challenge(payload.mission_id)
    return await ai_agents.explain(payload.mission_id, raw_challenge)


@router.post('/tutor')
async def tutor(payload: Mission, request: Request):
    """Additive alias for teammates following the agent implementation plan."""
    rate_limit.check(ai_rate_limit_key(None, request))
    raw_challenge = curriculum.challenge(payload.mission_id)
    return await ai_agents.explain(payload.mission_id, raw_challenge)


@router.post('/ask')
async def ask(payload: AskTutor, request: Request):
    rate_limit.check(ai_rate_limit_key(payload.student_id, request))
    raw_challenge = curriculum.challenge(payload.mission_id)
    return await ai_agents.ask(payload.mission_id, payload.student_id, payload.message, raw_challenge)


@router.post('/generate-scenario')
async def generate_scenario(payload: ScenarioRequest, request: Request):
    # ScenarioRequest.student_id defaults to 'anonymous' rather than empty,
    # so anonymous callers share one bucket here instead of falling back to
    # per-IP like the other unauthenticated routes -- acceptable for now,
    # worth revisiting if scenario generation gets hit anonymously a lot.
    rate_limit.check(ai_rate_limit_key(payload.student_id, request))
    raw_challenge = curriculum.challenge(payload.mission_id)
    npc_id = payload.npc_id or MISSION_NPCS[payload.mission_id]
    return await ai_agents.generate_scenario(
        payload.mission_id, payload.student_id, npc_id, payload.difficulty, raw_challenge,
    )
