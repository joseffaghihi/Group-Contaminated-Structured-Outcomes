#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.remote_zip import list_remote_zip


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="https://storage.googleapis.com/rxrx/rxrx1/rxrx1-images.zip",
    )
    parser.add_argument("--contains", default="HUVEC-01/Plate1")
    parser.add_argument("--limit", type=int, default=24)
    args = parser.parse_args()
    matches = [name for name in list_remote_zip(args.url) if args.contains in name]
    for name in matches[: args.limit]:
        print(name)
    print(f"matching members: {len(matches)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

