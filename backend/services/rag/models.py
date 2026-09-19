"""Curriculum data model and loader (validated, no LLM involved).

`status` says how sure we are that a topic is part of Egypt's Grade 9 course:
    core         found in public outlines of the Grade 9 (third preparatory) book
    supporting   a prerequisite we added so core topics make sense
    unconfirmed  in our starter set, but NOT verified for Egyptian Grade 9
"""

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

from .settings import DEFAULT_CURRICULUM


class Unit(BaseModel):
    id: str
    title: str


class Topic(BaseModel):
    id: str
    unit: str
    title: str
    difficulty: int = Field(ge=1, le=3, description='1=easy, 2=medium, 3=hard')
    status: Literal['core', 'supporting', 'unconfirmed']
    source_note: Optional[str] = None
    prerequisites: list[str] = Field(default_factory=list)
    mission_ids: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(min_length=1)
    concepts: list[str] = Field(default_factory=list)
    formulas: list[str] = Field(default_factory=list)
    misconceptions: list[str] = Field(default_factory=list)
    content: list[str] = Field(min_length=1)


class Curriculum(BaseModel):
    curriculum_id: str
    title: str
    subject: str
    grade: int
    note: Optional[str] = None
    sources: list[str] = Field(default_factory=list)
    units: list[Unit]
    topics: list[Topic]

    @model_validator(mode='after')
    def _check_references(self) -> 'Curriculum':
        ids = [t.id for t in self.topics]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate topic ids in curriculum')
        known = set(ids)
        unit_ids = {u.id for u in self.units}
        for topic in self.topics:
            if topic.unit not in unit_ids:
                raise ValueError(f'Topic {topic.id!r} uses unknown unit {topic.unit!r}')
            for pre in topic.prerequisites:
                if pre not in known:
                    raise ValueError(f'Topic {topic.id!r} has unknown prerequisite {pre!r}')
        return self

    def topic(self, topic_id: str) -> Optional[Topic]:
        return next((t for t in self.topics if t.id == topic_id), None)

    def topics_for_mission(self, mission_id: str) -> list[Topic]:
        return [t for t in self.topics if mission_id in t.mission_ids]


def load_curriculum(path: Path | str = DEFAULT_CURRICULUM) -> Curriculum:
    return Curriculum.model_validate(json.loads(Path(path).read_text(encoding='utf-8')))
