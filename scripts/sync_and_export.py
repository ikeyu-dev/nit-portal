#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import export_public_data
import sync_portal


def main() -> int:
    sync_portal.main()
    export_public_data.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
