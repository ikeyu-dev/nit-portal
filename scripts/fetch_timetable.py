#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from nit_portal.config import load_dotenv, require_env
from nit_portal.portal_client import PortalClient


def main() -> int:
    load_dotenv()
    client = PortalClient(require_env("USER_NAME"), require_env("PASSWORD"))
    payload = client.fetch_timetable()
    json.dump(
        {
            "metadata": {
                "title": payload.title,
                "year": payload.year,
                "semester": payload.semester,
                "campus": payload.campus,
                "campus_periods": payload.campus_periods,
            },
            "classes": [asdict(entry) for entry in payload.classes],
        },
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
