"""Turning curricula and uploaded documents into retrievable chunks.

    curriculum JSON -> chunks (one per teaching paragraph, plus objectives,
                               formulas and misconception chunks, each tagged with its topic)
    PDF / text      -> clean text -> paragraph-aware chunks
"""

import io
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Optional

from .models import Curriculum

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 300


@dataclass
class Chunk:
    id: str
    text: str
    kind: str  # content | objectives | formulas | misconception | upload
    source: str  # curriculum id or uploaded filename
    topic_id: Optional[str] = None
    topic_title: Optional[str] = None
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class PDFError(ValueError):
    """Raised for unreadable, oversized, or text-less PDFs."""


def extract_pdf_text(data: bytes) -> str:
    if len(data) > MAX_PDF_BYTES:
        raise PDFError(f'PDF is larger than {MAX_PDF_BYTES // (1024 * 1024)} MB')
    if not data.startswith(b'%PDF'):
        raise PDFError('File does not look like a PDF')
    try:
        from pypdf import PdfReader  # optional dependency, imported lazily
    except ImportError as exc:
        raise PDFError('PDF support needs pypdf: python -m pip install pypdf') from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > MAX_PDF_PAGES:
            raise PDFError(f'PDF has more than {MAX_PDF_PAGES} pages')
        pages = [(page.extract_text() or '') for page in reader.pages]
    except PDFError:
        raise
    except Exception as exc:  # corrupt or encrypted files
        raise PDFError(f'Could not read PDF: {exc}') from exc
    text = clean_text('\n\n'.join(pages))
    if len(text) < 50:
        raise PDFError('No text found. This PDF may be a scan; run OCR on it first.')
    return text


def clean_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)  # re-join hyphenated line breaks
    lines = [ln.strip() for ln in text.split('\n')]
    lines = [ln for ln in lines if not re.fullmatch(r'(?i)(page\s*)?\d{1,4}', ln)]  # bare page numbers
    text = '\n'.join(lines)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'(])')


def chunk_text(text: str, max_words: int = 90) -> list[str]:
    """Paragraph-aware chunking. Long paragraphs are split on sentence
    boundaries, and each new piece repeats the previous sentence as overlap so
    an idea is not cut in half."""
    chunks: list[str] = []
    for para in re.split(r'\n\s*\n', text):
        para = re.sub(r'\s*\n\s*', ' ', para).strip()  # PDFs wrap lines inside paragraphs
        if not para:
            continue
        if len(para.split()) <= max_words:
            chunks.append(para)
            continue
        current: list[str] = []
        count = 0
        for sentence in _SENTENCE_SPLIT.split(para):
            words = len(sentence.split())
            if current and count + words > max_words:
                chunks.append(' '.join(current))
                current = [current[-1]]  # one-sentence overlap
                count = len(current[0].split())
            current.append(sentence)
            count += words
        if current:
            chunks.append(' '.join(current))
    return chunks


def chunks_from_curriculum(curriculum: Curriculum) -> list[Chunk]:
    out: list[Chunk] = []
    for topic in curriculum.topics:
        base = {'source': curriculum.curriculum_id, 'topic_id': topic.id, 'topic_title': topic.title}
        meta = {'difficulty': topic.difficulty, 'status': topic.status}
        for i, paragraph in enumerate(topic.content):
            out.append(Chunk(id=f'{topic.id}:content:{i}', text=f'{topic.title}. {paragraph}',
                             kind='content', meta=meta, **base))
        out.append(Chunk(id=f'{topic.id}:objectives',
                         text=f'{topic.title}. Learning objectives: ' + ' '.join(topic.objectives),
                         kind='objectives', meta=meta, **base))
        if topic.formulas:
            out.append(Chunk(id=f'{topic.id}:formulas',
                             text=f'{topic.title}. Key formulas: ' + '; '.join(topic.formulas),
                             kind='formulas', meta=meta, **base))
        for i, misconception in enumerate(topic.misconceptions):
            out.append(Chunk(id=f'{topic.id}:misconception:{i}',
                             text=f'{topic.title}. Common misconception: {misconception}',
                             kind='misconception', meta=meta, **base))
    return out


def chunks_from_text(text: str, source: str) -> list[Chunk]:
    safe = re.sub(r'[^A-Za-z0-9_.-]', '_', source)[:60] or 'upload'
    return [Chunk(id=f'{safe}:{i}', text=piece, kind='upload', source=source)
            for i, piece in enumerate(chunk_text(text))]
