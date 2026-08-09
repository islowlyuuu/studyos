import json

import redis

from app.config import settings

_redis: redis.Redis | None = None

QUEUE_NAME = "studyos:parse_queue"


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = redis.from_url(settings.redis_url)
    return _redis


def enqueue_parse(doc_id: int, file_path: str, filename: str, file_type: str) -> None:
    payload = json.dumps({"doc_id": doc_id, "file_path": file_path, "filename": filename, "file_type": file_type})
    get_redis().lpush(QUEUE_NAME, payload)
