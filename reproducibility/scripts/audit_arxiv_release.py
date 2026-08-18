#!/usr/bin/env python3
"""Verify that the standalone arXiv source is tied to generated results.

This is a release-level audit, separate from the frozen 45-test scientific
analysis suite.  It prevents a manually edited submission from drifting away
from the machine-generated numerical inputs that the suite already validates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN_NAME = "group_contaminated_structured_outcomes_arxiv.tex"
GENERATED_INPUTS = {
    "results.tex": ROOT / "paper/results.tex",
    "extension_results.tex": ROOT / "paper/extension_results.tex",
}
REQUIRED_REFERENCES = {
    "SimTableRows",
    "RxCanonicalMMD",
    "RxCanonicalP",
    "RxReplicationRows",
    "RxAcquisitionNullRows",
    "RxApproximateStressRows",
    "RxSensitivityRows",
    "SoftwareTestsPassed",
}
FORBIDDEN_NAMES = {
    ".DS_Store",
    "__MACOSX",
}
FORBIDDEN_SUFFIXES = {
    ".aux",
    ".fdb_latexmk",
    ".fls",
    ".log",
    ".out",
    ".synctex.gz",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def macro_names(text: str, command: str) -> set[str]:
    pattern = re.compile(rf"\\{command}\s*\{{\\([A-Za-z@]+)\}}")
    return set(pattern.findall(text))


def audit(arxiv_dir: Path, *, compile_pdf: bool) -> dict[str, object]:
    errors: list[str] = []
    checks: list[str] = []
    main = arxiv_dir / MAIN_NAME
    if not main.is_file():
        raise FileNotFoundError(f"Missing arXiv main source: {main}")
    main_text = main.read_text(encoding="utf-8")

    for name, generated in GENERATED_INPUTS.items():
        candidate = arxiv_dir / name
        if not candidate.is_file():
            errors.append(f"missing generated input: {candidate}")
            continue
        if candidate.read_bytes() != generated.read_bytes():
            errors.append(f"arXiv {name} differs from generated {generated}")
        else:
            checks.append(f"{name}: byte-identical to generated analysis input")
        expected_input = rf"\IfFileExists{{{name}}}{{\input{{{name}}}}}{{}}"
        if expected_input not in main_text:
            errors.append(f"main source does not load {name} through the audited input")
        if r"\pending" in candidate.read_text(encoding="utf-8"):
            errors.append(f"pending value found in {name}")

    provided = macro_names(main_text, "providecommand")
    referenced = {name for name in REQUIRED_REFERENCES if rf"\{name}" in main_text}
    missing_references = REQUIRED_REFERENCES - referenced
    if missing_references:
        errors.append(
            "main source omits required generated macro references: "
            + ", ".join(sorted(missing_references))
        )
    else:
        checks.append("all critical table/result macros are referenced")
    missing_declarations = REQUIRED_REFERENCES - provided
    if missing_declarations:
        errors.append(
            "main source omits fallback declarations: "
            + ", ".join(sorted(missing_declarations))
        )

    arxiv_figure = arxiv_dir / "simulation_power.pdf"
    generated_figure = ROOT / "paper/figures/simulation_power.pdf"
    if not arxiv_figure.is_file() or not generated_figure.is_file():
        errors.append("simulation figure is missing from the arXiv or analysis tree")
    elif sha256(arxiv_figure) != sha256(generated_figure):
        errors.append("arXiv simulation figure differs from the generated analysis figure")
    else:
        checks.append("simulation_power.pdf: byte-identical to generated figure")

    for path in arxiv_dir.rglob("*"):
        if path.name in FORBIDDEN_NAMES or any(
            path.name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES
        ):
            errors.append(f"forbidden arXiv build artifact: {path.relative_to(arxiv_dir)}")

    compiled_sha256 = None
    if compile_pdf and not errors:
        executable = shutil.which("latexmk")
        if executable is None:
            errors.append("latexmk is unavailable for the requested compile audit")
        else:
            with tempfile.TemporaryDirectory(prefix="arxiv-release-audit-") as temporary:
                build_dir = Path(temporary)
                for source in arxiv_dir.iterdir():
                    if source.is_file():
                        shutil.copy2(source, build_dir / source.name)
                process = subprocess.run(
                    [
                        executable,
                        "-pdf",
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        MAIN_NAME,
                    ],
                    cwd=build_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if process.returncode:
                    errors.append(
                        "isolated arXiv compile failed:\n"
                        + process.stdout[-4000:]
                        + process.stderr[-4000:]
                    )
                else:
                    compiled = build_dir / MAIN_NAME.replace(".tex", ".pdf")
                    compiled_sha256 = sha256(compiled)
                    checks.append("isolated latexmk compilation passed")

    payload: dict[str, object] = {
        "status": "passed" if not errors else "failed",
        "arxiv_dir": str(arxiv_dir.resolve()),
        "checks": checks,
        "errors": errors,
        "compiled_pdf_sha256": compiled_sha256,
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--arxiv-dir",
        type=Path,
        default=ROOT / "paper/arxiv",
        help="directory containing the standalone arXiv source",
    )
    parser.add_argument(
        "--compile",
        action="store_true",
        help="also compile the source in a temporary isolated directory",
    )
    arguments = parser.parse_args()
    payload = audit(arguments.arxiv_dir, compile_pdf=arguments.compile)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
