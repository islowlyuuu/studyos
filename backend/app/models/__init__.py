from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    file_type: Mapped[str] = mapped_column(String(50))
    storage_path: Mapped[str] = mapped_column(String(500), default="")
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/parsing/done/failed
    parser_version: Mapped[str] = mapped_column(String(50), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("source_documents.id"))
    content: Mapped[str] = mapped_column(Text)
    heading_path: Mapped[str] = mapped_column(String(500), default="")  # 例如 "第1章/1.1 概念"
    page_number: Mapped[int] = mapped_column(Integer, nullable=True)
    char_start: Mapped[int] = mapped_column(Integer, nullable=True)
    char_end: Mapped[int] = mapped_column(Integer, nullable=True)
    embedding: Mapped[list] = mapped_column(Vector(settings.embedding_dim), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default=dict)

    document = relationship("SourceDocument", back_populates="chunks")


class KnowledgePoint(Base):
    __tablename__ = "knowledge_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)  # 前置知识点名/ID 列表
    mastery_level: Mapped[str] = mapped_column(String(20), default="new")  # new/learning/familiar/mastered/needs_review
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    source_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question_type: Mapped[str] = mapped_column(String(20))  # single_choice/true_false/short_answer/debug/...
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")
    content: Mapped[str] = mapped_column(Text)
    reference_answer: Mapped[str] = mapped_column(Text, default="")
    rubric: Mapped[dict] = mapped_column(JSON, default=dict)  # 评分规则
    source_chunk_ids: Mapped[list] = mapped_column(JSON, default=list)
    knowledge_point_ids: Mapped[list] = mapped_column(JSON, default=list)


class AnswerAttempt(Base):
    __tablename__ = "answer_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    answer: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default="")
    mistakes: Mapped[list] = mapped_column(JSON, default=list)  # 错的点 / 薄弱知识点
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    intent: Mapped[str] = mapped_column(String(100), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    prompt_version: Mapped[str] = mapped_column(String(50), default="")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    tool_trace: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
