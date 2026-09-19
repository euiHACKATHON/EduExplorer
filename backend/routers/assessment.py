"""Assessment endpoint.  ROUTER: backend engineer.
GRADING: Person 5 (services/assessment.py).  SCORING: Person 2 (services/adaptive.py).
"""
from fastapi import APIRouter, Depends, HTTPException

from ..database import connect
from ..deps import get_current_student
from ..schemas import Assessment
from ..services import adaptive, assessment as grading, curriculum

router = APIRouter(tags=['assessment'])


@router.post('/assessment')
def assess(payload: Assessment, current_student: str = Depends(get_current_student)):
    if payload.student_id != current_student:
        raise HTTPException(403, "Cannot submit an assessment for another student")
    q = curriculum.challenge(payload.mission_id, payload.context)
    if payload.question_id != q['question_id']:
        raise HTTPException(400, 'Question does not match mission')
    correct = grading.grade(q, payload.answer)
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        xp, mastery = adaptive.update_mastery(
            db, payload.student_id, payload.mission_id,
            payload.context, correct, payload.hints_used,
        )
        db.execute(
            'INSERT INTO attempts(student,mission,context,question_id,correct,'
            'hints_used,time_taken) VALUES(?,?,?,?,?,?,?)',
            (payload.student_id, payload.mission_id, payload.context,
             payload.question_id, int(correct), payload.hints_used, payload.time_taken),
        )
        db.commit()
    return {
        'correct': correct,
        'xp_earned': xp,
        'mastery': mastery,
        'feedback': grading.feedback(q, correct),
        'source': 'verified',
    }
