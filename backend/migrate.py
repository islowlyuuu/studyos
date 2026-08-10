"""开发期轻量迁移：把缺失的列/表补齐（create_all 不会改已存在的表）。

用法：python migrate.py
"""
from sqlalchemy import inspect, text

from app.database import engine


def main() -> None:
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("source_documents")}
    with engine.begin() as conn:
        if "storage_path" not in cols:
            conn.execute(
                text("ALTER TABLE source_documents ADD COLUMN storage_path VARCHAR(500) NOT NULL DEFAULT ''")
            )
            print("added source_documents.storage_path")
        else:
            print("source_documents.storage_path exists")


if __name__ == "__main__":
    main()
