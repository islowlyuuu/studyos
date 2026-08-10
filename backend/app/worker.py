import json

import redis

from app.services.ingest import ingest_document
from app.services.queue import QUEUE_NAME, get_redis, reset_redis


def run_worker() -> None:
    r = get_redis()
    print("[worker] started, waiting for jobs...")
    while True:
        try:
            item = r.brpop(QUEUE_NAME, timeout=10)
        except redis.RedisError:
            reset_redis()
            r = get_redis()
            continue
        if item is None:
            continue
        _, payload = item
        job = json.loads(payload)
        print(f"[worker] parsing doc {job['doc_id']}: {job['filename']}")
        try:
            with open(job["file_path"], "rb") as f:
                data = f.read()
            ingest_document(job["doc_id"], job["filename"], data, job["file_type"])
            print(f"[worker] done doc {job['doc_id']}")
        except Exception as e:
            print(f"[worker] failed doc {job['doc_id']}: {e}")


if __name__ == "__main__":
    run_worker()
