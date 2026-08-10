from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.agent.router import run_agent
from app.database import SessionLocal
from app.models import KnowledgePoint, MistakeRecord, StudyPlan

router = APIRouter(prefix="/api/agent", tags=["agent"])

DEFAULT_USER_ID = 1


class AgentRequest(BaseModel):
    message: str


@router.post("/run")
def run(req: AgentRequest):
    return run_agent(req.message, user_id=DEFAULT_USER_ID)


@router.get("/knowledge-points")
def list_knowledge_points():
    db = SessionLocal()
    try:
        rows = db.execute(
            select(KnowledgePoint).order_by(KnowledgePoint.id.desc())
        ).scalars().all()
        return [
            {"id": k.id, "name": k.name, "mastery_level": k.mastery_level} for k in rows
        ]
    finally:
        db.close()


@router.get("/mistakes")
def list_mistakes():
    db = SessionLocal()
    try:
        rows = db.execute(select(MistakeRecord).order_by(MistakeRecord.id.desc())).scalars().all()
        return [
            {
                "id": m.id,
                "question": m.question,
                "knowledge_points": m.knowledge_points,
                "note": m.note,
                "created_at": str(m.created_at),
            }
            for m in rows
        ]
    finally:
        db.close()


@router.get("/plans")
def list_plans():
    db = SessionLocal()
    try:
        rows = db.execute(select(StudyPlan).order_by(StudyPlan.id.desc())).scalars().all()
        return [
            {
                "id": p.id,
                "goal": p.goal,
                "focus_points": p.focus_points,
                "duration_days": p.duration_days,
                "content": p.content,
                "created_at": str(p.created_at),
            }
            for p in rows
        ]
    finally:
        db.close()
