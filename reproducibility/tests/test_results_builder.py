from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


def _load_builder():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/build_results_tex.py"
    specification = importlib.util.spec_from_file_location("build_results_tex", path)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module, root


def test_completed_results_require_every_paper_macro_and_no_pending() -> None:
    builder, root = _load_builder()
    main = root / "paper/main.tex"
    template = root / "paper/results_template.tex"
    required = builder._macro_names(
        main.read_text(), "providecommand"
    ) | builder._macro_names(template.read_text(), "renewcommand")
    generated = "\\resultsavailabletrue\n" + "\n".join(
        f"\\renewcommand{{\\{name}}}{{verified}}" for name in sorted(required)
    )
    builder._validate_macro_coverage(
        generated,
        main_tex=main,
        template_tex=template,
    )

    missing_one = generated.replace(
        f"\\renewcommand{{\\{sorted(required)[0]}}}{{verified}}\n",
        "",
    )
    try:
        builder._validate_macro_coverage(
            missing_one,
            main_tex=main,
            template_tex=template,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("Macro coverage validator accepted an omitted macro.")

    try:
        builder._validate_macro_coverage(
            generated + "\n\\pending\n",
            main_tex=main,
            template_tex=template,
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("Macro coverage validator accepted a pending value.")


def test_simulation_reproduction_hash_gate_rejects_changed_results() -> None:
    builder, root = _load_builder()
    reproduction = json.loads(
        (root / "results/simulation/reproduction_audit.json").read_text()
    )
    replicates = root / "results/simulation/simulation_replicates.csv"
    summary = root / "results/simulation/simulation_summary.csv"
    audit = root / "results/simulation/simulation_audit.json"
    builder._verify_simulation_reproduction(
        reproduction,
        replicates_path=replicates,
        summary_path=summary,
        audit_path=audit,
    )

    with tempfile.TemporaryDirectory() as directory:
        changed = Path(directory) / "simulation_summary.csv"
        changed.write_bytes(summary.read_bytes() + b"\n")
        try:
            builder._verify_simulation_reproduction(
                reproduction,
                replicates_path=replicates,
                summary_path=changed,
                audit_path=audit,
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("Reproduction gate accepted a changed summary CSV.")
