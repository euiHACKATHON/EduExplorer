import pytest
import uuid
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.adaptive import student_state, update_mastery


def test_student_state_is_empty_for_new_student():
    from backend.database import connect

    with connect() as db:
        assert student_state(db, "new-student") == []


def test_mastery_updates_with_recency():
    from backend.database import connect

    with connect() as db:
        xp, score1 = update_mastery(
            db,
            "adaptive-test",
            "M001",
            "numerical",
            True,
            0,
            5,
        )

        assert xp == 100
        assert score1 == pytest.approx(0.2)

        xp, score2 = update_mastery(
            db,
            "adaptive-test",
            "M001",
            "numerical",
            True,
            0,
            5,
        )

        assert xp == 0
        assert score2 == pytest.approx(0.36)

        xp, score3 = update_mastery(
            db,
            "adaptive-test",
            "M001",
            "numerical",
            False,
            0,
            5,
        )

        assert xp == 0
        assert score3 == pytest.approx(0.308)


def test_harder_correct_answer_gives_stronger_evidence():
    from backend.database import connect

    with connect() as db:
        _, easy_score = update_mastery(
            db, "easy-test", "M001", "numerical", True, 0, 1
        )
        _, hard_score = update_mastery(
            db, "hard-test", "M001", "numerical", True, 0, 5
        )

        assert easy_score == pytest.approx(0.16)
        assert hard_score == pytest.approx(0.20)
        assert hard_score > easy_score


def test_student_state_returns_current_difficulty():
    from backend.database import connect

    with connect() as db:
        update_mastery(
            db,
            "difficulty-test",
            "M001",
            "numerical",
            True,
            0,
            4,
        )

        state = student_state(db, "difficulty-test")

        assert len(state) == 1
        assert state[0]["current_difficulty"] == 4


def test_next_challenge_targets_weakest_area():
    from backend.database import connect
    from backend.services.adaptive import next_challenge

    with connect() as db:
        update_mastery(
            db, "recommendation-test", "M001", "numerical", True, 0, 3
        )
        update_mastery(
            db, "recommendation-test", "M002", "real_world", False, 0, 2
        )

        recommendation = next_challenge(db, "recommendation-test")

        assert recommendation["mission_id"] == "M002"
        assert recommendation["context"] == "real_world"
        assert recommendation["difficulty"] == 1


def test_next_challenge_increases_difficulty_when_mastery_is_strong():
    from backend.database import connect
    from backend.services.adaptive import next_challenge

    with connect() as db:
        update_mastery(
            db, "strong-test", "M001", "numerical", True, 0, 5
        )

        # Move mastery above 0.80 through repeated strong evidence.
        for _ in range(12):
            update_mastery(
                db, "strong-test", "M001", "numerical", True, 0, 5
            )

        recommendation = next_challenge(db, "strong-test")

        assert recommendation["mission_id"] == "M001"
        assert recommendation["difficulty"] == 5
        assert "advanced" in recommendation["reason"].lower()


def test_adaptive_student_endpoint_requires_authentication():
    client = TestClient(app)

    response = client.get("/adaptive/student/test-student")

    assert response.status_code in (401, 403)


def test_adaptive_next_endpoint_requires_authentication():
    client = TestClient(app)

    response = client.get("/adaptive/next/test-student")

    assert response.status_code in (401, 403)


def test_adaptive_api_returns_student_state_and_next_challenge():
    import uuid
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    student_id = f"api-adaptive-{uuid.uuid4().hex[:8]}"

    registration = client.post(
        "/auth/register",
        json={
            "student_id": student_id,
            "display_name": "Adaptive Test",
            "grade_level": "12",
            "password": "test-password-123",
        },
    )

    assert registration.status_code == 200

    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    state_response = client.get(
        f"/adaptive/student/{student_id}",
        headers=headers,
    )

    assert state_response.status_code == 200
    assert state_response.json() == {
        "student_id": student_id,
        "state": [],
    }

    next_response = client.get(
        f"/adaptive/next/{student_id}",
        headers=headers,
    )

    assert next_response.status_code == 200

    recommendation = next_response.json()

    assert recommendation["mission_id"] == "M001"
    assert recommendation["objective_id"] == "newtons_second_law"
    assert recommendation["context"] == "numerical"
    assert recommendation["difficulty"] == 1
    assert recommendation["activity_type"] == "calculation"
    assert "reason" in recommendation


def test_assessment_updates_adaptive_state():
    import uuid
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    student_id = f"assessment-adaptive-{uuid.uuid4().hex[:8]}"

    registration = client.post(
        "/auth/register",
        json={
            "student_id": student_id,
            "display_name": "Assessment Adaptive Test",
            "grade_level": "12",
            "password": "test-password-123",
        },
    )

    assert registration.status_code == 200

    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assessment = client.post(
        "/assessment",
        headers=headers,
        json={
            "student_id": student_id,
            "mission_id": "M001",
            "question_id": "Q001",
            "answer": "C",
            "time_taken": 18,
            "hints_used": 0,
            "context": "numerical",
        },
    )

    assert assessment.status_code == 200

    state_response = client.get(
        f"/adaptive/student/{student_id}",
        headers=headers,
    )

    assert state_response.status_code == 200

    state = state_response.json()["state"]

    assert len(state) == 1
    assert state[0]["mission_id"] == "M001"
    assert state[0]["context"] == "numerical"
    assert state[0]["attempts"] == 1
    assert state[0]["correct"] == 1
    assert state[0]["mastery"] > 0
    assert state[0]["current_difficulty"] == 2


def test_recent_failures_trigger_review():
    from backend.database import connect
    from backend.services.adaptive import next_challenge, update_mastery

    with connect() as db:
        student = "recent-failure-test"

        # Build strong mastery.
        for _ in range(12):
            update_mastery(
                db, student, "M001", "numerical", True, 0, 5
            )

        # Record recent failures directly in the attempt history.
        db.executemany(
            """
            INSERT INTO attempts(
                student, mission, context, question_id,
                correct, hints_used, time_taken
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (student, "M001", "numerical", "Q001", 0, 0, 30),
                (student, "M001", "numerical", "Q001", 0, 0, 35),
            ],
        )

        recommendation = next_challenge(db, student)

        assert recommendation["mission_id"] == "M001"
        assert recommendation["difficulty"] <= 3
        assert "review" in recommendation["reason"].lower()


def test_recommendation_includes_skills():
    import uuid
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    student_id = f"skills-test-{uuid.uuid4().hex[:8]}"

    registration = client.post(
        "/auth/register",
        json={
            "student_id": student_id,
            "display_name": "Skills Test",
            "grade_level": "12",
            "password": "test-password-123",
        },
    )
    assert registration.status_code == 200

    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        f"/adaptive/next/{student_id}",
        headers=headers,
    )

    assert response.status_code == 200
    recommendation = response.json()

    assert recommendation["objective_id"] == "newtons_second_law"
    assert recommendation["skills"] == ["calculation"]


def test_hint_decision_escalates_for_repeated_failures():
    from backend.database import connect
    from backend.services.adaptive import hint_level

    with connect() as db:
        student = "hint-test"

        db.executemany(
            """
            INSERT INTO attempts(
                student, mission, context, question_id,
                correct, hints_used, time_taken
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (student, "M001", "numerical", "Q001", 0, 0, 30),
                (student, "M001", "numerical", "Q001", 0, 1, 40),
            ],
        )

        assert hint_level(
            db,
            student,
            "M001",
            "numerical",
            time_seconds=20,
            explicit_request=False,
        ) == 2


def test_hint_decision_escalates_to_worked_example():
    from backend.database import connect
    from backend.services.adaptive import hint_level

    with connect() as db:
        student = "hint-level-3-test"

        db.executemany(
            """
            INSERT INTO attempts(
                student, mission, context, question_id,
                correct, hints_used, time_taken
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (student, "M001", "numerical", "Q001", 0, 2, 30),
                (student, "M001", "numerical", "Q001", 0, 2, 40),
                (student, "M001", "numerical", "Q001", 0, 2, 50),
            ],
        )

        assert hint_level(
            db,
            student,
            "M001",
            "numerical",
            time_seconds=20,
            explicit_request=False,
        ) == 3


def test_explicit_hint_request_returns_first_hint():
    from backend.database import connect
    from backend.services.adaptive import hint_level

    with connect() as db:
        assert hint_level(
            db,
            "explicit-hint-test",
            "M001",
            "numerical",
            time_seconds=5,
            explicit_request=True,
        ) == 1


def test_hint_endpoint_uses_adaptive_hint_level(monkeypatch):
    import uuid
    from fastapi.testclient import TestClient
    from backend.database import connect
    from backend.main import app

    captured = {}

    async def fake_hint(mission_id, question_id, student_id, level, raw_challenge):
        captured["level"] = level
        return {"level": level}

    monkeypatch.setattr(
        "backend.routers.ai.ai_agents.hint",
        fake_hint,
    )

    client = TestClient(app)
    student_id = f"hint-api-{uuid.uuid4().hex[:8]}"

    registration = client.post(
        "/auth/register",
        json={
            "student_id": student_id,
            "display_name": "Hint API Test",
            "grade_level": "12",
            "password": "test-password-123",
        },
    )
    assert registration.status_code == 200

    token = registration.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with connect() as db:
        db.executemany(
            """
            INSERT INTO attempts(
                student, mission, context, question_id,
                correct, hints_used, time_taken
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (student_id, "M001", "numerical", "Q001", 0, 0, 30),
                (student_id, "M001", "numerical", "Q001", 0, 0, 40),
            ],
        )
        db.commit()

    response = client.post(
        "/ai/hint",
        headers=headers,
        json={
            "mission_id": "M001",
            "question_id": "Q001",
            "student_id": student_id,
            "level": 1,
        },
    )

    assert response.status_code == 200
    assert captured["level"] == 2