from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    path = ROOT / "scripts/build_extension_results_tex.py"
    specification = importlib.util.spec_from_file_location(
        "build_extension_results_tex_test",
        path,
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def test_extension_builder_verifies_audited_outputs_and_emits_all_macros() -> None:
    builder = _load_builder()
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "extension_results.tex"
        previous = sys.argv
        try:
            sys.argv = ["build_extension_results_tex.py", "--output", str(output)]
            assert builder.main() == 0
        finally:
            sys.argv = previous
        text = output.read_text()
        assert r"\extensionsavailabletrue" in text
        assert r"\renewcommand{\RxSensitivityRows}" in text
        assert r"\renewcommand{\RxSensitivityCritical}" in text
        assert r"\renewcommand{\RxPersistenceStabilityChecks}" in text
        assert "2.199995" in text

