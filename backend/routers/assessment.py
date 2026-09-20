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

    # Person 5 Assessment Evaluation
    eval_result = grading.evaluate_assessment(
        question=q,
        answer=payload.answer,
        time_taken=payload.time_taken,
        hints_used=payload.hints_used,
        context=payload.context,
        mission_id=payload.mission_id,
    )

    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        xp, mastery = adaptive.update_mastery(
            db,
            payload.student_id,
            payload.mission_id,
            payload.context,
            eval_result.correct,
            payload.hints_used,
            q.get('difficulty', 1),
            assessment_result=eval_result,
        )
        db.execute(
            'INSERT INTO attempts(student,mission,context,question_id,correct,'
            'hints_used,time_taken) VALUES(?,?,?,?,?,?,?)',
            (payload.student_id, payload.mission_id, payload.context,
             payload.question_id, int(eval_result.correct), payload.hints_used, payload.time_taken),
        )
        db.commit()

    return {
        'correct': eval_result.correct,
        'xp_earned': xp,
        'mastery': mastery,
        'feedback': eval_result.feedback,
        'source': 'verified',
        'evidence_score': eval_result.evidence_score,
        'performance_factor': eval_result.performance_factor,
        'misconception': eval_result.misconception,
        'objective_id': eval_result.objective_id,
    }
