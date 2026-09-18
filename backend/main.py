"""Local classroom prototype. Add auth and rate limits before public hosting."""

import hashlib
import json
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.agents.graph import run_agent
from backend.agents.schemas import (
    DialogueOption,
    HintResponse,
    NPCResponse,
    ScenarioResponse,
    TutorResponse,
    lesson_facts_from_challenge,
)
from backend.agents.state import new_state

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DB = os.getenv("MARS_DB", str(ROOT / "backend" / "progress.sqlite3"))
MISSIONS = ("M001", "M002", "M003")
NPCS = ("scientist_01", "engineer_01", "botanist_01")
MISSION_NPCS = dict(zip(MISSIONS, NPCS))

app = FastAPI(title="Celestial Academy")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
with closing(sqlite3.connect(DB)) as db:
    db.execute(
        "CREATE TABLE IF NOT EXISTS scores "
        "(student TEXT, mission TEXT, xp INTEGER, mastery REAL, "
        "PRIMARY KEY(student,mission))"
    )
    db.commit()


def challenge(mission_id: str) -> dict:
    if mission_id not in MISSIONS:
        raise HTTPException(404, "Unknown mission")
    path = ROOT / "public" / "mock" / f"challenge_{mission_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _dialogue_data(npc_id: str) -> dict:
    if npc_id not in NPCS:
        raise HTTPException(404, "Unknown crewmate")
    path = ROOT / "public" / "mock" / f"dialogue_{npc_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _thread_id(kind: str, student_id: str, identity: str) -> str:
    raw = f"{kind}:{student_id or 'anonymous'}:{identity}".encode()
    return f"{kind}-{hashlib.sha256(raw).hexdigest()[:24]}"


def _normalise_answer_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _contains_correct_answer(text: str, raw_challenge: dict) -> bool:
    """Post-generation guard; the answer is never placed in model context."""

    correct = next(
        option["text"]
        for option in raw_challenge["options"]
        if option["id"] == raw_challenge["answer"]
    )
    answer = _normalise_answer_text(correct)
    return len(answer) >= 3 and answer in _normalise_answer_text(text)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ai_available": bool(os.getenv("GROQ_API_KEY")),
        "provider": "groq",
    }


@app.get("/challenges/{mission_id}")
def get_challenge(mission_id: str):
    question = challenge(mission_id)
    return {
        key: value
        for key, value in question.items()
        if key not in ("answer", "explanation", "hints")
    }


@app.get("/ai/dialogue")
async def dialogue(npc_id: str, student_id: str = ""):
    data = _dialogue_data(npc_id)
    question = challenge(data["options"][0]["payload"])
    facts = lesson_facts_from_challenge(question)
    options = [DialogueOption.model_validate(option) for option in data["options"]]
    state = new_state(
        "dialogue",
        student_id or "anonymous",
        mission_id=facts.mission_id,
        npc_id=npc_id,
        lesson_facts=facts,
        npc_options=options,
    )
    result = await run_agent(state, _thread_id("dialogue", student_id, npc_id))
    response = result.get("npc_result")
    if not isinstance(response, NPCResponse):
        raise HTTPException(503, "Dialogue agent unavailable")
    if response.source == "ai" and _contains_correct_answer(response.message, question):
        response = NPCResponse(
            npc_id=npc_id,
            npc_name=data["npc_name"],
            message=data["message"],
            source="authored-fallback",
            options=options,
        )
    return response.model_dump()


class Mission(BaseModel):
    mission_id: Literal["M001", "M002", "M003"]


class Hint(Mission):
    question_id: str = Field(max_length=20)
    student_id: str = Field(max_length=100)
    level: int = Field(ge=1, le=3)


@app.post("/ai/hint")
async def hint(payload: Hint):
    question = challenge(payload.mission_id)
    if question["question_id"] != payload.question_id:
        raise HTTPException(400, "Question does not match mission")
    facts = lesson_facts_from_challenge(question)
    state = new_state(
        "hint",
        payload.student_id or "anonymous",
        mission_id=payload.mission_id,
        question_id=payload.question_id,
        lesson_facts=facts,
        hint_level=payload.level,
        hints_used=payload.level - 1,
    )
    result = await run_agent(
        state,
        _thread_id("hint", payload.student_id, payload.mission_id),
    )
    response = result.get("hint_result")
    if not isinstance(response, HintResponse):
        raise HTTPException(503, "Tutor agent unavailable")
    if response.source == "ai" and _contains_correct_answer(response.hint, question):
        response = HintResponse(
            hint=question["hints"][payload.level - 1],
            source="authored-fallback",
            level=payload.level,
        )
    return {"hint": response.hint, "source": response.source}


async def _explain(payload: Mission):
    question = challenge(payload.mission_id)
    facts = lesson_facts_from_challenge(question)
    state = new_state(
        "explain",
        "anonymous",
        mission_id=payload.mission_id,
        lesson_facts=facts,
    )
    result = await run_agent(state, _thread_id("explain", "anonymous", payload.mission_id))
    response = result.get("tutor_result")
    if not isinstance(response, TutorResponse):
        raise HTTPException(503, "Tutor agent unavailable")
    if response.source == "ai" and _contains_correct_answer(response.message, question):
        response = TutorResponse(
            message=question["lesson"], source="authored-fallback"
        )
    return response.model_dump()


@app.post("/ai/explain")
async def explain(payload: Mission):
    return await _explain(payload)


@app.post("/ai/tutor")
async def tutor(payload: Mission):
    """Additive alias for teammates following the agent implementation plan."""

    return await _explain(payload)


class ScenarioRequest(Mission):
    student_id: str = Field(default="anonymous", max_length=100)
    npc_id: Literal["scientist_01", "engineer_01", "botanist_01"] | None = None
    difficulty: int = Field(default=2, ge=1, le=3)


@app.post("/ai/generate-scenario")
async def generate_scenario(payload: ScenarioRequest):
    question = challenge(payload.mission_id)
    facts = lesson_facts_from_challenge(question)
    npc_id = payload.npc_id or MISSION_NPCS[payload.mission_id]
    state = new_state(
        "scenario",
        payload.student_id,
        mission_id=payload.mission_id,
        npc_id=npc_id,
        lesson_facts=facts,
        difficulty_hint=payload.difficulty,
    )
    result = await run_agent(
        state,
        _thread_id("scenario", payload.student_id, payload.mission_id),
    )
    response = result.get("scenario_result")
    if not isinstance(response, ScenarioResponse):
        raise HTTPException(503, "Scenario agent unavailable")
    if response.source == "ai" and (
        _contains_correct_answer(response.mission_title, question)
        or _contains_correct_answer(response.objective, question)
    ):
        response = ScenarioResponse(
            mission_id=facts.mission_id,
            mission_title=facts.title,
            objective=facts.context,
            difficulty=payload.difficulty,
            npc_id=npc_id,
            source="authored-fallback",
        )
    return response.model_dump()


class Assessment(Mission):
    student_id: str = Field(
        min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$"
    )
    question_id: str = Field(max_length=20)
    answer: Literal["A", "B", "C", "D"]
    time_taken: float = Field(ge=0, le=86400)
    hints_used: int = Field(ge=0, le=3)


@app.post("/assessment")
def assess(payload: Assessment):
    question = challenge(payload.mission_id)
    if payload.question_id != question["question_id"]:
        raise HTTPException(400, "Question does not match mission")
    correct = payload.answer == question["answer"]
    with closing(sqlite3.connect(DB, timeout=10)) as db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute(
            "SELECT xp,mastery FROM scores WHERE student=? AND mission=?",
            (payload.student_id, payload.mission_id),
        ).fetchone()
        already = bool(previous and previous[0] > 0)
        xp = max(50, 100 - 15 * payload.hints_used) if correct and not already else 0
        mastery = max(
            previous[1] if previous else 0,
            max(0.6, 1 - 0.15 * payload.hints_used) if correct else 0.2,
        )
        db.execute(
            "INSERT INTO scores VALUES(?,?,?,?) "
            "ON CONFLICT(student,mission) DO UPDATE SET "
            "xp=MAX(scores.xp,excluded.xp),"
            "mastery=MAX(scores.mastery,excluded.mastery)",
            (payload.student_id, payload.mission_id, xp, mastery),
        )
        db.commit()
    return {
        "correct": correct,
        "xp_earned": xp,
        "mastery": mastery,
        "feedback": question["explanation"]
        if correct
        else "Not quite. Check the relationship between the quantities, then try again.",
        "source": "verified",
    }


@app.get("/students/{student_id}/progress")
def progress(student_id: str):
    with closing(sqlite3.connect(DB)) as db:
        rows = db.execute(
            "SELECT mission,xp,mastery FROM scores WHERE student=?", (student_id,)
        ).fetchall()
    return {
        "xp": sum(row[1] for row in rows),
        "completed": [row[0] for row in rows if row[1] > 0],
        "mastery": {row[0]: row[2] for row in rows},
    }
