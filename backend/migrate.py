"""开发期轻量迁移：补齐资料治理和评测所需表/列。

用法：python migrate.py
"""
from sqlalchemy import inspect, text

from app.database import Base, engine
from app import models  # noqa: F401


DOCUMENT_COLUMNS = {
    "storage_path": "VARCHAR(500) NOT NULL DEFAULT ''",
    "content_hash": "VARCHAR(64) NOT NULL DEFAULT ''",
    "logical_key": "VARCHAR(36) NOT NULL DEFAULT ''",
    "version": "INTEGER NOT NULL DEFAULT 1",
    "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
    "cancel_requested": "BOOLEAN NOT NULL DEFAULT FALSE",
    "chunker_version": "VARCHAR(50) NOT NULL DEFAULT 'heading-v1'",
    "embedding_model": "VARCHAR(255) NOT NULL DEFAULT ''",
    "indexed_at": "TIMESTAMP WITH TIME ZONE",
}


def main() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("source_documents")}
    with engine.begin() as connection:
        for name, definition in DOCUMENT_COLUMNS.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE source_documents ADD COLUMN {name} {definition}"))
                print(f"added source_documents.{name}")
        connection.execute(text("UPDATE source_documents SET logical_key = CAST(id AS TEXT) WHERE logical_key = ''"))
        connection.execute(text("UPDATE source_documents SET content_hash = CONCAT('legacy-', id) WHERE content_hash = ''"))
        connection.execute(text("UPDATE source_documents SET is_active = TRUE WHERE parse_status = 'done' AND cancel_requested = FALSE"))
    print("migration complete")


if __name__ == "__main__":
    main()
