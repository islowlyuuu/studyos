from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app import models  # noqa: F401  确保建表时模型已注册
from app.api import agent, documents, practice, qa
from app.config import settings
from app.database import Base, SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.execute(select(models.User).limit(1)).first() is None:
            db.add(models.User(email="default@studyos.local"))
            db.commit()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # v1 单机开发环境，后续收紧
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(qa.router)
app.include_router(practice.router)
app.include_router(agent.router)


@app.get("/health")
def health():
    return {"status": "ok"}
