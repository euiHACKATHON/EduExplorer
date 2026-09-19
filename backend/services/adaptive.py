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


def level_for_score(score: float) -> str:
    if score >= 0.7:
        return 'mastered'
    if score >= 0.4:
        return 'developing'
    return 'weak'


def update_mastery(
    db, student: str, mission: str, context: str, correct: bool, hints_used: int
) -> tuple[int, float]:
    """Shared scoring path for both /assessment and resolved predictions.

    The caller owns the surrounding transaction and the commit.
    """
    previous = db.execute(
        'SELECT xp,score FROM mastery WHERE student=? AND mission=? AND context=?',
        (student, mission, context),
    ).fetchone()
    already = bool(previous and previous[0] > 0)
    xp = max(50, 100 - 15 * hints_used) if correct and not already else 0
    score = max(
        previous[1] if previous else 0,
        max(.6, 1 - .15 * hints_used) if correct else .2,
    )
    db.execute(
        'INSERT INTO mastery(student,mission,context,xp,score,attempts) VALUES(?,?,?,?,?,1) '
        'ON CONFLICT(student,mission,context) DO UPDATE SET '
        'xp=MAX(mastery.xp,excluded.xp), score=MAX(mastery.score,excluded.score), '
        'attempts=mastery.attempts+1',
        (student, mission, context, xp, score),
    )
    return xp, score


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


def next_challenge(db, student_id: str) -> dict:
    """What should this student attempt next?

    Expected shape: {'mission_id': str, 'context': str, 'difficulty': int,
                     'reason': str}

    Starting point: read this student's mastery rows (same query as
    build_progress), pick the lowest-scoring (mission, context) pair they
    haven't mastered yet, and default to 'numerical' context for anything
    they haven't attempted at all. Rule-based is fine for a first pass --
    same "start simple" guidance as update_mastery above.
    """
    raise NotImplementedError('Person 2: adaptive challenge selection')
