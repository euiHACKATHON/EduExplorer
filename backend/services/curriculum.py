"""Curriculum / content loading.  OWNER: Person 3 (RAG & Curriculum).

Today this reads authored JSON from public/mock/. Replace the bodies with
DB- or knowledge-graph-backed lookups; keep the signatures and the returned
dict shape identical so the routers do not change.
"""
import json
from typing import Optional

from fastapi import HTTPException

from ..config import KNOWN_MISSIONS, KNOWN_NPCS, MOCK_DIR


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
