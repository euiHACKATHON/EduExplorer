"""Mission and challenge delivery.  OWNER: backend engineer."""
from typing import Optional

from fastapi import APIRouter

from ..schemas import ContextType
from ..services import curriculum

router = APIRouter(tags=['missions'])

# Keys that must never reach a student-facing response.
PRIVATE_KEYS = ('answer', 'explanation', 'hints')


@router.get('/challenges/{mission_id}')
def get_challenge(mission_id: str, context: Optional[ContextType] = None):
    q = curriculum.challenge(mission_id, context)
    return {k: v for k, v in q.items() if k not in PRIVATE_KEYS}
