import pytest

from backend.database import connect, init_db
from backend.services.adaptive import update_mastery


@pytest.fixture
def db():
    init_db()
    with connect() as connection:
        yield connection


def simulate_student(db, student_id, interactions):
    scores = []

    for interaction in interactions:
        _, score = update_mastery(
            db,
            student_id,
            interaction["mission"],
            interaction["context"],
            interaction["correct"],
            interaction["hints"],
            interaction["difficulty"],
        )
        scores.append(score)

    return scores


def test_fast_student_improves_with_correct_answers(db):
    scores = simulate_student(
        db,
        "eval-fast",
        [
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 1,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 2,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 3,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 4,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 5,
            },
        ],
    )

    assert scores[-1] > scores[0]
    assert scores[-1] > 0.5


def test_struggling_student_stays_low(db):
    scores = simulate_student(
        db,
        "eval-struggling",
        [
            {
                "mission": "M001",
                "context": "numerical",
                "correct": False,
                "hints": 1,
                "difficulty": 3,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": False,
                "hints": 1,
                "difficulty": 2,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": False,
                "hints": 2,
                "difficulty": 2,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": False,
                "hints": 2,
                "difficulty": 1,
            },
        ],
    )

    assert scores[-1] < 0.4


def test_harder_questions_provide_stronger_evidence(db):
    easy_scores = simulate_student(
        db,
        "eval-easy",
        [
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 1,
            },
        ],
    )

    hard_scores = simulate_student(
        db,
        "eval-hard",
        [
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 5,
            },
        ],
    )

    assert hard_scores[-1] > easy_scores[-1]


def test_inconsistent_student_does_not_look_mastered(db):
    scores = simulate_student(
        db,
        "eval-inconsistent",
        [
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 0,
                "difficulty": 2,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": False,
                "hints": 1,
                "difficulty": 2,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": True,
                "hints": 1,
                "difficulty": 3,
            },
            {
                "mission": "M001",
                "context": "numerical",
                "correct": False,
                "hints": 1,
                "difficulty": 3,
            },
        ],
    )

    assert scores[-1] < 0.7


from backend.services.adaptive import next_challenge


def test_struggling_student_gets_review_recommendation(db):
    student_id = "eval-review"

    for _ in range(3):
        update_mastery(
            db,
            student_id,
            "M001",
            "numerical",
            False,
            1,
            2,
        )

        db.execute(
            """
            INSERT INTO attempts(
                student, mission, context, question_id,
                correct, hints_used, time_taken
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (student_id, "M001", "numerical", "Q001", 0, 1, 40),
        )

    db.commit()

    recommendation = next_challenge(db, student_id)

    assert recommendation["mission_id"] == "M001"
    assert recommendation["difficulty"] <= 2
    assert "review" in recommendation["reason"].lower()


def test_strong_student_gets_harder_recommendation(db):
    student_id = "eval-strong"

    for difficulty in [1, 2, 3, 4, 5]:
        update_mastery(
            db,
            student_id,
            "M001",
            "numerical",
            True,
            0,
            difficulty,
        )

    recommendation = next_challenge(db, student_id)

    assert recommendation["mission_id"] == "M001"
    assert recommendation["difficulty"] > 1
    assert "increase the challenge" in recommendation["reason"].lower()


def test_new_student_gets_foundational_activity(db):
    recommendation = next_challenge(db, "eval-new")

    assert recommendation["mission_id"] == "M001"
    assert recommendation["objective_id"] == "newtons_second_law"
    assert recommendation["difficulty"] == 1
    assert recommendation["activity_type"] == "calculation"
    assert recommendation["skills"] == ["calculation"]


def test_student_progression_adapts_after_improvement(db):
    student_id = "eval-recovery"

    # Student starts by struggling.
    for _ in range(4):
        update_mastery(
            db,
            student_id,
            "M001",
            "numerical",
            False,
            1,
            1,
        )

    weak_recommendation = next_challenge(db, student_id)

    assert weak_recommendation["difficulty"] == 1

    # Student then improves with several successful attempts.
    for difficulty in [1, 2, 3, 4, 5, 5, 5, 5]:
        update_mastery(
            db,
            student_id,
            "M001",
            "numerical",
            True,
            0,
            difficulty,
        )

    improved_recommendation = next_challenge(db, student_id)

    assert improved_recommendation["difficulty"] > weak_recommendation["difficulty"]