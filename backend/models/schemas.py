from pydantic import BaseModel
from typing import Optional


class Question(BaseModel):
    id: int
    type: str
    chapter: str
    question: str
    options: Optional[dict] = None
    answer: str
    analysis: str
    score_steps: Optional[list[dict]] = None
    knowledge_points: Optional[list[str]] = None
    difficulty: str


class AnswerRequest(BaseModel):
    question_id: int
    answer: str


class ScoreStep(BaseModel):
    step: str
    keywords: list[str]
    score: float


class ScoreResult(BaseModel):
    total_score: float
    max_score: float
    percentage: float
    details: list[dict]


class AnswerResponse(BaseModel):
    question_id: int
    is_correct: bool
    score: ScoreResult
    correct_answer: str
    analysis: str


class ChatRequest(BaseModel):
    question: str
    history: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    answer: str
    sources: Optional[list[str]] = None
