"""Game progression -- levels and badges.  OWNER: Person 5
(Assessment / Validation / Progression, per the team plan) -- the backend
engineer builds the storage/endpoint plumbing (routers/students.py), Person
5 owns tuning the actual rules below.

Deliberately derived from existing mastery/attempts rows rather than a new
"awarded badges" table: fewer places state can drift out of sync, at the
cost of recomputing on every request. Fine at this scale. If badges ever
need something that isn't derivable from stored data (e.g. a one-time
"first login" badge with no data trail), that's when a real badges table
earns its keep.

LEVEL_XP_STEP and the badge rules in compute_badges are placeholders, same
spirit as adaptive.next_challenge -- the first thing to replace once
Person 5 has real design opinions about what should be rewarded.
"""
LEVEL_XP_STEP = 200  # flat: every 200 total xp is a new level


def level_for_xp(total_xp: int) -> int:
    return 1 + total_xp // LEVEL_XP_STEP


def compute_badges(mastery_rows, attempt_rows) -> list[str]:
    """mastery_rows: iterable of (mission, context, xp, score).
    attempt_rows: iterable of (mission, context, correct, hints_used)."""
    badges = []
    if any(xp > 0 for _mission, _context, xp, _score in mastery_rows):
        badges.append('first_mission_complete')
    if any(correct and hints_used == 0 for _m, _c, correct, hints_used in attempt_rows):
        badges.append('no_hints_win')
    if any(context == 'transfer' and score >= 0.7 for _m, context, _xp, score in mastery_rows):
        badges.append('transfer_master')
    return badges
