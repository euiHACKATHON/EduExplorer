import os
import tempfile

os.environ["MARS_DB"] = os.path.join(tempfile.mkdtemp(), "test.sqlite3")
os.environ["GROQ_API_KEY"] = ""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_reports_groq_configuration():
    result = client.get("/health").json()
    assert result == {"status": "ok", "ai_available": False, "provider": "groq"}


def test_assessment_and_progress():
    payload = dict(student_id="test-cadet", mission_id="M001", question_id="Q001", answer="A", time_taken=18, hints_used=1)
    assert client.post("/assessment", json=payload).json()["correct"] is False
    payload["answer"] = "C"
    result = client.post("/assessment", json=payload).json()
    assert result["correct"] is True and result["xp_earned"] == 85
    assert client.post("/assessment", json=payload).json()["xp_earned"] == 0
    progress = client.get("/students/test-cadet/progress").json()
    assert progress["xp"] == 85 and progress["completed"] == ["M001"]
    payload["question_id"] = "wrong"
    assert client.post("/assessment", json=payload).status_code == 400


def test_validation_and_private_answer():
    question = client.get("/challenges/M001").json()
    assert all(key not in question for key in ("answer", "explanation", "hints"))
    assert client.get("/challenges/M999").status_code == 404
    assert client.get("/ai/dialogue?npc_id=unknown").status_code == 404
    invalid = dict(mission_id="M001", question_id="Q001", student_id="test", level=4)
    assert client.post("/ai/hint", json=invalid).status_code == 422


def test_all_ai_routes_have_safe_offline_fallbacks():
    dialogue = client.get("/ai/dialogue?npc_id=scientist_01&student_id=test").json()
    assert dialogue["source"] == "authored-fallback" and len(dialogue["options"]) == 2
    hint = client.post("/ai/hint", json=dict(mission_id="M002", question_id="Q002", student_id="test", level=2)).json()
    assert hint["source"] == "authored-fallback" and "200" in hint["hint"]
    explanation = client.post("/ai/explain", json={"mission_id": "M002"}).json()
    tutor_alias = client.post("/ai/tutor", json={"mission_id": "M002"}).json()
    assert explanation["source"] == "authored-fallback" and tutor_alias == explanation
    scenario = client.post("/ai/generate-scenario", json={"mission_id": "M003", "student_id": "test", "difficulty": 3}).json()
    assert scenario["source"] == "authored-fallback"
    assert scenario["mission_id"] == "M003" and scenario["difficulty"] == 3
    assert scenario["npc_id"] == "botanist_01"


def test_scenario_route_rejects_generated_correct_answer(monkeypatch):
    import backend.main as module
    from backend.agents.schemas import ScenarioResponse

    async def leaking_agent(state, thread_id):
        state["scenario_result"] = ScenarioResponse(
            mission_id="M001",
            mission_title="The 2,000 N Rescue",
            objective="Save the rover.",
            difficulty=2,
            npc_id="scientist_01",
            source="ai",
        )
        return state

    monkeypatch.setattr(module, "run_agent", leaking_agent)
    result = client.post("/ai/generate-scenario", json={"mission_id": "M001"}).json()
    assert result["source"] == "authored-fallback"
    assert "2,000" not in result["mission_title"]
