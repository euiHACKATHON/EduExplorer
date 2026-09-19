"""Thin wrappers over the GenAI service.  ROUTER: backend engineer.
LOGIC: Person 1, in services/ai_agents.py.
"""
from fastapi import APIRouter, HTTPException

from ..schemas import Hint, Mission
from ..services import ai_agents, curriculum

router = APIRouter(prefix='/ai', tags=['ai'])


@router.get('/dialogue')
async def dialogue(npc_id: str, student_id: str = ''):
    data = curriculum.npc_dialogue(npc_id)
    q = curriculum.challenge(data['options'][0]['payload'])
    data['message'], data['source'] = await ai_agents.generate(
        'Introduce yourself as the provided crewmate. Give a short mission '
        'briefing without revealing the answer.',
        {'name': data['npc_name'], 'context': q['context'], 'lesson': q['lesson']},
        data['message'],
    )
    return data


@router.post('/hint')
async def hint(payload: Hint):
    q = curriculum.challenge(payload.mission_id)
    if q['question_id'] != payload.question_id:
        raise HTTPException(400, 'Question does not match mission')
    authored = q['hints'][payload.level - 1]
    text, source = await ai_agents.generate(
        'Give one scaffolded hint. Do not state the final answer or an option '
        'letter. Rephrase the supplied hint with a useful analogy if appropriate.',
        {'question': q['question'], 'hint': authored, 'level': payload.level},
        authored,
    )
    return {'hint': text, 'source': source}


@router.post('/explain')
async def explain(payload: Mission):
    q = curriculum.challenge(payload.mission_id)
    message, source = await ai_agents.generate(
        'Explain this science concept using a Mars analogy. Preserve the '
        'scientific meaning.',
        {'lesson': q['lesson']},
        q['lesson'],
    )
    return {'message': message, 'source': source}
