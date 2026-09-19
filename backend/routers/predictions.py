""""Predict before you run it" mechanic.  OWNER: backend engineer."""
from fastapi import APIRouter, Depends, HTTPException

from ..database import connect
from ..deps import require_self
from ..schemas import PredictionCreate, PredictionResolve
from ..services import adaptive

router = APIRouter(prefix='/student', tags=['predictions'])


@router.post('/{student_id}/predict')
def submit_prediction(
    student_id: str, payload: PredictionCreate, _current: str = Depends(require_self)
):
    """Store the student's prediction before they see the outcome. Resolve it
    once the experiment reveals the actual result via /predict/resolve."""
    with connect() as db:
        cur = db.execute(
            'INSERT INTO predictions(student,mission,question_id,predicted) '
            'VALUES(?,?,?,?)',
            (student_id, payload.mission_id, payload.question_id, payload.predicted),
        )
        db.commit()
        prediction_id = cur.lastrowid
    return {'prediction_id': prediction_id, 'predicted': payload.predicted}


@router.post('/{student_id}/predict/resolve')
def resolve_prediction(
    student_id: str, payload: PredictionResolve, _current: str = Depends(require_self)
):
    with connect() as db:
        row = db.execute(
            'SELECT mission,predicted FROM predictions WHERE id=? AND student=?',
            (payload.prediction_id, student_id),
        ).fetchone()
        if row is None:
            raise HTTPException(404, 'Prediction not found')
        mission, predicted = row
        matched = predicted.strip().lower() == payload.actual.strip().lower()
        db.execute(
            'UPDATE predictions SET actual=?, matched=? WHERE id=?',
            (payload.actual, int(matched), payload.prediction_id),
        )
        # A matched prediction is strong evidence of transfer, not just
        # memorization -- feed it into the TRANSFER context mastery score.
        xp, mastery = adaptive.update_mastery(
            db, student_id, mission, 'transfer', matched, payload.hints_used
        )
        db.commit()
    return {'matched': matched, 'xp_earned': xp, 'mastery': mastery}
