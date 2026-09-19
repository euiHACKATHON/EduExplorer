"""Student progress.  OWNER: backend engineer.

Registration/login live in routers/auth.py now -- this file is just the
data a student (and only that student) can read about themselves.
"""
from fastapi import APIRouter, Depends

from ..database import connect
from ..deps import require_self
from ..services import adaptive

router = APIRouter(tags=['students'])


@router.get('/students/{student_id}/progress')
def progress(student_id: str, _current: str = Depends(require_self)):
    with connect() as db:
        rows = db.execute(
            'SELECT mission,context,xp,score FROM mastery WHERE student=?',
            (student_id,),
        ).fetchall()
    return adaptive.build_progress(rows)
