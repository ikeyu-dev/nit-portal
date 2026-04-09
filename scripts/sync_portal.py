#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from nit_portal.config import get_database_url, load_dotenv, require_env
from nit_portal.db import create_session_factory
from nit_portal.models import Notice, PortalCredential, TimetableEntry, User
from nit_portal.portal_client import PortalClient, make_notice_content_hash, make_notice_summary_key, make_timetable_key
from nit_portal.security import encrypt_secret


def make_storage_notice_key(user_id: int, portal_notice_key: str) -> str:
    return f"{user_id}:{portal_notice_key}"


def make_storage_timetable_key(user_id: int, portal_timetable_key: str) -> str:
    return f"{user_id}:{portal_timetable_key}"


def ensure_user(session, portal_user_name: str, display_name: str | None = None) -> User:
    user = session.execute(select(User).where(User.portal_user_name == portal_user_name)).scalar_one_or_none()
    if user is None:
        user = User(
            portal_user_name=portal_user_name,
            display_name=display_name or portal_user_name,
            is_active=True,
        )
        session.add(user)
        session.flush()
    elif display_name and user.display_name != display_name:
        user.display_name = display_name
    return user


def maybe_upsert_credential(session, user: User, portal_user_name: str, password: str) -> None:
    if not os.environ.get("CREDENTIALS_ENCRYPTION_KEY"):
        return

    credential = session.execute(
        select(PortalCredential).where(PortalCredential.user_id == user.id)
    ).scalar_one_or_none()
    if credential is None:
        credential = PortalCredential(user_id=user.id)
        session.add(credential)

    credential.portal_user_name_encrypted = encrypt_secret(portal_user_name)
    credential.portal_password_encrypted = encrypt_secret(password)


def upsert_notice(session, user_id: int, payload: dict, synced_at: datetime) -> None:
    storage_notice_key = make_storage_notice_key(user_id, payload["portal_notice_key"])
    notice = session.execute(
        select(Notice).where(Notice.portal_notice_key == storage_notice_key)
    ).scalar_one_or_none()
    if notice is None:
        legacy_notice_key = make_storage_notice_key(
            user_id,
            make_notice_summary_key(payload["title"], payload["sender"], payload["published_on"]),
        )
        notice = session.execute(
            select(Notice).where(Notice.portal_notice_key == legacy_notice_key)
        ).scalar_one_or_none()
    content_hash = payload.get("content_hash") or make_notice_content_hash(payload)

    if notice is None:
        notice = Notice(user_id=user_id, portal_notice_key=storage_notice_key)
        session.add(notice)
    else:
        notice.portal_notice_key = storage_notice_key

    notice.user_id = user_id
    if notice.first_seen_at is None:
        notice.first_seen_at = synced_at
    if notice.content_updated_at is None:
        notice.content_updated_at = synced_at
    if notice.content_hash != content_hash:
        notice.content_updated_at = synced_at

    notice.title = payload["title"]
    notice.sender = payload["sender"]
    notice.category = payload["category"]
    notice.body = payload["body"]
    notice.source_tab_labels_json = json.dumps(payload.get("source_tab_labels", []), ensure_ascii=False)
    notice.detail_link_ids_json = json.dumps(payload.get("detail_link_ids", []), ensure_ascii=False)
    notice.content_hash = content_hash
    notice.published_on = payload["published_on"]
    notice.notice_starts_at = payload["notice_starts_at"]
    notice.notice_ends_at = payload["notice_ends_at"]
    notice.is_new = payload["is_new"]
    notice.is_important = payload["is_important"]
    notice.is_flagged = payload["is_flagged"]
    notice.is_read = payload["is_read"]
    notice.last_synced_at = synced_at
    notice.last_seen_at = synced_at


def upsert_timetable_entry(session, user_id: int, year: int, semester: str, campus: str, entry, synced_at: datetime) -> None:
    storage_timetable_key = make_storage_timetable_key(user_id, make_timetable_key(year, semester, campus, entry))
    row = session.execute(
        select(TimetableEntry).where(TimetableEntry.portal_timetable_key == storage_timetable_key)
    ).scalar_one_or_none()

    if row is None:
        row = TimetableEntry(user_id=user_id, portal_timetable_key=storage_timetable_key)
        session.add(row)

    row.user_id = user_id
    row.academic_year = year
    row.semester = semester
    row.campus = campus
    row.period = entry.period
    row.weekday = entry.weekday
    row.subject = entry.subject
    row.instructor = entry.instructor
    row.room = entry.room
    row.course_code = entry.course_code
    row.credits = entry.credits
    row.note = entry.note
    row.last_synced_at = synced_at


def delete_stale_timetable_entries(
    session,
    user_id: int,
    year: int,
    semester: str,
    campus: str,
    active_keys: set[str],
) -> None:
    rows = session.execute(
        select(TimetableEntry).where(
            TimetableEntry.user_id == user_id,
            TimetableEntry.academic_year == year,
            TimetableEntry.semester == semester,
            TimetableEntry.campus == campus,
        )
    ).scalars()
    for row in rows:
        if row.portal_timetable_key in active_keys:
            continue
        session.delete(row)


def sync_user(session_factory, user_id: int, portal_user_name: str, password: str) -> tuple[int, int]:
    client = PortalClient(user_name=portal_user_name, password=password)
    timetable = client.fetch_timetable()
    notices = client.fetch_notices()
    synced_at = datetime.now()

    with session_factory() as session:
        active_timetable_keys: set[str] = set()
        for entry in timetable.classes:
            storage_timetable_key = make_storage_timetable_key(user_id, make_timetable_key(timetable.year, timetable.semester, timetable.campus, entry))
            active_timetable_keys.add(storage_timetable_key)
            upsert_timetable_entry(
                session,
                user_id=user_id,
                year=timetable.year,
                semester=timetable.semester,
                campus=timetable.campus,
                entry=entry,
                synced_at=synced_at,
            )
        delete_stale_timetable_entries(
            session,
            user_id=user_id,
            year=timetable.year,
            semester=timetable.semester,
            campus=timetable.campus,
            active_keys=active_timetable_keys,
        )

        for notice_payload in notices.notices:
            if notice_payload["published_on"]:
                notice_payload["published_on"] = datetime.strptime(notice_payload["published_on"], "%Y-%m-%d").date()
            if notice_payload["notice_starts_at"]:
                notice_payload["notice_starts_at"] = datetime.fromisoformat(notice_payload["notice_starts_at"])
            if notice_payload["notice_ends_at"]:
                notice_payload["notice_ends_at"] = datetime.fromisoformat(notice_payload["notice_ends_at"])
            upsert_notice(session, user_id=user_id, payload=notice_payload, synced_at=synced_at)

        session.commit()

    return len(timetable.classes), len(notices.notices)


def main() -> int:
    load_dotenv()
    portal_user_name = require_env("USER_NAME")
    password = require_env("PASSWORD")
    session_factory = create_session_factory(get_database_url())

    with session_factory() as session:
        user = ensure_user(session, portal_user_name=portal_user_name)
        maybe_upsert_credential(session, user, portal_user_name=portal_user_name, password=password)
        user_id = user.id
        session.commit()

    timetable_count, notice_count = sync_user(
        session_factory,
        user_id=user_id,
        portal_user_name=portal_user_name,
        password=password,
    )

    print(f"Synced {timetable_count} timetable entries and {notice_count} notices")
    print(f"Database: {get_database_url()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
