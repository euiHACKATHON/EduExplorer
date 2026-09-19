"""Request/response contract. Owned by the backend engineer.

Service modules may read these; they must not redefine them. Changing a
field here is an API change -- announce it to the team.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

ContextType = Literal['numerical', 'real_world', 'transfer']
MissionId = Literal['M001', 'M002', 'M003']


class StudentRegister(BaseModel):
    student_id: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    display_name: str = Field(min_length=1, max_length=100)
    grade_level: Optional[str] = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=200)


class LoginRequest(BaseModel):
    student_id: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    student_id: str


class Mission(BaseModel):
    mission_id: MissionId


class Hint(Mission):
    question_id: str = Field(max_length=20)
    student_id: str = Field(max_length=100)
    level: int = Field(ge=1, le=3)


class Assessment(Mission):
    student_id: str = Field(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_-]+$')
    question_id: str = Field(max_length=20)
    answer: Literal['A', 'B', 'C', 'D']
    time_taken: float = Field(ge=0, le=86400)
    hints_used: int = Field(ge=0, le=3)
    context: ContextType = 'numerical'


class PredictionCreate(BaseModel):
    mission_id: MissionId
    question_id: str = Field(max_length=20)
    predicted: str = Field(min_length=1, max_length=200)


class PredictionResolve(BaseModel):
    prediction_id: int
    actual: str = Field(min_length=1, max_length=200)
    hints_used: int = Field(default=0, ge=0, le=3)
