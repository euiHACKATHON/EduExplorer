# Backend — how this is organized

Read this before you touch anything in `backend/`. It tells you where your
code goes, what you can rely on staying stable, and how to call the API
from your own module or from Replit.

## Folder map

```
backend/
├── main.py          app factory only — do not add logic here
├── config.py         all env vars, read from here, not os.getenv() directly
├── database.py       sqlite connection + schema
├── schemas.py        the request/response contract — see below
├── deps.py            auth dependencies (get_current_student, require_self)
├── routers/           HTTP layer — backend engineer only
└── services/          YOUR CODE GOES HERE
    ├── ai_agents.py    Person 1 — GenAI / agents
    ├── adaptive.py     Person 2 — adaptive learning / mastery
    ├── curriculum.py   Person 3 — RAG / curriculum
    └── assessment.py   Person 5 — grading / question validation
```

**Rule: only edit your file in `services/`.** Routers and `main.py` are
mine — if you need a new field in a request/response or a new endpoint,
tell me and I'll add it, or open a PR against `schemas.py`/`routers/` and
tag me. This keeps five people from fighting over the same files.

## Where your code plugs in

Each service file has a docstring saying who owns it and what the
function signatures are. Some functions are already implemented with a
simple placeholder (e.g. `adaptive.update_mastery` does real rule-based
scoring today); some are stubs that raise `NotImplementedError` — those
are your first task. Examples:

- `services/adaptive.next_challenge(db, student_id)` — Person 2, decide
  what a student attempts next. Not wired to a route yet; once you have a
  real implementation, tell me and I'll add `GET /student/{id}/next-challenge`.
- `services/assessment.validate_question(question)` — Person 5, check an
  LLM-generated question before it reaches a student.
- `services/ai_agents.generate(...)` — Person 1, this already calls
  OpenAI's Responses API with a fallback. Replace the internals with your
  LangGraph/multi-agent setup; keep the `(text, source)` return shape and
  the "never raise, always fall back" behavior — that's what keeps a
  flaky provider from ever 500ing a student's request.
- `services/curriculum.challenge(mission_id, context)` — Person 3, this
  currently reads `public/mock/challenge_*.json`. Replace with your
  DB/knowledge-graph lookup; keep the returned dict shape (`question_id`,
  `question`, `options`, `answer`, `explanation`, `hints`, `context`,
  `lesson`) so nothing downstream breaks.

If your function's signature needs to change, ping me — it's the contract
everyone else's code assumes.

## Auth — what you need to know

Every request that reads or writes a specific student's data now needs a
bearer token, and a student can only act as themselves.

**Register / log in:**
```bash
curl -X POST localhost:8000/auth/register -H 'Content-Type: application/json' \
  -d '{"student_id":"cadet-1","display_name":"Ada","grade_level":"10","password":"changeme123"}'
# -> {"access_token": "...", "token_type": "bearer", "student_id": "cadet-1"}

curl -X POST localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"student_id":"cadet-1","password":"changeme123"}'
```

**Use the token on protected routes:**
```bash
curl localhost:8000/students/cadet-1/progress \
  -H 'Authorization: Bearer <token>'
```

Protected: `GET /students/{id}/progress`, `POST /assessment`,
`POST /student/{id}/predict`, `POST /student/{id}/predict/resolve`.
Trying to read or write as a different student than the one in your token
gets a `403`, not silently ignored or allowed.

Not protected (no student-specific write): `GET /challenges/{id}`,
`GET /ai/dialogue`, `POST /ai/hint`, `POST /ai/explain`. If your service
starts persisting anything against a student_id, tell me — it needs to
move behind auth too.

Two things to know if you're building anything auth-adjacent:
- Tokens are HMAC-signed JSON, not a spec-compliant JWT (see
  `services/auth.py` docstring). Fine for now; flagged for replacement
  before this goes anywhere public.
- Set `AUTH_SECRET` in your local `.env`. If you don't, the app still
  runs but logs a warning and uses an insecure dev default — don't ship
  that.

## Running it locally

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
# API docs: http://localhost:8000/docs
```

Run tests before you push:
```bash
python -m pytest test_api.py -v
```
All 7 should pass. If your change breaks one, fix it before opening a PR
— that test file is the shared safety net for all five of us.

## Working agreements

- Feature branches + PRs, nobody pushes to `main` directly.
- Your service function can fail (raise), but it must not crash the
  request in a way that leaks a stack trace, an API key, or another
  student's data. Prefer returning a typed error / falling back over
  raising unhandled.
- If you're blocking on an endpoint that doesn't exist yet, say so —
  it's faster for me to add a thin router than for you to build around
  a workaround.
- The full API contract is always live at `/docs` — check there before
  asking "does this endpoint exist."
