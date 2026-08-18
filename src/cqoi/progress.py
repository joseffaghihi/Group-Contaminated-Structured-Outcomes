from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


def _format_seconds(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds):
        return "--:--:--"
    seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class ProgressState:
    stage: str
    completed: int
    total: int
    started_at: float
    updated_at: float
    status: str = "running"
    failures: int = 0
    message: str = ""

    @property
    def fraction(self) -> float:
        return 0.0 if self.total <= 0 else min(1.0, self.completed / self.total)

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, self.updated_at - self.started_at)

    @property
    def eta_seconds(self) -> float | None:
        if self.completed <= 0 or self.total <= 0:
            return None
        rate = self.completed / max(self.elapsed_seconds, 1e-12)
        return (self.total - self.completed) / rate if rate > 0 else None


class ProgressTracker:
    """Terminal progress bar plus an atomically updated machine-readable state."""

    def __init__(
        self,
        stage: str,
        total: int,
        state_path: str | Path,
        *,
        min_interval_seconds: float = 0.25,
    ) -> None:
        now = time.time()
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state = ProgressState(stage, 0, int(total), now, now)
        self.min_interval_seconds = min_interval_seconds
        self._last_print = 0.0
        self._write_and_print(force=True)

    def update(self, completed: int | None = None, *, advance: int = 0, message: str = "") -> None:
        if completed is None:
            completed = self.state.completed + advance
        self.state.completed = min(max(0, int(completed)), self.state.total)
        self.state.updated_at = time.time()
        self.state.message = message
        self._write_and_print(force=self.state.completed == self.state.total)

    def fail(self, message: str) -> None:
        self.state.updated_at = time.time()
        self.state.status = "failed"
        self.state.failures += 1
        self.state.message = message
        self._write_and_print(force=True)

    def complete(self, message: str = "") -> None:
        self.state.completed = self.state.total
        self.state.updated_at = time.time()
        self.state.status = "completed"
        self.state.message = message
        self._write_and_print(force=True)

    def _write_and_print(self, *, force: bool) -> None:
        payload = asdict(self.state)
        payload.update(
            fraction=self.state.fraction,
            elapsed_seconds=self.state.elapsed_seconds,
            eta_seconds=self.state.eta_seconds,
        )
        temporary = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        os.replace(temporary, self.state_path)

        now = time.time()
        if force or now - self._last_print >= self.min_interval_seconds:
            width = 28
            filled = int(round(width * self.state.fraction))
            # ASCII keeps progress output portable on Windows consoles whose
            # default encoding cannot represent block-drawing characters.
            bar = "#" * filled + "-" * (width - filled)
            percent = 100.0 * self.state.fraction
            line = (
                f"\r[{bar}] {percent:6.2f}% "
                f"{self.state.completed}/{self.state.total} "
                f"elapsed={_format_seconds(self.state.elapsed_seconds)} "
                f"ETA={_format_seconds(self.state.eta_seconds)} "
                f"failures={self.state.failures} "
                f"stage={self.state.stage}"
            )
            if self.state.message:
                line += f" | {self.state.message}"
            stream = sys.stderr if self.state.status == "failed" else sys.stdout
            print(line, end="\n" if force else "", flush=True, file=stream)
            self._last_print = now

