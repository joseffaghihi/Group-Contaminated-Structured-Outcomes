#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import inspect
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.progress import ProgressTracker


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> int:
    modules = [load_module(path) for path in sorted((ROOT / "tests").glob("test_*.py"))]
    tests = [
        (module.__name__, name, function)
        for module in modules
        for name, function in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_")
    ]
    tracker = ProgressTracker("unit-tests", len(tests), ROOT / "logs/progress_tests.json")
    failures = []
    for index, (module_name, name, function) in enumerate(tests, start=1):
        try:
            function()
            message = f"PASS {module_name}.{name}"
        except Exception:
            failures.append((module_name, name, traceback.format_exc()))
            message = f"FAIL {module_name}.{name}"
        tracker.state.failures = len(failures)
        tracker.update(index, message=message)
    if failures:
        tracker.fail(f"{len(failures)} test(s) failed")
        for module_name, name, trace in failures:
            print(f"\n{module_name}.{name}\n{trace}", file=sys.stderr)
        return 1
    tracker.complete(f"{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

