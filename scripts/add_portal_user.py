#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from nit_portal.config import get_database_url, load_dotenv, require_env
from nit_portal.db import create_session_factory
from nit_portal.models import PortalCredential
from nit_portal.security import encrypt_secret
from sync_portal import ensure_user


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--portal-user-name", required=True)
    parser.add_argument("--active", action="store_true", default=False)
    args = parser.parse_args()

    load_dotenv()
    password = require_env("TARGET_PORTAL_PASSWORD")
    create_session = create_session_factory(get_database_url())

    with create_session() as session:
        user = ensure_user(session, portal_user_name=args.portal_user_name, display_name=args.display_name)
        user.is_active = args.active or user.is_active

        credential = session.execute(
            select(PortalCredential).where(PortalCredential.user_id == user.id)
        ).scalar_one_or_none()
        if credential is None:
            credential = PortalCredential(user_id=user.id)
            session.add(credential)

        credential.portal_user_name_encrypted = encrypt_secret(args.portal_user_name)
        credential.portal_password_encrypted = encrypt_secret(password)
        session.commit()

    print(f"Saved portal user: {args.portal_user_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
