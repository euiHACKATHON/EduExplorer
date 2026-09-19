"""Student progress, game progression, and mission list.  OWNER: backend
engineer.

Registration/login live in routers/auth.py -- this file is just the data a
student (and only that student) can read about themselves.
"""
from fastapi import APIRouter, Depends

from ..config import KNOWN_MISSIONS
from ..database import connect
from ..deps import require_self
from ..services import adaptive, curriculum, progression

router = APIRouter(tags=['students'])


@router.get('/students/{student_id}/progress')
def progress(student_id: str, _current: str = Depends(require_self)):
    with connect() as db:
        rows = db.execute(
            'SELECT mission,context,xp,score FROM mastery WHERE student=?',
            (student_id,),
        ).fetchall()
    return adaptive.build_progress(rows)


@router.get('/students/{student_id}/game-progress')
def game_progress(student_id: str, _current: str = Depends(require_self)):
    """Level + badges, on top of the raw xp/mastery in /progress. Split into
    its own endpoint rather than folded into /progress so existing
    consumers of /progress don't need to change shape."""
    with connect() as db:
        mastery_rows = db.execute(
            'SELECT mission,context,xp,score FROM mastery WHERE student=?',
            (student_id,),
        ).fetchall()
        attempt_rows = db.execute(
            'SELECT mission,context,correct,hints_used FROM attempts WHERE student=?',
            (student_id,),
        ).fetchall()
    total_xp = sum(row[2] for row in mastery_rows)
    return {
        'xp': total_xp,
        'level': progression.level_for_xp(total_xp),
        'badges': progression.compute_badges(mastery_rows, attempt_rows),
    }


@router.get('/students/{student_id}/missions')
def list_missions(student_id: str, _current: str = Depends(require_self)):
    """Missions in order, with lock state for this student.

    Sequential unlock: mission N is playable once mission N-1 has been
    completed (any xp > 0 in the mastery table, matching the `completed`
    list build_progress already computes). The first mission is always
    unlocked. This is a deliberately simple placeholder -- once Person 2's
    adaptive next_challenge() exists, this endpoint can defer to it for
    which *context* to serve, not just which mission is playable.
    """
    with connect() as db:
        rows = db.execute(
            'SELECT mission,context,xp,score FROM mastery WHERE student=?',
            (student_id,),
        ).fetchall()
    completed = set(adaptive.build_progress(rows)['completed'])

    missions = []
    unlocked = True
    for mission_id in KNOWN_MISSIONS:
        q = curriculum.challenge(mission_id)
        missions.append({
            'mission_id': mission_id,
            'title': q.get('title', mission_id),
            'locked': not unlocked,
            'completed': mission_id in completed,
        })
        unlocked = mission_id in completed
    return {'missions': missions}
