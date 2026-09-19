"""Search over chunks: BM25 keyword search, plus optional semantic search.

BM25 is pure Python and works everywhere (including the Docker image). If
`sentence-transformers` is installed, its embeddings are combined with BM25
using reciprocal-rank fusion, which handles paraphrased questions better
("why does my heavy cart speed up slowly?").
"""

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from . import settings
from .chunking import Chunk

log = logging.getLogger(__name__)

_STOPWORDS = frozenset(
    'a an and are as at be been being by can could do does did for from had has have how i if in into is it its '
    'me my of on or our so than that the their them then there these they this those to was we were what when '
    'where which who whom why will with would you your'.split()
)


def _stem(word: str) -> str:
    """Very light suffix stripping so 'accelerates', 'accelerating' and
    'acceleration' style variants meet. Deliberately simple."""
    if word.isdigit() or len(word) <= 3:
        return word
    if word.endswith('ies') and len(word) > 4:
        return word[:-3] + 'y'
    if word.endswith('sses'):
        return word[:-2]
    if word.endswith('ing') and len(word) > 5:
        return word[:-3]
    if word.endswith('ed') and len(word) > 4:
        return word[:-2]
    if word.endswith('es') and len(word) > 4 and word[-3] in 'sxz':
        return word[:-2]
    if word.endswith('s') and not word.endswith('ss') and not word.endswith('us'):
        return word[:-1]
    return word


def tokenize(text: str) -> list[str]:
    words = re.findall(r'[a-z0-9]+(?:\.[0-9]+)?', text.lower())
    return [_stem(w) for w in words if w not in _STOPWORDS and (len(w) > 1 or w.isdigit())]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.dl = [len(d) for d in docs]
        n = len(docs)
        self.avgdl = (sum(self.dl) / n) if n else 1.0
        df: Counter = Counter()
        for d in docs:
            df.update(set(d))
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = [0.0] * len(self.tf)
        for term in set(query):
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tf in enumerate(self.tf):
                f = tf.get(term, 0)
                if f:
                    norm = f + self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl)
                    out[i] += idf * f * (self.k1 + 1) / norm
        return out


@lru_cache(maxsize=1)
def _load_model(name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name)


class DenseIndex:
    """Semantic vectors (needs sentence-transformers, which brings PyTorch)."""

    def __init__(self, texts: list[str], model_name: str):
        self._model = _load_model(model_name)
        self._matrix = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)

    def scores(self, query: str) -> list[float]:
        vec = self._model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        return (self._matrix @ vec).tolist()


@dataclass
class Hit:
    chunk: Chunk
    score: float  # only comparable within one search() call


class Searcher:
    RRF_K = 60
    DENSE_MIN = 0.30  # cosine similarity below this is not treated as a semantic match
    LEXICAL_RELATIVE_MIN = 0.20  # keyword hit must reach 20% of the best keyword score

    def __init__(self, chunks: list[Chunk], mode: Optional[str] = None):
        self.chunks = list(chunks)
        mode = mode or settings.embedder_mode()
        self._bm25 = BM25([tokenize(c.text) for c in self.chunks])
        self._dense: Optional[DenseIndex] = None
        self.backend = 'bm25'
        if self.chunks and mode in ('auto', 'semantic'):
            try:
                self._dense = DenseIndex([c.text for c in self.chunks], settings.semantic_model())
                self.backend = 'bm25+semantic'
            except Exception as exc:  # not installed, offline, model missing
                if mode == 'semantic':
                    raise
                log.warning('Semantic search unavailable (%s); using BM25 keyword search.', type(exc).__name__)

    def search(
        self,
        query: str,
        k: int = 4,
        topic_ids: Optional[set[str]] = None,
        kinds: Optional[set[str]] = None,
    ) -> list[Hit]:
        if not self.chunks or not query.strip():
            return []
        allowed = [
            i for i, c in enumerate(self.chunks)
            if (topic_ids is None or c.topic_id in topic_ids) and (kinds is None or c.kind in kinds)
        ]
        if not allowed:
            return []

        bm = self._bm25.scores(tokenize(query))
        lexical = sorted((i for i in allowed if bm[i] > 0), key=lambda i: -bm[i])
        if lexical:
            floor = bm[lexical[0]] * self.LEXICAL_RELATIVE_MIN
            lexical = [i for i in lexical if bm[i] >= floor]

        if self._dense is None:
            return [Hit(self.chunks[i], round(bm[i], 4)) for i in lexical[:k]]

        sims = self._dense.scores(query)
        semantic = sorted((i for i in allowed if sims[i] >= self.DENSE_MIN), key=lambda i: -sims[i])
        fused: dict[int, float] = {}
        for ranking in (lexical, semantic):
            for rank, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (self.RRF_K + rank + 1)
        best = sorted(fused, key=lambda i: -fused[i])[:k]
        return [Hit(self.chunks[i], round(fused[i], 4)) for i in best]
