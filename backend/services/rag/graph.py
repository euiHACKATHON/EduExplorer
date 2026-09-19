"""Knowledge graph of topics (pure Python, no third-party package).

Nodes are topics; an edge A -> B means "A is a prerequisite of B". The graph
answers the questions the Adaptive Learning module needs: what must be learned
first, what a topic unlocks, and which topics a student is ready for next.
"""

import heapq

from .models import Curriculum


class KnowledgeGraph:
    def __init__(self, curriculum: Curriculum):
        self.curriculum = curriculum
        self._topics = {t.id: t for t in curriculum.topics}
        self._prereqs = {t.id: list(t.prerequisites) for t in curriculum.topics}
        self._unlocks: dict[str, list[str]] = {tid: [] for tid in self._topics}
        for tid, pres in self._prereqs.items():
            for pre in pres:
                self._unlocks[pre].append(tid)
        self._unit_rank = {u.id: i for i, u in enumerate(curriculum.units)}
        self._order = self._topological_order()

    def _sort_key(self, tid: str) -> tuple:
        """Teaching-order tiebreak: book unit order, confirmed topics before
        unconfirmed ones, easier first, then id (so the order is stable)."""
        t = self._topics[tid]
        status_rank = {'core': 0, 'supporting': 1, 'unconfirmed': 2}[t.status]
        return (self._unit_rank[t.unit], status_rank, t.difficulty, tid)

    def _topological_order(self) -> list[str]:
        """Kahn's algorithm with the tiebreak above. Raises ValueError if
        prerequisites form a cycle."""
        indegree = {tid: len(pres) for tid, pres in self._prereqs.items()}
        heap = [self._sort_key(t) for t, n in indegree.items() if n == 0]
        heapq.heapify(heap)
        order: list[str] = []
        while heap:
            tid = heapq.heappop(heap)[-1]
            order.append(tid)
            for nxt in self._unlocks[tid]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    heapq.heappush(heap, self._sort_key(nxt))
        if len(order) != len(self._topics):
            raise ValueError('Prerequisites contain a cycle')
        return order

    def _check(self, topic_id: str) -> None:
        if topic_id not in self._topics:
            raise KeyError(topic_id)

    def _in_path_order(self, ids: set[str]) -> list[str]:
        return [t for t in self._order if t in ids]

    def prerequisites(self, topic_id: str, transitive: bool = False) -> list[str]:
        self._check(topic_id)
        if not transitive:
            return self._in_path_order(set(self._prereqs[topic_id]))
        seen: set[str] = set()
        stack = list(self._prereqs[topic_id])
        while stack:
            tid = stack.pop()
            if tid not in seen:
                seen.add(tid)
                stack.extend(self._prereqs[tid])
        return self._in_path_order(seen)

    def unlocks(self, topic_id: str) -> list[str]:
        self._check(topic_id)
        return self._in_path_order(set(self._unlocks[topic_id]))

    def concepts(self, topic_id: str) -> list[str]:
        self._check(topic_id)
        return list(self._topics[topic_id].concepts)

    def learning_path(self) -> list[str]:
        """Every topic id in a valid teaching order (prerequisites first)."""
        return list(self._order)

    def next_topics(self, mastered: set[str]) -> list[str]:
        """Topics not yet mastered whose prerequisites are ALL mastered."""
        return [
            tid for tid in self._order
            if tid not in mastered and all(p in mastered for p in self._prereqs[tid])
        ]

    def to_dict(self) -> dict:
        """JSON-friendly export (for a frontend graph view)."""
        return {
            'nodes': [
                {'id': t.id, 'title': t.title, 'unit': t.unit, 'difficulty': t.difficulty,
                 'status': t.status, 'concepts': t.concepts}
                for t in (self._topics[i] for i in self._order)
            ],
            'edges': [
                {'source': pre, 'target': tid, 'relation': 'prerequisite_of'}
                for tid in self._order for pre in self._prereqs[tid]
            ],
        }
