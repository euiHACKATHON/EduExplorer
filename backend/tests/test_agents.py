import asyncio
import uuid

import pytest
from pydantic import ValidationError

from backend.agents import npc_agent, scenario_agent, tutor_agent
from backend.agents.graph import run_agent
from backend.agents.schemas import DialogueOption, HintResponse, lesson_facts_from_challenge
from backend.agents.state import new_state
from backend.agents.supervisor import route_request
from backend.main import _contains_correct_answer, challenge


def facts(mission_id="M001"):
    return lesson_facts_from_challenge(challenge(mission_id))


class FakeStructuredModel:
    def __init__(self, schema, values=None, error=None, captured=None):
        self.schema, self.values, self.error, self.captured = schema, values or {}, error, captured

    async def ainvoke(self, messages):
        if self.captured is not None:
            self.captured.extend(messages)
        if self.error:
            raise self.error
        return self.schema(**self.values[self.schema.__name__])


class FakeModel:
    def __init__(self, values=None, error=None, captured=None):
        self.values, self.error, self.captured = values, error, captured

    def with_structured_output(self, schema):
        return FakeStructuredModel(schema, self.values, self.error, self.captured)


def test_supervisor_routes_every_request_type():
    assert route_request({"request_type": "dialogue"}) == "npc"
    assert route_request({"request_type": "hint"}) == "tutor"
    assert route_request({"request_type": "explain"}) == "tutor"
    assert route_request({"request_type": "ask"}) == "tutor"
    assert route_request({"request_type": "scenario"}) == "scenario"
    with pytest.raises(ValueError):
        route_request({"request_type": "invalid"})


@pytest.mark.parametrize("leak", ["The answer is C", "Choose option C", "C) is correct", "Correct choice: C"])
def test_hint_schema_rejects_answer_key_leaks(leak):
    with pytest.raises(ValidationError):
        HintResponse(hint=leak, source="ai", level=1)


def test_post_generation_guard_detects_correct_option_text():
    raw = challenge("M001")
    assert _contains_correct_answer("The rover needs 2,000 N.", raw)
    assert not _contains_correct_answer("Multiply mass by acceleration.", raw)


def test_tutor_agents_use_structured_output(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    model = FakeModel(values={"_HintDraft": {"hint": "Use the force relationship, then multiply."}, "_ExplainDraft": {"message": "Force changes how a rover moves."}, "_AskDraft": {"message": "Mass measures how much matter the rover contains."}})
    monkeypatch.setattr(tutor_agent, "_get_llm", lambda: model)
    hint = asyncio.run(tutor_agent.generate_hint(facts(), 1))
    explanation = asyncio.run(tutor_agent.generate_explanation(facts()))
    answer = asyncio.run(tutor_agent.answer_lesson_question(facts(), "What is mass?", []))
    assert hint.source == "ai" and hint.level == 1
    assert explanation.source == "ai"
    assert answer.source == "ai" and "Mass" in answer.message


def test_graph_restores_tutor_chat_history(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    thread_id = f"ask-{uuid.uuid4()}"

    def state(message):
        return new_state(
            "ask",
            "cadet",
            mission_id="M001",
            lesson_facts=facts(),
            user_message=message,
        )

    first = asyncio.run(run_agent(state("What is force?"), thread_id))
    second = asyncio.run(run_agent(state("How does mass change it?"), thread_id))
    assert len(first["conversation_history"]) == 2
    assert len(second["conversation_history"]) == 4


def test_rate_limit_or_provider_error_returns_authored_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(tutor_agent, "_get_llm", lambda: FakeModel(error=RuntimeError("429 rate limit")))
    result = asyncio.run(tutor_agent.generate_hint(facts(), 2))
    assert result.source == "authored-fallback" and result.hint == facts().hints[1]


def test_scenario_prompt_never_contains_question_or_correct_answer(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    captured = []
    model = FakeModel(values={"_ScenarioDraft": {"mission_title": "Rover Rescue", "objective": "Restore the stranded rover before nightfall."}}, captured=captured)
    monkeypatch.setattr(scenario_agent, "_get_llm", lambda: model)
    result = asyncio.run(scenario_agent.generate_scenario(facts(), "scientist_01", 2))
    prompt = "\n".join(content for _, content in captured)
    assert result.source == "ai"
    assert facts().question not in prompt and "2,000 N" not in prompt


def test_npc_personas_are_distinct_and_actions_stay_authored(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    options = [DialogueOption(text="Begin", action="START_CHALLENGE", payload="M001")]
    scientist = asyncio.run(npc_agent.generate_npc_response("scientist_01", facts(), options, []))
    engineer = asyncio.run(npc_agent.generate_npc_response("engineer_01", facts(), options, []))
    assert scientist.message != engineer.message
    assert scientist.options == options == engineer.options


def test_npc_agent_uses_structured_output_and_preserves_actions(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    model = FakeModel(values={"_NPCDraft": {"message": "Rover Beta needs a careful physics check, cadet."}})
    monkeypatch.setattr(npc_agent, "_get_llm", lambda: model)
    options = [DialogueOption(text="Begin", action="START_CHALLENGE", payload="M001")]
    response = asyncio.run(npc_agent.generate_npc_response("scientist_01", facts(), options, []))
    assert response.source == "ai"
    assert response.npc_name == "Dr. Sara"
    assert response.options == options


def test_graph_restores_dialogue_history_for_same_session(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    thread_id = f"test-{uuid.uuid4()}"
    options = [DialogueOption(text="Begin", action="START_CHALLENGE", payload="M001")]

    def state():
        return new_state("dialogue", "cadet", mission_id="M001", npc_id="scientist_01", lesson_facts=facts(), npc_options=options)

    first = asyncio.run(run_agent(state(), thread_id))
    second = asyncio.run(run_agent(state(), thread_id))
    assert len(first["conversation_history"]) == 1
    assert len(second["conversation_history"]) == 2
