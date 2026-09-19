# Backend Progress Log — Mars Colony Explorer

Status as of the last merge. Written for the team so everyone can see what
changed, why, and what's still open.

---

## 1. Split the monolith into routers + services

The original `main.py` had all five people's responsibilities in one
250-line file. It's now:

```
backend/
├── main.py          app factory only — CORS, router registration, health check
├── config.py         every env var, read from one place
├── database.py       sqlite connection + schema (+ auto-migration guard)
├── schemas.py         the request/response contract
├── deps.py            auth dependencies
├── routers/            HTTP layer — backend engineer owns this
└── services/           domain logic — one file per person
    ├── ai_agents.py     Person 1 — GenAI / agents
    ├── adaptive.py      Person 2 — mastery scoring / adaptive learning
    ├── curriculum.py    Person 3 — RAG / curriculum content
    └── assessment.py    Person 5 — grading / question validation
```

**Why:** five people editing one file was going to be constant merge
conflicts. Now each person has one file to work in; routers stay thin
(validate → call service → shape response) and never contain domain logic.

**Rule going forward:** only the backend engineer edits `routers/` and
`main.py`. Everyone else works in their `services/*.py` file.

A team-facing `backend/TEAM_README.md` documents this structure, who owns
what, and how to call the API — check there before asking "does this
endpoint exist."

---

## 2. Added authentication and ownership checks

Before this, any caller could submit an assessment or read progress as
*any* `student_id` — no verification at all.

Now:

| Endpoint | Behavior |
|---|---|
| `POST /auth/register` | student_id, display_name, grade_level, password (min 8 chars) → bearer token. Re-registering the same id is `409`, not a silent upsert — it's an account now, not a profile |
| `POST /auth/login` | student_id + password → token |
| `GET /auth/me` | who the token belongs to |
| `GET /students/{id}/progress` | requires a token; `403` if the token's student doesn't match `{id}` |
| `POST /assessment` | requires a token; `403` if the token's student doesn't match the body's `student_id` |
| `POST /student/{id}/predict`, `.../predict/resolve` | same ownership check as progress |

**Implementation notes:**
- Passwords: PBKDF2-HMAC-SHA256, stdlib only (`hashlib`), random salt per user.
- Tokens: HMAC-signed JSON, JWT-*shaped* but not a spec-compliant JWT — no
  new dependency needed for the prototype. Flagged in `services/auth.py`
  for a real JWT library (PyJWT/python-jose) before any public deployment.
- `AUTH_SECRET` must be set in `.env`; if it isn't, the app still runs but
  logs a warning and uses an insecure dev default.
- `/ai/*` routes remain unauthenticated for now (no student-specific
  writes happen there yet) — see Open Items if that changes.

All 8 tests in `test_api.py` passed against this, including a new
`test_login_and_ownership` covering the 401/403 cases directly.

---

## 3. Merged in the GenAI agent system (Person 1's work)

Person 1 built a LangGraph-based multi-agent system independently, against
an earlier (pre-split, pre-auth) version of `main.py`. Merging it in
required reconciling two different architectures, not just resolving text
conflicts. Here's what came in and what changed.

### What Person 1 built (kept as-is, in `backend/agents/`)
- A Supervisor → {Tutor, Scenario, NPC} graph via LangGraph, with one
  `AgentState` flowing through it.
- Structured, validated LLM output: every agent response is a Pydantic
  model (`HintResponse`, `TutorResponse`, `NPCResponse`, `ScenarioResponse`),
  so a malformed response fails validation instead of shipping broken JSON
  to the frontend.
- Two layers of answer-leak protection: a regex validator in the schemas
  (catches "the answer is C", "option B", etc.) plus a content-based check,
  `_contains_correct_answer`, that catches the model stating the right
  answer in its own words.
- Multi-turn memory for NPC dialogue and the new `/ai/ask` endpoint, via
  LangGraph's checkpointer, keyed by a hashed thread ID.
- Full test coverage in `backend/tests/test_agents.py`.
- A provider swap: OpenAI → Groq (`langgraph`, `langchain-groq`,
  `langchain-core`, `groq` in `requirements.txt`; `openai` removed).

### What changed to integrate it into the split + auth structure
- `services/ai_agents.py` rewritten as a thin wrapper around `run_agent()`
  instead of the old direct OpenAI call. `_contains_correct_answer` now
  lives here.
- `routers/ai.py` expanded to 5 endpoints: `dialogue`, `hint`, `explain`,
  `tutor` (alias for `explain`), `ask` (new — free-form tutor Q&A with
  history), `generate-scenario` (new — AI-narrated mission framing).
- `schemas.py`: added `AskTutor`, `ScenarioRequest`, `NpcId`.
- `config.py`: added `MISSION_NPCS` (default crewmate per mission);
  replaced `openai_key()`/`openai_model()` with `groq_key()`.
- `main.py`: health check now reports the Groq provider/key status. Added
  a two-line re-export of `challenge` and `_contains_correct_answer` so
  `tests/test_agents.py`'s `from backend.main import ...` import keeps
  working, even though those functions now live in `services/`.
- **One deliberate behavior change, not yet confirmed with Person 1:**
  their original code raised `503 "agent unavailable"` if the graph
  returned no result. This was changed to fall back to authored content
  instead, matching the "never 500 the student on an AI hiccup" pattern
  used everywhere else. Worth a quick check with them — if the `503` was
  intentional (e.g. so the frontend retries), it should be reverted.
- `test_api.py`: removed the now-dead OpenAI mock test, replaced with a
  lighter check that all five `/ai/*` routes degrade to authored fallback
  when no `GROQ_API_KEY` is set.

### Environment change
`GROQ_API_KEY` is now what matters for AI features; `OPENAI_API_KEY` is no
longer read anywhere. Everyone's `.env` needs updating.

---

## 4. Current state of the database schema

Mastery is tracked per `(student, mission, context)`, not just per
`(student, mission)` — this is what lets `/assessment` detect "solved it
numerically, failed it on transfer," the core differentiator called out in
the design doc. `transfer_gaps` in `GET /students/{id}/progress` flags any
mission where the score spread across contexts crosses a threshold.

Still SQLite, single-file, no migrations tool. This is fine for the
classroom prototype but is called out below as the next real piece of work.

---

## 5. What's tested right now

- `test_api.py` (8 tests): registration/login, ownership checks (401/403),
  per-context mastery, transfer-gap detection, the prediction mechanic,
  private-answer stripping, AI-route fallback behavior with no key set.
- `backend/tests/test_agents.py` (Person 1's suite): supervisor routing,
  answer-leak rejection at the schema level, structured-output mocking,
  provider-failure fallback, multi-turn history persistence, NPC persona
  distinctness.

Both suites need `pip install -r requirements.txt` (now includes
`langgraph`/`langchain-groq`/`groq`) before they'll collect — confirmed
locally that they fail to import until those are installed, which is
expected, not a bug.

---

## 6. Open items / not done yet

- **Postgres migration.** Still SQLite. Needed before more than one person
  can hit the same live backend reliably.
- **Rate limiting on `/ai/*`.** Nothing currently stops one runaway loop
  from burning through the Groq key.
- **`GET /student/{id}/next-challenge`.** Stubbed in
  `services/adaptive.py` (`NotImplementedError`) — Person 2's next task.
  The Scenario agent already has a `difficulty_hint` field waiting for it.
- **`services/assessment.validate_question`.** Also stubbed — Person 5's
  task, for validating LLM-generated questions before they reach a student.
- **`/ai/*` routes are still unauthenticated.** Fine today since they don't
  write student-specific data, but if that changes (e.g. persisting
  conversation history per student in the DB instead of just in the
  in-memory checkpointer), they need the same ownership check as
  `/assessment`.
- **Confirm the 503→fallback change** with Person 1 (see section 3).
- **Real JWT library** before any public deployment — current tokens are
  HMAC-signed JSON, not spec-compliant JWTs, which is fine for a single
  trusted backend but should be swapped out (see `services/auth.py`).
