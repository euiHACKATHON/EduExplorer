"""Password hashing and session tokens.  OWNER: backend engineer.

Deliberately dependency-free for the classroom prototype:
- Passwords: PBKDF2-HMAC-SHA256 (stdlib `hashlib`), random salt per user.
- Tokens: a JSON payload + HMAC-SHA256 signature, base64url-encoded. This is
  JWT-*shaped* but is NOT a spec-compliant JWT (no header/alg negotiation,
  no standard library interop). It is fine for a single trusted backend
  issuing and verifying its own tokens.

Before public hosting, swap `create_token`/`decode_token` for a real JWT
library (PyJWT or python-jose) -- same flag as elsewhere in this codebase.
Nothing outside this file needs to change if the function signatures stay
the same.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from ..config import AUTH_SECRET, TOKEN_TTL_SECONDS

PBKDF2_ITERATIONS = 260_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, PBKDF2_ITERATIONS)
    return f'{salt.hex()}${digest.hex()}'


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split('$', 1)
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    candidate = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(candidate.hex(), digest_hex)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def _b64decode(data: str) -> bytes:
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(student_id: str) -> str:
    payload = {'sub': student_id, 'exp': int(time.time()) + TOKEN_TTL_SECONDS}
    payload_b64 = _b64encode(json.dumps(payload).encode())
    signature = hmac.new(AUTH_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f'{payload_b64}.{signature}'


def decode_token(token: str) -> str:
    """Return the student_id encoded in `token`, or raise ValueError."""
    try:
        payload_b64, signature = token.split('.', 1)
    except ValueError:
        raise ValueError('Malformed token')
    expected = hmac.new(AUTH_SECRET.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError('Bad signature')
    payload = json.loads(_b64decode(payload_b64))
    if payload.get('exp', 0) < time.time():
        raise ValueError('Token expired')
    student_id = payload.get('sub')
    if not student_id:
        raise ValueError('Token missing subject')
    return student_id
