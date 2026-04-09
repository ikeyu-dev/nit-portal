#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from nit_portal.config import get_database_url, load_dotenv
from nit_portal.db import create_session_factory
from nit_portal.models import PortalCredential, User
from nit_portal.security import decrypt_secret
from sync_portal import sync_user


def main() -> int:
    load_dotenv()
    session_factory = create_session_factory(get_database_url())

    with session_factory() as session:
        users = session.execute(select(User).where(User.is_active.is_(True)).order_by(User.id.asc())).scalars().all()
        credentials_by_user_id = {
            credential.user_id: credential
            for credential in session.execute(select(PortalCredential)).scalars().all()
        }

    total_users = 0
    total_timetable_entries = 0
    total_notices = 0
    for user in users:
        credential = credentials_by_user_id.get(user.id)
        if credential is None:
            continue

        portal_user_name = decrypt_secret(credential.portal_user_name_encrypted)
        password = decrypt_secret(credential.portal_password_encrypted)
        timetable_count, notice_count = sync_user(
            session_factory=session_factory,
            user_id=user.id,
            portal_user_name=portal_user_name,
            password=password,
        )
        total_users += 1
        total_timetable_entries += timetable_count
        total_notices += notice_count
        print(f"[{user.id}] {user.display_name}: {timetable_count} timetable entries, {notice_count} notices")

    print(
        f"Synced {total_users} users, {total_timetable_entries} timetable entries, {total_notices} notices"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
