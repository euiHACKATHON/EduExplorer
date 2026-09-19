"""Student progress and mission list.  OWNER: backend engineer.

Registration/login live in routers/auth.py -- this file is just the data a
student (and only that student) can read about themselves.
"""
from fastapi import APIRouter, Depends

from ..config import KNOWN_MISSIONS
from ..database import connect
from ..deps import require_self
from ..services import adaptive, curriculum

router = APIRouter(tags=['students'])


@router.get('/students/{student_id}/progress')
def progress(student_id: str, _current: str = Depends(require_self)):
    with connect() as db:
        rows = db.execute(
            'SELECT mission,context,xp,score FROM mastery WHERE student=?',
            (student_id,),
        ).fetchall()
    return adaptive.build_progress(rows)


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
