"""Shared FastAPI dependencies.  OWNER: backend engineer.

`require_self` relies on FastAPI's normal dependency resolution: when a
route has a path parameter named `student_id`, any dependency of that route
that also declares a `student_id` parameter receives the same value. That's
why `require_self` doesn't need `Path(...)` -- FastAPI wires it up because
the names match.
"""
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request

from .services.auth import decode_token


def get_current_student(authorization: str = Header(default='')) -> str:
    """Extract and verify the bearer token. Returns the student_id inside it."""
    if not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Missing or malformed Authorization header')
    token = authorization.removeprefix('Bearer ').strip()
    try:
        return decode_token(token)
    except ValueError:
        raise HTTPException(401, 'Invalid or expired token')


def require_self(student_id: str, current_student: str = Depends(get_current_student)) -> str:
    """Use on any route with a {student_id} path param that only that
    student (not other students) should be able to read or write."""
    if student_id != current_student:
        raise HTTPException(403, "Cannot access another student's data")
    return current_student


def ai_rate_limit_key(student_id: Optional[str], request: Request) -> str:
    """Key to rate-limit an /ai/* call against: the student if we know who
    they are, otherwise the caller's IP. Not a `Depends()` -- called
    directly inside each route since not every /ai/* payload carries a
    student_id (see routers/ai.py)."""
    if student_id:
        return f'student:{student_id}'
    client = request.client.host if request.client else 'unknown'
    return f'ip:{client}'
