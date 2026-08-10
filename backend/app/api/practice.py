from fastapi import APIRouter
from pydantic import BaseModel

from app.services.practice import generate_question, grade_answer

router = APIRouter(prefix="/api/practice", tags=["practice"])

DEFAULT_USER_ID = 1


class GenerateRequest(BaseModel):
    topic: str
    question_type: str | None = None


class AnswerRequest(BaseModel):
    question_id: int
    answer: str


@router.post("/generate")
def generate(req: GenerateRequest):
    return generate_question(req.topic, user_id=DEFAULT_USER_ID, question_type=req.question_type)


@router.post("/answer")
def answer(req: AnswerRequest):
    return grade_answer(req.question_id, req.answer, user_id=DEFAULT_USER_ID)
