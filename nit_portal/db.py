from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


NOTICE_COLUMN_DEFINITIONS = {
    "user_id": "INTEGER",
    "source_tab_labels_json": "TEXT",
    "detail_link_ids_json": "TEXT",
    "content_hash": "VARCHAR(64)",
    "first_seen_at": "DATETIME",
    "content_updated_at": "DATETIME",
    "last_seen_at": "DATETIME",
}

TIMETABLE_COLUMN_DEFINITIONS = {
    "user_id": "INTEGER",
}


def _run_notice_migrations(engine) -> None:
    inspector = inspect(engine)
    if "notices" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("notices")}
    with engine.begin() as connection:
        for column_name, column_sql in NOTICE_COLUMN_DEFINITIONS.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE notices ADD COLUMN {column_name} {column_sql}"))


def _run_timetable_migrations(engine) -> None:
    inspector = inspect(engine)
    if "timetable_entries" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("timetable_entries")}
    with engine.begin() as connection:
        for column_name, column_sql in TIMETABLE_COLUMN_DEFINITIONS.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(f"ALTER TABLE timetable_entries ADD COLUMN {column_name} {column_sql}"))


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    _run_notice_migrations(engine)
    _run_timetable_migrations(engine)
    return sessionmaker(bind=engine, autoflush=False, future=True)
