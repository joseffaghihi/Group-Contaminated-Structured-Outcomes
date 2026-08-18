#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path


def fmt(seconds):
    if seconds is None or not math.isfinite(float(seconds)):
        return "--:--:--"
    seconds = max(0, int(round(float(seconds))))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def render(state: dict) -> str:
    fraction = float(state.get("fraction", 0.0))
    width = 32
    filled = int(round(width * fraction))
    bar = "█" * filled + "░" * (width - filled)
    return (
        f"[{bar}] {100*fraction:6.2f}%  "
        f"{state.get('completed', 0)}/{state.get('total', 0)}  "
        f"elapsed={fmt(state.get('elapsed_seconds'))}  "
        f"ETA={fmt(state.get('eta_seconds'))}  "
        f"failures={state.get('failures', 0)}  "
        f"status={state.get('status', 'unknown')}  "
        f"stage={state.get('stage', 'unknown')}\n"
        f"{state.get('message', '')}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor experiment progress and failures.")
    parser.add_argument("state", type=Path)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            state = json.loads(args.state.read_text())
            print("\033[2J\033[H" + render(state), flush=True)
            if args.once or state.get("status") in {"completed", "failed"}:
                return 1 if state.get("status") == "failed" else 0
        except FileNotFoundError:
            print(f"Waiting for progress state: {args.state}", flush=True)
            if args.once:
                return 2
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Transient monitor read error: {exc}", flush=True)
        time.sleep(max(0.5, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())

