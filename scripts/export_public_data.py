#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from nit_portal.config import get_database_url, load_dotenv
from nit_portal.db import create_session_factory
from nit_portal.models import Notice, TimetableEntry, User


OUTPUT_DIR = Path("public/api")


def serialize_datetime(value: date | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_export_user_id(session_factory) -> int | None:
    export_user_id = os.environ.get("EXPORT_USER_ID")
    if export_user_id:
        return int(export_user_id)

    export_portal_user_name = os.environ.get("EXPORT_PORTAL_USER_NAME") or os.environ.get("USER_NAME")
    if not export_portal_user_name:
        return None

    with session_factory() as session:
        user = session.execute(select(User).where(User.portal_user_name == export_portal_user_name)).scalar_one_or_none()
    return user.id if user else None


def export_notices(session_factory, export_user_id: int | None) -> dict:
    with session_factory() as session:
        statement = select(Notice)
        if export_user_id is not None:
            statement = statement.where(Notice.user_id == export_user_id)
        notices = session.execute(statement.order_by(Notice.published_on.desc(), Notice.id.desc())).scalars().all()

    items = []
    for notice in notices:
        items.append(
            {
                "id": notice.id,
                "portal_notice_key": notice.portal_notice_key,
                "title": notice.title,
                "sender": notice.sender,
                "category": notice.category,
                "body": notice.body,
                "published_on": serialize_datetime(notice.published_on),
                "notice_starts_at": serialize_datetime(notice.notice_starts_at),
                "notice_ends_at": serialize_datetime(notice.notice_ends_at),
                "is_new": notice.is_new,
                "is_important": notice.is_important,
                "is_flagged": notice.is_flagged,
                "is_read": notice.is_read,
                "source_tab_labels": json.loads(notice.source_tab_labels_json or "[]"),
                "detail_link_ids": json.loads(notice.detail_link_ids_json or "[]"),
                "content_hash": notice.content_hash,
                "first_seen_at": serialize_datetime(notice.first_seen_at),
                "content_updated_at": serialize_datetime(notice.content_updated_at),
                "last_synced_at": serialize_datetime(notice.last_synced_at),
                "last_seen_at": serialize_datetime(notice.last_seen_at),
            }
        )

    payload = {
        "metadata": {
            "count": len(items),
            "all_tab_count": sum(1 for item in items if "all" in item["source_tab_labels"]),
            "exported_at": datetime.now().isoformat(),
        },
        "items": items,
    }
    write_json(OUTPUT_DIR / "notices.json", payload)
    return payload["metadata"]


def export_timetable(session_factory, export_user_id: int | None) -> dict:
    with session_factory() as session:
        statement = select(TimetableEntry)
        if export_user_id is not None:
            statement = statement.where(TimetableEntry.user_id == export_user_id)
        entries = session.execute(
            statement.order_by(TimetableEntry.weekday.asc(), TimetableEntry.period.asc(), TimetableEntry.id.asc())
        ).scalars().all()

    items = []
    academic_year = None
    semester = None
    campus = None
    for entry in entries:
        academic_year = academic_year or entry.academic_year
        semester = semester or entry.semester
        campus = campus or entry.campus
        items.append(
            {
                "id": entry.id,
                "portal_timetable_key": entry.portal_timetable_key,
                "academic_year": entry.academic_year,
                "semester": entry.semester,
                "campus": entry.campus,
                "weekday": entry.weekday,
                "period": entry.period,
                "subject": entry.subject,
                "instructor": entry.instructor,
                "room": entry.room,
                "course_code": entry.course_code,
                "credits": entry.credits,
                "note": entry.note,
                "last_synced_at": serialize_datetime(entry.last_synced_at),
            }
        )

    payload = {
        "metadata": {
            "count": len(items),
            "academic_year": academic_year,
            "semester": semester,
            "campus": campus,
            "exported_at": datetime.now().isoformat(),
        },
        "items": items,
    }
    write_json(OUTPUT_DIR / "timetable.json", payload)
    return payload["metadata"]


def main() -> int:
    load_dotenv()
    session_factory = create_session_factory(get_database_url())
    export_user_id = resolve_export_user_id(session_factory)
    notice_metadata = export_notices(session_factory, export_user_id)
    timetable_metadata = export_timetable(session_factory, export_user_id)
    status_payload = {
        "metadata": {
            "exported_at": datetime.now().isoformat(),
            "export_user_id": export_user_id,
        },
        "notices": notice_metadata,
        "timetable": timetable_metadata,
    }
    write_json(OUTPUT_DIR / "status.json", status_payload)
    print(f"Exported public data to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
