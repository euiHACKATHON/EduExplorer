"""Mars Colony Explorer -- application factory.

Local classroom prototype. Per-user rate limits are still required before
public hosting (auth now exists; see routers/auth.py and deps.py).

This file registers middleware and routers ONLY. Endpoint logic lives in
routers/, domain logic in services/. Do not add business logic here.

`challenge` and `_contains_correct_answer` are re-exported below purely so
`tests/test_agents.py` (which imports them from backend.main) keeps
working. Their real home is services/curriculum.py and
services/ai_agents.py respectively -- import from there in new code.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ALLOWED_ORIGINS, groq_key
from .database import init_db
from .routers import ai, assessment, auth, missions, predictions, students
from .services.ai_agents import _contains_correct_answer  # noqa: F401  (re-export)
from .services.curriculum import challenge  # noqa: F401  (re-export)


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title='Mars Colony Explorer')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=['GET', 'POST'],
        allow_headers=['Content-Type', 'Authorization'],
    )

    @app.get('/health')
    def health():
        return {'status': 'ok', 'ai_available': bool(groq_key()), 'provider': 'groq'}

    app.include_router(auth.router)
    app.include_router(students.router)
    app.include_router(missions.router)
    app.include_router(ai.router)
    app.include_router(assessment.router)
    app.include_router(predictions.router)
    return app


app = create_app()
