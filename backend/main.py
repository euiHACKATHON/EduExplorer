"""Local classroom prototype. Auth and per-user rate limits are required before public hosting."""
import json
import os
import sqlite3
from pathlib import Path
from typing import Literal
from contextlib import closing
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import AsyncOpenAI

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
DB = os.getenv('MARS_DB', str(ROOT / 'backend' / 'progress.sqlite3'))
app = FastAPI(title='Mars Colony Explorer')
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173', 'http://127.0.0.1:5173'], allow_methods=['GET','POST'], allow_headers=['Content-Type'])
with closing(sqlite3.connect(DB)) as db:
    db.execute('CREATE TABLE IF NOT EXISTS scores (student TEXT, mission TEXT, xp INTEGER, mastery REAL, PRIMARY KEY(student,mission))')
    db.commit()


def challenge(mid):
    if mid not in ('M001','M002','M003'):
        raise HTTPException(404, 'Unknown mission')
    return json.loads((ROOT / 'public' / 'mock' / f'challenge_{mid}.json').read_text(encoding='utf-8'))


async def generate(instruction, context, fallback):
    if not os.getenv('OPENAI_API_KEY'):
        return fallback, 'authored-fallback'
    try:
        async with AsyncOpenAI(timeout=18, max_retries=0) as client:
            response = await client.responses.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
                instructions='You are a friendly Mars colony science tutor for ages 10–14. Stay within the supplied science facts. Use at most 80 words. Never ask for personal information. ' + instruction,
                input=json.dumps(context), max_output_tokens=220, store=False)
            if response.output_text and response.output_text.strip():
                return response.output_text.strip(), 'ai'
    except Exception:
        # Do not expose credentials, upstream error bodies, or student data.
        pass
    return fallback, 'authored-fallback'


@app.get('/health')
def health():
    return {'status':'ok','ai_available':bool(os.getenv('OPENAI_API_KEY'))}


@app.get('/challenges/{mission_id}')
def get_challenge(mission_id: str):
    q = challenge(mission_id)
    return {k:v for k,v in q.items() if k not in ('answer','explanation','hints')}


@app.get('/ai/dialogue')
async def dialogue(npc_id: str, student_id: str = ''):
    if npc_id not in ('scientist_01','engineer_01','botanist_01'):
        raise HTTPException(404, 'Unknown crewmate')
    data=json.loads((ROOT/'public'/'mock'/f'dialogue_{npc_id}.json').read_text(encoding='utf-8'))
    q=challenge(data['options'][0]['payload'])
    data['message'],data['source']=await generate('Introduce yourself as the provided crewmate. Give a short mission briefing without revealing the answer.',{'name':data['npc_name'],'context':q['context'],'lesson':q['lesson']},data['message'])
    return data


class Mission(BaseModel):
    mission_id: Literal['M001','M002','M003']


class Hint(Mission):
    question_id: str = Field(max_length=20)
    student_id: str = Field(max_length=100)
    level: int = Field(ge=1,le=3)


@app.post('/ai/hint')
async def hint(payload: Hint):
    q=challenge(payload.mission_id)
    if q['question_id']!=payload.question_id:
        raise HTTPException(400,'Question does not match mission')
    hint,source=await generate('Give one scaffolded hint. Do not state the final answer or an option letter. Rephrase the supplied hint with a useful analogy if appropriate.',{'question':q['question'],'hint':q['hints'][payload.level-1],'level':payload.level},q['hints'][payload.level-1])
    return {'hint':hint,'source':source}


@app.post('/ai/explain')
async def explain(payload: Mission):
    q=challenge(payload.mission_id)
    message,source=await generate('Explain this science concept using a Mars analogy. Preserve the scientific meaning.',{'lesson':q['lesson']},q['lesson'])
    return {'message':message,'source':source}


class Assessment(Mission):
    student_id: str = Field(min_length=1,max_length=100,pattern=r'^[a-zA-Z0-9_-]+$')
    question_id: str = Field(max_length=20)
    answer: Literal['A','B','C','D']
    time_taken: float = Field(ge=0,le=86400)
    hints_used: int = Field(ge=0,le=3)


@app.post('/assessment')
def assess(payload: Assessment):
    q=challenge(payload.mission_id)
    if payload.question_id != q['question_id']:
        raise HTTPException(400,'Question does not match mission')
    correct=payload.answer==q['answer']
    with closing(sqlite3.connect(DB,timeout=10)) as db:
        db.execute('BEGIN IMMEDIATE')
        previous=db.execute('SELECT xp,mastery FROM scores WHERE student=? AND mission=?',(payload.student_id,payload.mission_id)).fetchone()
        already=bool(previous and previous[0]>0)
        xp=max(50,100-15*payload.hints_used) if correct and not already else 0
        mastery=max(previous[1] if previous else 0, max(.6,1-.15*payload.hints_used) if correct else .2)
        db.execute('INSERT INTO scores VALUES(?,?,?,?) ON CONFLICT(student,mission) DO UPDATE SET xp=MAX(scores.xp,excluded.xp),mastery=MAX(scores.mastery,excluded.mastery)',(payload.student_id,payload.mission_id,xp,mastery))
        db.commit()
    return {'correct':correct,'xp_earned':xp,'mastery':mastery,'feedback':q['explanation'] if correct else 'Not quite. Check the relationship between the quantities, then try again.','source':'verified'}


@app.get('/students/{student_id}/progress')
def progress(student_id: str):
    with closing(sqlite3.connect(DB)) as db:
        rows=db.execute('SELECT mission,xp,mastery FROM scores WHERE student=?',(student_id,)).fetchall()
    return {'xp':sum(r[1] for r in rows),'completed':[r[0] for r in rows if r[1]>0],'mastery':{r[0]:r[2] for r in rows}}
