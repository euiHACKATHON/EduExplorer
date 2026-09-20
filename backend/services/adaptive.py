"""Student model, mastery scoring, transfer-gap detection.
OWNER: Person 2 (Adaptive Learning).

Deliberately simple additive rule-based scoring per the "start simple" MVP
guidance. Swap for BKT / knowledge tracing / IRT later without touching the
API shape: keep `update_mastery` returning (xp, score).

`next_challenge` is the stub Person 2 fills in next -- this is the single
most important unfinished piece of the MVP (design doc success criterion
#6: "the next challenge changes according to the student's demonstrated
understanding"). Nothing else calls this yet; once it's implemented, tell
the backend engineer and a GET /student/{id}/next-challenge route gets
added to wire it in.
"""
from ..config import TRANSFER_GAP_THRESHOLD
from .curriculum import challenge


def level_for_score(score: float) -> str:
    if score >= 0.7:
        return 'mastered'
    if score >= 0.4:
        return 'developing'
    return 'weak'


def update_mastery(
    db,
    student: str,
    mission: str,
    context: str,
    correct: bool,
    hints_used: int,
    difficulty: int = 1,
    assessment_result=None,
) -> tuple[int, float]:
    """Update mastery using a recency-weighted evidence model.

    Correct answers increase mastery; incorrect answers decrease it.
    Difficulty is currently inferred from the available game context and
    will be made explicit when the curriculum exposes difficulty metadata.

    The caller owns the surrounding transaction and commit.
    """
    previous = db.execute(
        'SELECT xp, score, attempts FROM mastery '
        'WHERE student=? AND mission=? AND context=?',
        (student, mission, context),
    ).fetchone()

    old_score = previous[1] if previous else 0.0
    already_completed = bool(previous and previous[0] > 0)

    # Use evidence score provided by Person 5's AssessmentResult if available,
    # otherwise compute base evidence score.
    if assessment_result is not None and hasattr(assessment_result, 'evidence_score'):
        evidence = assessment_result.evidence_score
    elif correct:
        difficulty_weight = 0.8 + (difficulty - 1) * 0.05
        evidence = min(
            1.0,
            max(0.6, difficulty_weight - 0.15 * hints_used),
        )
    else:
        evidence = max(0.0, 0.2 - (difficulty - 1) * 0.025)

    # Recency/update rate.
    alpha = 0.20

    new_score = (1 - alpha) * old_score + alpha * evidence
    new_score = max(0.0, min(1.0, new_score))

    # XP remains separate from mastery.
    xp = max(50, 100 - 15 * hints_used) if correct and not already_completed else 0

    db.execute(
        'INSERT INTO mastery('
        'student,mission,context,xp,score,attempts,difficulty'
        ') VALUES(?,?,?,?,?,?,?) '
        'ON CONFLICT(student,mission,context) DO UPDATE SET '
        'xp=MAX(mastery.xp,excluded.xp), '
        'score=excluded.score, '
        'attempts=mastery.attempts+1, '
        'difficulty=excluded.difficulty',
        (student, mission, context, xp, new_score, 1, difficulty),
    )

    return xp, new_score


def student_state(db, student: str) -> list[dict]:
    """Return the adaptive learning state for each mission/context.

    The state is derived from the mastery table and attempt history so the
    adaptive engine has both current mastery and supporting evidence.
    """
    rows = db.execute(
        """
        SELECT
            m.mission,
            m.context,
            m.score,
            m.attempts,
            m.difficulty,
            COALESCE(SUM(a.correct), 0) AS correct,
            COALESCE(SUM(a.hints_used), 0) AS hints_used,
            MAX(a.created_at) AS last_attempt
        FROM mastery AS m
        LEFT JOIN attempts AS a
            ON a.student = m.student
            AND a.mission = m.mission
            AND a.context = m.context
        WHERE m.student = ?
        GROUP BY m.mission, m.context
        ORDER BY m.mission, m.context
        """,
        (student,),
    ).fetchall()

    return [
        {
            'mission_id': mission,
            'context': context,
            'mastery': score,
            'attempts': attempts,
            'correct': correct,
            'hints_used': hints_used,
            'last_attempt': last_attempt,
            'current_difficulty': difficulty,
        }
        for (
            mission,
            context,
            score,
            attempts,
            difficulty,
            correct,
            hints_used,
            last_attempt,
        ) in rows
    ]


def transfer_gaps(rows) -> list[str]:
    """rows: iterable of (mission, context, score). Flags missions where the
    score spread across contexts suggests memorization without transfer."""
    by_mission: dict[str, list[float]] = {}
    for mission, _context, score in rows:
        by_mission.setdefault(mission, []).append(score)
    return [
        m for m, scores in by_mission.items()
        if len(scores) >= 2 and max(scores) - min(scores) >= TRANSFER_GAP_THRESHOLD
    ]


def build_progress(rows) -> dict:
    """rows: iterable of (mission, context, xp, score)."""
    mastery_by_mission: dict[str, dict] = {}
    for mission, ctx, _xp, score in rows:
        mastery_by_mission.setdefault(mission, {})[ctx] = {
            'score': score,
            'level': level_for_score(score),
        }
    return {
        'xp': sum(r[2] for r in rows),
        'completed': sorted({r[0] for r in rows if r[2] > 0}),
        'mastery': mastery_by_mission,
        'transfer_gaps': transfer_gaps([(r[0], r[1], r[3]) for r in rows]),
    }


def hint_level(
    db,
    student_id: str,
    mission: str,
    context: str,
    time_seconds: float,
    explicit_request: bool = False,
) -> int:
    """Choose a hint level from recent performance and time spent."""
    recent_failures = db.execute(
        """
        SELECT correct
        FROM attempts
        WHERE student = ?
          AND mission = ?
          AND context = ?
        ORDER BY id DESC
        LIMIT 3
        """,
        (student_id, mission, context),
    ).fetchall()

    failure_count = sum(
        1 for (correct,) in recent_failures if not correct
    )

    if failure_count >= 3:
        return 3

    if failure_count >= 2:
        return 2

    if explicit_request:
        return 1

    if time_seconds > 60:
        return 1

    return 0


def next_challenge(db, student_id: str) -> dict:
    """Choose the next learning activity from the student's current state."""
    states = student_state(db, student_id)

    if not states:
        curriculum = challenge('M001')
        return {
    'mission_id': 'M001',
    'objective_id': curriculum.get('objective_id'),
    'context': 'numerical',
    'difficulty': 1,
    'activity_type': curriculum.get('activity_type', 'calculation'),
    'skills': curriculum.get('skills', []),
    'reason': 'Start with a foundational numerical activity.',
}
    # Focus on the weakest known learning area.
    weakest = min(states, key=lambda item: item['mastery'])
    curriculum = challenge(weakest['mission_id'])
    recent_failures = db.execute(
        """
        SELECT correct
        FROM attempts
        WHERE student = ?
          AND mission = ?
          AND context = ?
        ORDER BY id DESC
        LIMIT 3
        """,
        (
            student_id,
            weakest['mission_id'],
            weakest['context'],
        ),
    ).fetchall()

    recent_failure_count = sum(
        1 for (correct,) in recent_failures if not correct
    )


    mastery = weakest['mastery']
    current_difficulty = weakest['current_difficulty']

    if recent_failure_count >= 2:
        difficulty = min(3, max(1, current_difficulty))
        reason = 'Recent failures were detected, so a review activity is recommended.'
    elif mastery < 0.40:
        difficulty = max(1, current_difficulty - 1)
        reason = 'Mastery is weak, so a remedial activity is recommended.'
    elif mastery < 0.60:
        difficulty = min(5, max(1, current_difficulty))
        reason = 'Mastery is developing, so continue with an accessible activity.'
    elif mastery < 0.80:
        difficulty = min(5, current_difficulty + 1)
        reason = 'Mastery is moderate, so increase the challenge.'
    else:
        difficulty = min(5, current_difficulty + 1)
        reason = 'Mastery is strong, so an advanced activity is recommended.'

    return {
    'mission_id': weakest['mission_id'],
    'objective_id': curriculum.get('objective_id'),
    'context': weakest['context'],
    'difficulty': difficulty,
    'activity_type': curriculum.get('activity_type', 'calculation'),
    'skills': curriculum.get('skills', []),
    'reason': reason,
}
