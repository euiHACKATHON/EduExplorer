"""Test-wide settings, applied before any test module imports backend.main.

Tests must never download models, call Groq, or write to the real database or
the RAG uploads cache.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix='eduexplorer-tests-')
os.environ['RAG_EMBEDDER'] = 'bm25'
os.environ['RAG_UPLOADS'] = os.path.join(_tmp, 'uploads.json')
os.environ.pop('RAG_ALLOW_UPLOAD', None)
os.environ.setdefault('MARS_DB', os.path.join(_tmp, 'progress.sqlite3'))
os.environ.setdefault('AUTH_SECRET', 'test-secret-do-not-use-in-prod')
os.environ['GROQ_API_KEY'] = ''
