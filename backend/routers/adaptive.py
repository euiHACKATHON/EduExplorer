from fastapi import APIRouter, Depends

from ..database import connect
from ..deps import require_self
from ..services import adaptive

router = APIRouter(prefix='/adaptive', tags=['adaptive'])


@router.get('/student/{student_id}')
def student_state(
    student_id: str,
    _current: str = Depends(require_self),
):
    with connect() as db:
        return {
            'student_id': student_id,
            'state': adaptive.student_state(db, student_id),
        }


@router.get('/next/{student_id}')
def next_challenge(
    student_id: str,
    _current: str = Depends(require_self),
):
    with connect() as db:
        return adaptive.next_challenge(db, student_id)