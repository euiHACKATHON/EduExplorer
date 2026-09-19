"""Curriculum / content loading + curriculum RAG.  OWNER: Person 3 (RAG & Curriculum).

Two jobs:

1. `challenge()` / `npc_dialogue()` still read the authored JSON in public/mock/.
   Their signatures and returned dict shapes are unchanged, so routers and the
   agents keep working. (Replace the bodies when questions move to a database.)

2. Curriculum knowledge for everyone else, backed by services/rag/:
   - context_for(mission_id, question)  -> passages for AgentState.retrieved_context
   - search(question, ...)              -> ranked curriculum passages
   - objectives(...), topic_detail(...) -> learning objectives / topic info
   - learning_path(), next_topics(...)  -> knowledge-graph queries (for Person 2)
   - add_upload(...)                    -> index an uploaded curriculum document

The index is built lazily once and reused. `context_for` NEVER raises: if
retrieval breaks, the tutor simply runs without extra context.
"""
import json
import logging
from typing import Optional

from fastapi import HTTPException

from ..config import KNOWN_MISSIONS, KNOWN_NPCS, MOCK_DIR
from .rag.index import CurriculumIndex

log = logging.getLogger(__name__)


# --- authored challenges & dialogue (unchanged contract) ---------------------------
def challenge(mission_id: str, context: Optional[str] = None) -> dict:
    """Return the full challenge record, answer and hints included.

    Callers that send this to a student MUST strip the private keys --
    see routers/missions.py.
    """
    if mission_id not in KNOWN_MISSIONS:
        raise HTTPException(404, 'Unknown mission')
    # Prefer a context-specific variant (challenge_M001_transfer.json) if one
    # exists; fall back to the base file. Lets missions grow extra context
    # variants incrementally without breaking single-variant missions.
    if context:
        variant = MOCK_DIR / f'challenge_{mission_id}_{context}.json'
        if variant.exists():
            return json.loads(variant.read_text(encoding='utf-8'))
    return json.loads((MOCK_DIR / f'challenge_{mission_id}.json').read_text(encoding='utf-8'))


def npc_dialogue(npc_id: str) -> dict:
    if npc_id not in KNOWN_NPCS:
        raise HTTPException(404, 'Unknown crewmate')
    return json.loads((MOCK_DIR / f'dialogue_{npc_id}.json').read_text(encoding='utf-8'))


# --- curriculum knowledge (RAG + knowledge graph) ---------------------------------------
_index: Optional[CurriculumIndex] = None


def get_index() -> CurriculumIndex:
    """Lazily built singleton."""
    global _index
    if _index is None:
        _index = CurriculumIndex()
    return _index


def warm_up() -> None:
    """Build the index now (called once at server start-up), so the first request is
    fast and a first-run model download shows in the server terminal."""
    get_index()


def context_for(mission_id: str, question: Optional[str] = None, k: int = 3) -> list[str]:
    try:
        return get_index().context_for(mission_id, question, k)
    except Exception:
        log.exception('Curriculum retrieval failed; continuing without extra context')
        return []


def search(question: str, k: int = 4, topic_id: Optional[str] = None):
    return get_index().search(question, k=k, topic_id=topic_id)


def objectives(topic_id: Optional[str] = None, unit: Optional[str] = None) -> list[dict]:
    return get_index().objectives(topic_id=topic_id, unit=unit)


def objectives_for_mission(mission_id: str) -> list[dict]:
    idx = get_index()
    return [o for o in idx.objectives() if mission_id in o['mission_ids']]


def topic_detail(topic_id: str) -> Optional[dict]:
    return get_index().topic_detail(topic_id)


def learning_path() -> list[str]:
    return get_index().graph.learning_path()


def next_topics(mastered: set[str]) -> list[str]:
    """Topic ids a student is ready to learn, given the topics they have mastered."""
    return get_index().graph.next_topics(mastered)


def add_upload(filename: str, text: str) -> int:
    return get_index().add_upload(filename, text)
