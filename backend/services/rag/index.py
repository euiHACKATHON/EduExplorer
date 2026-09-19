"""CurriculumIndex: curriculum + knowledge graph + search, in one object."""

import json
from pathlib import Path
from typing import Optional

from . import settings
from .chunking import Chunk, chunks_from_curriculum, chunks_from_text
from .graph import KnowledgeGraph
from .models import Curriculum, load_curriculum
from .search import Hit, Searcher

# What the tutor agent may see as background material.
CONTEXT_KINDS = {'content', 'formulas', 'misconception', 'upload'}


class CurriculumIndex:
    def __init__(
        self,
        curriculum_path: Path | str = settings.DEFAULT_CURRICULUM,
        uploads_path: Optional[Path | str] = None,
        mode: Optional[str] = None,
    ):
        self.curriculum: Curriculum = load_curriculum(curriculum_path)
        self.graph = KnowledgeGraph(self.curriculum)
        self.uploads_path = Path(uploads_path) if uploads_path else settings.uploads_path()
        self._mode = mode
        self._curriculum_chunks = chunks_from_curriculum(self.curriculum)
        self._uploaded: list[Chunk] = self._load_uploads()
        self._searcher = Searcher(self.all_chunks(), mode)

    # --- index management ------------------------------------------------------
    @property
    def backend(self) -> str:
        return self._searcher.backend

    def all_chunks(self) -> list[Chunk]:
        return self._curriculum_chunks + self._uploaded

    def _load_uploads(self) -> list[Chunk]:
        try:
            raw = json.loads(self.uploads_path.read_text(encoding='utf-8'))
            return [Chunk(**item) for item in raw]
        except (OSError, ValueError, TypeError):
            return []  # a missing or corrupt cache must never stop the server starting

    def _save_uploads(self) -> None:
        self.uploads_path.parent.mkdir(parents=True, exist_ok=True)
        self.uploads_path.write_text(
            json.dumps([c.to_dict() for c in self._uploaded], ensure_ascii=False), encoding='utf-8'
        )

    def add_upload(self, filename: str, text: str) -> int:
        """Index text from an uploaded document. Re-uploading the same
        filename replaces its earlier chunks. Returns the chunk count."""
        self._uploaded = [c for c in self._uploaded if c.source != filename]
        new = chunks_from_text(text, filename)
        self._uploaded.extend(new)
        self._save_uploads()
        self._searcher = Searcher(self.all_chunks(), self._mode)
        return len(new)

    # --- queries ---------------------------------------------------------------
    def search(self, question: str, k: int = 4, topic_id: Optional[str] = None) -> list[Hit]:
        return self._searcher.search(question, k=k, topic_ids={topic_id} if topic_id else None)

    def _mission_scope(self, mission_id: str) -> set[str]:
        """Topics linked to a mission, plus everything they build on."""
        scope: set[str] = set()
        for topic in self.curriculum.topics_for_mission(mission_id):
            scope.add(topic.id)
            scope.update(self.graph.prerequisites(topic.id, transitive=True))
        return scope

    def context_for(self, mission_id: str, question: Optional[str] = None, k: int = 3) -> list[str]:
        """Background passages for `AgentState.retrieved_context`.

        Prefers passages from the mission's own topic and its prerequisites, then
        fills any remaining slots from the wider curriculum. Returns [] for
        missions with no linked topic (e.g. the biology mission)."""
        topics = self.curriculum.topics_for_mission(mission_id)
        if not topics:
            return []
        query = question or f'{topics[0].title}. {topics[0].objectives[0]}'
        hits = self._searcher.search(query, k=k, topic_ids=self._mission_scope(mission_id), kinds=CONTEXT_KINDS)
        if len(hits) < k and question:
            seen = {h.chunk.id for h in hits}
            wider = self._searcher.search(query, k=k, kinds=CONTEXT_KINDS)
            hits += [h for h in wider if h.chunk.id not in seen][: k - len(hits)]
        return [h.chunk.text for h in hits]

    def objectives(self, topic_id: Optional[str] = None, unit: Optional[str] = None) -> list[dict]:
        out = []
        for topic in self.curriculum.topics:
            if topic_id and topic.id != topic_id:
                continue
            if unit and topic.unit != unit:
                continue
            for i, text in enumerate(topic.objectives):
                out.append({
                    'objective_id': f'{topic.id}#{i + 1}',
                    'topic_id': topic.id,
                    'topic_title': topic.title,
                    'unit': topic.unit,
                    'difficulty': topic.difficulty,
                    'status': topic.status,
                    'objective': text,
                    'mission_ids': topic.mission_ids,
                })
        return out

    def topic_detail(self, topic_id: str) -> Optional[dict]:
        topic = self.curriculum.topic(topic_id)
        if topic is None:
            return None
        return {
            **topic.model_dump(),
            'prerequisites_all': self.graph.prerequisites(topic_id, transitive=True),
            'unlocks': self.graph.unlocks(topic_id),
        }
