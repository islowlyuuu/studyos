from sqlalchemy import inspect, text

from app import models  # noqa: F401
from app.database import engine

with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

models.Base.metadata.create_all(bind=engine)
print("DB tables:", sorted(inspect(engine).get_table_names()))

import redis  # noqa: E402

r = redis.from_url("redis://localhost:6379/0")
print("redis ping:", r.ping())
