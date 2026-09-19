"""Environment settings for the RAG module (read lazily, so tests can change them).

RAG_EMBEDDER     auto (default) | bm25 | semantic
                 auto: use semantic search if sentence-transformers is installed
                 and its model loads, otherwise fall back to BM25 keyword search.
RAG_MODEL        sentence-transformers model name (default all-MiniLM-L6-v2, ~90 MB)
RAG_UPLOADS      where uploaded-document chunks are cached (JSON file)
RAG_ALLOW_UPLOAD 1 to enable POST /curriculum/upload (off by default)
"""

import os
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / 'data'
DEFAULT_CURRICULUM = DATA_DIR / 'physics_grade9.json'


def embedder_mode() -> str:
    return os.getenv('RAG_EMBEDDER', 'auto').strip().lower()


def semantic_model() -> str:
    return os.getenv('RAG_MODEL', 'sentence-transformers/all-MiniLM-L6-v2')


def uploads_path() -> Path:
    return Path(os.getenv('RAG_UPLOADS', str(DATA_DIR / 'uploads.json')))


def uploads_enabled() -> bool:
    return os.getenv('RAG_ALLOW_UPLOAD', '').strip().lower() in ('1', 'true', 'yes')
