# Agent integration points

The FastAPI routes call `graph.run_agent()`, which sends a validated `AgentState`
through a LangGraph supervisor to exactly one specialist node.

- **Curriculum/RAG (Person 3):** populate `AgentState.retrieved_context` before
  invoking the graph. `lesson_facts` is currently built from reviewed static JSON
  and deliberately excludes answer keys and answer choices.
- **Mastery/adaptation (Person 2):** provide a difficulty bucket through
  `AgentState.difficulty_hint`. The scenario route currently accepts a validated
  `difficulty` value from 1 to 3 and defaults to 2.
- **Question validation (Person 5):** authored questions and deterministic grading
  remain in `main.py` and `public/mock`. Scenario generation never creates or edits
  graded content; the shared boundary is `mission_id`.
- **Authentication/API ownership (Person 4):** existing route response shapes are
  unchanged. Authentication and rate limiting can wrap the FastAPI routes without
  modifying agent nodes.

`MemorySaver` is keyed with a hashed student/NPC thread identifier. It retains the
last 12 NPC messages during the process lifetime. Replace it with a persistent
checkpointer before multi-instance or production deployment.

All provider calls fail closed to authored content. The API performs an additional
post-generation comparison against the correct answer text without putting that
answer into model context.
