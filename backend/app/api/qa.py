from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.qa import answer_question, stream_answer

router = APIRouter(prefix="/api/qa", tags=["qa"])

DEFAULT_USER_ID = 1


class QARequest(BaseModel):
    query: str


@router.post("/ask")
def ask(req: QARequest):
    return answer_question(req.query, user_id=DEFAULT_USER_ID)


@router.post("/stream")
def ask_stream(req: QARequest):
    return StreamingResponse(stream_answer(req.query, user_id=DEFAULT_USER_ID), media_type="text/event-stream")
