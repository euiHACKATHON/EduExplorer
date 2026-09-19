"""Curriculum / RAG endpoints.  LOGIC: Person 3 (services/curriculum.py + services/rag/).

Proposed for the backend engineer to review: this file is a thin HTTP layer
only (validate -> call the service -> shape the response). Move RagQuery into
schemas.py if you prefer all request models to live there.
"""
import logging
from pathlib import Path
from typing import Optional

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..deps import get_current_student
from ..services import curriculum
from ..services.rag import settings
from ..services.rag.chunking import PDFError, extract_pdf_text

router = APIRouter(tags=['curriculum'])
log = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024

try:  # build the index at start-up so the first request is fast
    curriculum.warm_up()
except Exception:
    log.exception('Curriculum warm-up failed; it will be retried on the first request')


class RagQuery(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    k: int = Field(default=4, ge=1, le=10)
    topic_id: Optional[str] = Field(default=None, max_length=60)


@router.get('/curriculum/objectives')
def objectives(topic_id: Optional[str] = None, unit: Optional[str] = None):
    idx = curriculum.get_index()
    return {
        'curriculum': idx.curriculum.title,
        'grade': idx.curriculum.grade,
        'note': idx.curriculum.note,
        'objectives': curriculum.objectives(topic_id=topic_id, unit=unit),
    }


@router.get('/curriculum/graph')
def graph():
    idx = curriculum.get_index()
    return {'learning_path': idx.graph.learning_path(), **idx.graph.to_dict()}


@router.get('/topic/{topic_id}')
def topic(topic_id: str):
    detail = curriculum.topic_detail(topic_id)
    if detail is None:
        raise HTTPException(404, 'Unknown topic')
    return detail


@router.post('/rag/query')
def rag_query(payload: RagQuery):
    idx = curriculum.get_index()
    if payload.topic_id and idx.curriculum.topic(payload.topic_id) is None:
        raise HTTPException(404, 'Unknown topic')
    hits = curriculum.search(payload.question, k=payload.k, topic_id=payload.topic_id)
    return {
        'retrieval_backend': idx.backend,
        'results': [
            {
                'text': h.chunk.text,
                'score': h.score,
                'kind': h.chunk.kind,
                'topic_id': h.chunk.topic_id,
                'topic_title': h.chunk.topic_title,
                'source': h.chunk.source,
            }
            for h in hits
        ],
    }


@router.post('/curriculum/upload')
async def upload(
    request: Request,
    filename: str = Query(min_length=1, max_length=100),
    _student: str = Depends(get_current_student),
):
    """Index a curriculum document. The request body is the raw file (no
    multipart, so no extra dependency): e.g.
        curl -X POST "localhost:8000/curriculum/upload?filename=book.pdf" \\
             -H "Authorization: Bearer <token>" --data-binary @book.pdf
    Disabled unless RAG_ALLOW_UPLOAD=1: uploaded text ends up in tutor prompts,
    and there are no admin accounts yet. Uploads are lost on redeploy when the
    hosting filesystem is ephemeral."""
    if not settings.uploads_enabled():
        raise HTTPException(403, 'Curriculum upload is disabled. Set RAG_ALLOW_UPLOAD=1 to enable it.')
    name = Path(filename).name
    lower = name.lower()
    if not lower.endswith(('.pdf', '.txt', '.md')):
        raise HTTPException(400, 'Upload a .pdf, .txt or .md file')

    size, parts = 0, []
    async for part in request.stream():
        size += len(part)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(413, f'File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB')
        parts.append(part)
    data = b''.join(parts)

    if lower.endswith('.pdf'):
        try:
            text = await to_thread.run_sync(extract_pdf_text, data)
        except PDFError as exc:
            raise HTTPException(400, str(exc)) from exc
    else:
        try:
            text = data.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise HTTPException(400, 'Text files must be UTF-8') from exc
    count = await to_thread.run_sync(curriculum.add_upload, name, text)
    return {'filename': name, 'chunks_indexed': count}
