"""Single typed place for environment configuration.

Everything that used to be a scattered os.getenv() call lives here. Import
from this module instead of reading the environment directly.
"""
import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

# --- storage -------------------------------------------------------------
DB = os.getenv('MARS_DB', str(ROOT / 'backend' / 'progress.sqlite3'))
MOCK_DIR = ROOT / 'public' / 'mock'

# --- http ----------------------------------------------------------------
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        'ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173'
    ).split(',')
    if o.strip()
]

# --- content -------------------------------------------------------------
KNOWN_MISSIONS = ('M001', 'M002', 'M003')
KNOWN_NPCS = ('scientist_01', 'engineer_01', 'botanist_01')

# --- adaptive learning ---------------------------------------------------
# Score delta across contexts that flags a possible "fake mastery" gap.
TRANSFER_GAP_THRESHOLD = 0.35

# --- auth ------------------------------------------------------------------
# Lightweight HMAC-signed tokens for the classroom prototype (see
# services/auth.py) -- not a spec-compliant JWT library. Swap for
# python-jose/PyJWT before public hosting, same flag as the module docstring
# in main.py.
AUTH_SECRET = os.getenv('AUTH_SECRET', '')
if not AUTH_SECRET:
    AUTH_SECRET = 'dev-only-insecure-secret-change-me'
    warnings.warn(
        'AUTH_SECRET is not set -- using an insecure development default. '
        'Set AUTH_SECRET in your .env before deploying anywhere real.',
        stacklevel=2,
    )

TOKEN_TTL_SECONDS = int(os.getenv('TOKEN_TTL_SECONDS', str(60 * 60 * 12)))  # 12h


def openai_key() -> str:
    """Read lazily: tests flip this at runtime via monkeypatch.setenv."""
    return os.getenv('OPENAI_API_KEY', '')


def openai_model() -> str:
    return os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
