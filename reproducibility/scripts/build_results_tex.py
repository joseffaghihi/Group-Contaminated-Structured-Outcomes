#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FROZEN_RX_CONFIG = {
    "image_size": 64,
    "padding": 16,
    "max_integer_shift": 8,
    "bootstrap_replicates": 10_000,
    "bootstrap_seed": 926_031,
    "ect_levels": 25,
    "ect_min_component_size": 4,
    "nuclear_channel": 0,
    "invariance_tolerance": 1e-12,
    "approximate_angles": [5.0, 10.0, 20.0],
    "approximate_crop_pixels": 2,
    "approximate_noise_sd": 2.0,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _tex_text(value: object) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


def _number(value: float) -> str:
    return f"{float(value):.4f}"


def _interval(lower: float, upper: float) -> str:
    return f"({_number(lower)}, {_number(upper)})"


def _renew(name: str, value: str) -> str:
    return rf"\renewcommand{{\{name}}}{{{value}}}"


def _load_completed_json(path: Path) -> dict:
    payload = json.loads(path.read_text())
    if payload.get("status") != "completed":
        raise RuntimeError(f"Required analysis is not completed: {path}")
    return payload


def _verify_sidecar(path: Path, *, label: str) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(f"Missing {label} SHA-256 sidecar: {sidecar}")
    fields = sidecar.read_text().strip().split()
    if not fields:
        raise RuntimeError(f"Empty {label} SHA-256 sidecar: {sidecar}")
    expected = fields[0].lower()
    observed = _sha256(path)
    if expected != observed:
        raise RuntimeError(
            f"{label} SHA-256 mismatch: expected {expected}, observed {observed}."
        )
    return observed


def _verify_rx_output_hashes(rx_audit: dict, supplied: dict[str, Path]) -> None:
    recorded = rx_audit.get("outputs", {}).get("files", {})
    for key, path in supplied.items():
        item = recorded.get(key)
        if not isinstance(item, dict) or "sha256" not in item:
            raise RuntimeError(f"RxRx1 audit lacks an output hash for {key}.")
        observed = _sha256(path)
        if observed != str(item["sha256"]):
            raise RuntimeError(
                f"RxRx1 output hash mismatch for {key}: "
                f"expected {item['sha256']}, observed {observed}."
            )


def _verify_simulation_reproduction(
    reproduction: dict,
    *,
    replicates_path: Path,
    summary_path: Path,
    audit_path: Path,
) -> None:
    if reproduction.get("status") != "passed":
        raise RuntimeError("Independent simulation reproduction did not pass.")
    comparisons = reproduction.get("comparisons", {})
    targets = {
        "simulation_replicates_csv": replicates_path,
        "simulation_summary_csv": summary_path,
        "simulation_audit_json": audit_path,
    }
    for key, path in targets.items():
        comparison = comparisons.get(key, {})
        if key == "simulation_audit_json":
            if not comparison.get("normalized_structurally_identical", False):
                raise RuntimeError(
                    "Independent simulation audit JSON reproduction differs "
                    "beyond timestamps and output paths."
                )
        elif not comparison.get("byte_identical", False):
            raise RuntimeError(f"Independent simulation reproduction failed for {key}.")
        if comparison.get("original_sha256") != _sha256(path):
            raise RuntimeError(
                f"Current simulation artifact differs from the independently "
                f"reproduced frozen artifact: {path}."
            )


def _method_label(method: str) -> str:
    labels = {
        "quotient_exact": "Exact quotient",
        "raw_coordinates": "Raw pixels",
        "moment_registration": "Moment registration",
        "euler_secondary": "Finite Euler signature",
    }
    if method not in labels:
        raise ValueError(f"Unknown analysis method {method!r}.")
    return labels[method]


def _macro_names(text: str, command: str) -> set[str]:
    import re

    return set(
        re.findall(
            rf"\\{command}\{{\\([A-Za-z@]+)\}}",
            text,
        )
    )


def _validate_macro_coverage(
    generated: str,
    *,
    main_tex: Path,
    template_tex: Path,
) -> None:
    required = _macro_names(main_tex.read_text(), "providecommand")
    required |= _macro_names(template_tex.read_text(), "renewcommand")
    emitted = _macro_names(generated, "renewcommand")
    missing = sorted(required - emitted)
    if missing:
        raise RuntimeError(
            "Generated results omit paper macros: " + ", ".join(missing)
        )
    if r"\pending" in generated:
        raise RuntimeError("Generated completed results still contain \\pending.")
    if r"\resultsavailabletrue" not in generated:
        raise RuntimeError("Completed results must set \\resultsavailabletrue.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build paper/results.tex only from completed, audited simulation and "
            "RxRx1 result files; includes all nine frozen secondary contrasts."
        )
    )
    parser.add_argument(
        "--simulation-summary",
        type=Path,
        default=ROOT / "results/simulation/simulation_summary.csv",
    )
    parser.add_argument(
        "--simulation-replicates",
        type=Path,
        default=ROOT / "results/simulation/simulation_replicates.csv",
    )
    parser.add_argument(
        "--simulation-audit",
        type=Path,
        default=ROOT / "results/simulation/simulation_audit.json",
    )
    parser.add_argument(
        "--simulation-reproduction-audit",
        type=Path,
        default=ROOT / "results/simulation/reproduction_audit.json",
    )
    parser.add_argument(
        "--rx-results",
        type=Path,
        default=ROOT / "results/rxrx1/pair_seed_results.csv",
    )
    parser.add_argument(
        "--rx-summary",
        type=Path,
        default=ROOT / "results/rxrx1/experiment_summary.json",
    )
    parser.add_argument(
        "--rx-acquisition-null-summary",
        type=Path,
        default=(
            ROOT
            / "results/rxrx1/acquisition_null_false_positive_summary.csv"
        ),
    )
    parser.add_argument(
        "--rx-approximate-stress",
        type=Path,
        default=ROOT / "results/rxrx1/approximate_action_stress.csv",
    )
    parser.add_argument(
        "--rx-equivalence",
        type=Path,
        default=ROOT / "results/rxrx1/clean_contaminated_equivalence.csv",
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "data/manifests/selection_manifest.json",
    )
    parser.add_argument(
        "--tests-progress",
        type=Path,
        default=ROOT / "logs/progress_tests.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "paper/results.tex",
    )
    args = parser.parse_args()

    simulation_audit = _load_completed_json(args.simulation_audit)
    simulation_reproduction = json.loads(
        args.simulation_reproduction_audit.read_text()
    )
    _verify_simulation_reproduction(
        simulation_reproduction,
        replicates_path=args.simulation_replicates,
        summary_path=args.simulation_summary,
        audit_path=args.simulation_audit,
    )
    rx_audit = _load_completed_json(args.rx_summary)
    tests = _load_completed_json(args.tests_progress)
    selection = json.loads(args.selection.read_text())
    simulation = pd.read_csv(args.simulation_summary)
    rx = pd.read_csv(args.rx_results)
    acquisition_null = pd.read_csv(args.rx_acquisition_null_summary)
    approximate_stress = pd.read_csv(args.rx_approximate_stress)
    equivalence = pd.read_csv(args.rx_equivalence)

    manifest_hash = _verify_sidecar(args.selection, label="selection manifest")
    if rx_audit["manifest"]["sha256"] != manifest_hash:
        raise RuntimeError("RxRx1 audit and supplied selection manifest disagree.")
    frozen_seeds = [
        int(value)
        for value in selection["statistical_plan"]["nuisance_robustness_seeds"]
    ]
    if [int(value) for value in rx_audit["config"]["nuisance_seeds"]] != frozen_seeds:
        raise RuntimeError("RxRx1 nuisance seeds do not match the sealed manifest.")
    observed_rx_config = dict(rx_audit["config"])
    nuisance_config = observed_rx_config.pop("nuisance_seeds", None)
    if nuisance_config is None:
        raise RuntimeError("RxRx1 audit omits the nuisance-seed sequence.")
    if observed_rx_config != FROZEN_RX_CONFIG:
        raise RuntimeError(
            "RxRx1 audit configuration differs from the frozen paper protocol: "
            f"{observed_rx_config}."
        )
    if not bool(rx_audit["exact_invariance_gate"]["all_passed"]):
        raise RuntimeError("Cannot publish results after an exact-invariance failure.")
    _verify_rx_output_hashes(
        rx_audit,
        {
            "pair_seed_results": args.rx_results,
            "acquisition_null_false_positive_summary": (
                args.rx_acquisition_null_summary
            ),
            "approximate_action_stress": args.rx_approximate_stress,
            "clean_contaminated_equivalence": args.rx_equivalence,
        },
    )
    source_hashes = rx_audit.get("software", {}).get("source_sha256", {})
    current_source_paths = {
        "experiment.py": ROOT / "src/cqoi/experiment.py",
        "invariants.py": ROOT / "src/cqoi/invariants.py",
        "statistics.py": ROOT / "src/cqoi/statistics.py",
    }
    for name, path in current_source_paths.items():
        if source_hashes.get(name) != _sha256(path):
            raise RuntimeError(
                f"Current {name} differs from the source recorded by the RxRx1 run."
            )

    seed = int(selection["statistical_plan"]["nuisance_seed"])
    pair_specs = rx_audit["pair_specs"]
    primary = next(pair for pair in pair_specs if pair["role"] == "primary")
    replications = [pair for pair in pair_specs if pair["role"] != "primary"]
    if len(replications) != 9:
        raise RuntimeError(
            f"Expected nine frozen secondary pairs, found {len(replications)}."
        )
    primary_rows = rx[
        (rx["analysis"] == "observed")
        & (rx["nuisance_seed"] == seed)
        & (rx["pair_id"] == primary["pair_id"])
    ].set_index("method")
    required_methods = {
        "quotient_exact",
        "euler_secondary",
        "raw_coordinates",
        "moment_registration",
    }
    if not required_methods.issubset(primary_rows.index):
        raise RuntimeError("Primary RxRx1 result rows are incomplete.")

    def primary_values(method: str) -> tuple[str, str, str]:
        row = primary_rows.loc[method]
        if pd.isna(row.get("bootstrap_ci_lower")) or pd.isna(
            row.get("bootstrap_ci_upper")
        ):
            raise RuntimeError(f"Missing primary bootstrap interval for {method}.")
        return (
            _number(row["statistic"]),
            _interval(row["bootstrap_ci_lower"], row["bootstrap_ci_upper"]),
            _number(row["p_value"]),
        )

    canonical = primary_values("quotient_exact")
    euler = primary_values("euler_secondary")
    raw = primary_values("raw_coordinates")
    moment = primary_values("moment_registration")

    replication_frame = rx[
        (rx["analysis"] == "observed")
        & (rx["nuisance_seed"] == seed)
        & (rx["method"] == "quotient_exact")
        & (rx["role"] != "primary")
    ].set_index("pair_id")
    if len(replication_frame) != 9:
        raise RuntimeError(
            "Canonical secondary-contrast table does not contain nine rows."
        )
    replication_lines = []
    adjusted_significant = 0
    for index, pair in enumerate(replications, start=1):
        row = replication_frame.loc[pair["pair_id"]]
        adjusted = float(row["holm_replication_p"])
        adjusted_significant += int(adjusted <= 0.05)
        conditions = (
            rf"\texttt{{{_tex_text(pair['left_name'])}}} versus "
            rf"\texttt{{{_tex_text(pair['right_name'])}}}"
        )
        replication_lines.append(
            f"{index} & {conditions} & {_number(row['statistic'])} & "
            f"{_number(row['p_value'])} & {_number(adjusted)}\\\\"
        )
    replication_macro = "%\n" + "\n".join(replication_lines) + "\n"

    null_effect = float(simulation["effect_size"].min())
    alternative_effect = float(simulation["effect_size"].max())
    configured_effects = [
        float(value) for value in simulation_audit["config"]["effect_sizes"]
    ]
    if configured_effects != [0.0, 0.35, 0.70, 1.0]:
        raise RuntimeError(
            "Completed paper inputs must use the frozen effects 0, 0.35, 0.70, 1."
        )
    if sorted(simulation["effect_size"].unique().tolist()) != sorted(
        configured_effects
    ):
        raise RuntimeError("Simulation table does not contain every configured effect.")

    def simulation_row(method: str, effect: float) -> pd.Series:
        rows = simulation[
            (simulation["method"] == method)
            & (simulation["effect_size"] == effect)
        ]
        if len(rows) != 1:
            raise RuntimeError(
                f"Expected one simulation summary for {method}, effect={effect}."
            )
        return rows.iloc[0]

    sim_raw_null = simulation_row("raw_coordinates", null_effect)
    sim_quotient_null = simulation_row("quotient_exact", null_effect)
    sim_euler_null = simulation_row("euler_secondary", null_effect)
    sim_raw_power = simulation_row("raw_coordinates", alternative_effect)
    sim_quotient_power = simulation_row("quotient_exact", alternative_effect)
    sim_euler_power = simulation_row("euler_secondary", alternative_effect)
    simulation_methods = (
        "quotient_exact",
        "raw_coordinates",
        "moment_registration",
        "euler_secondary",
    )
    simulation_lines: list[str] = []
    rx_method_order = (
        "quotient_exact",
        "euler_secondary",
        "moment_registration",
        "raw_coordinates",
    )
    for method in simulation_methods:
        effect_rows = [
            simulation_row(method, effect)
            for effect in configured_effects
        ]
        null = effect_rows[0]
        null_cell = (
            f"{_number(null['rejection_fraction'])} "
            f"{_interval(null['clopper_pearson_95_lower'], null['clopper_pearson_95_upper'])}"
        )
        alternative_cells = [
            _number(row["rejection_fraction"]) for row in effect_rows[1:]
        ]
        permutations = {int(row["exact_permutations"]) for row in effect_rows}
        expected_permutations = 2 ** int(
            simulation_audit["config"]["experiment_pairs"]
        )
        if permutations != {expected_permutations}:
            raise RuntimeError(f"Wrong exact permutation count for {method}.")
        simulation_lines.append(
            " & ".join(
                [
                    _method_label(method),
                    null_cell,
                    *alternative_cells,
                    str(expected_permutations),
                ]
            )
            + r"\\"
        )
    simulation_macro = "%\n" + "\n".join(simulation_lines) + "\n"

    source_paths = [
        ROOT / "src/cqoi/experiment.py",
        ROOT / "src/cqoi/simulation.py",
        ROOT / "src/cqoi/statistics.py",
        ROOT / "scripts/run_rxrx1_experiment.py",
        ROOT / "scripts/run_simulation.py",
    ]
    source_fingerprint = hashlib.sha256(
        "".join(_sha256(path) for path in source_paths).encode("ascii")
    ).hexdigest()[:12]
    test_count = int(tests["total"])
    quotient_replication_holm_min = float(
        replication_frame["holm_replication_p"].min()
    )
    euler_replication_holm_min = float(
        rx[
            (rx["analysis"] == "observed")
            & (rx["nuisance_seed"] == seed)
            & (rx["method"] == "euler_secondary")
            & (rx["role"] != "primary")
        ]["holm_replication_p"].min()
    )
    invariant_trials = (
        len(rx_audit["config"]["nuisance_seeds"])
        * len(rx_audit["pair_specs"])
        * 2
        * len(selection["validation_experiments"])
        * 2
    )
    invariant_failures = 0 if rx_audit["exact_invariance_gate"]["all_passed"] else 1
    sim_invariance = simulation_audit["invariance_audit"]

    null_required_columns = {
        "method",
        "false_positives",
        "tests",
        "false_positive_fraction",
        "clopper_pearson_95_lower",
        "clopper_pearson_95_upper",
    }
    if not null_required_columns.issubset(acquisition_null.columns):
        missing = sorted(null_required_columns - set(acquisition_null.columns))
        raise RuntimeError(f"Acquisition-null summary lacks columns: {missing}")
    acquisition_lines: list[str] = []
    for method in rx_method_order:
        rows = acquisition_null[acquisition_null["method"] == method]
        if len(rows) != 1:
            raise RuntimeError(
                f"Expected one acquisition-null summary for {method}."
            )
        row = rows.iloc[0]
        fraction_with_descriptive_interval = (
            f"{_number(row['false_positive_fraction'])} "
            f"{_interval(row['clopper_pearson_95_lower'], row['clopper_pearson_95_upper'])}"
        )
        acquisition_lines.append(
            f"{_method_label(method)} & {int(row['tests'])} & "
            f"{int(row['false_positives'])} & "
            f"{fraction_with_descriptive_interval}\\\\"
        )
    acquisition_lines.append(
        r"\multicolumn{4}{p{0.92\linewidth}}{\footnotesize "
        r"Parentheses give exact binomial Clopper--Pearson intervals as "
        r"descriptive summaries only; pair--seed tests share biological blocks "
        r"and are not independent Bernoulli trials.}\\"
    )
    acquisition_macro = "%\n" + "\n".join(acquisition_lines) + "\n"

    condition_labels = {
        "rotation_5": r"Rotation \(5^\circ\)",
        "rotation_10": r"Rotation \(10^\circ\)",
        "rotation_20": r"Rotation \(20^\circ\)",
        "crop": "Two-pixel support crop",
        "noise": "Within-support Gaussian noise",
    }
    stress_required_columns = {
        "condition",
        "method",
        "relative_feature_error",
        "absolute_statistic_change",
        "absolute_p_value_change",
        "interpretation",
    }
    if not stress_required_columns.issubset(approximate_stress.columns):
        missing = sorted(stress_required_columns - set(approximate_stress.columns))
        raise RuntimeError(f"Approximate-action table lacks columns: {missing}")
    if set(approximate_stress["interpretation"]) != {
        "approximate-action robustness; not exact invariance"
    }:
        raise RuntimeError("Approximate-action rows have an invalid interpretation.")
    stress_lines: list[str] = []
    for condition, condition_label in condition_labels.items():
        for method in rx_method_order:
            rows = approximate_stress[
                (approximate_stress["condition"] == condition)
                & (approximate_stress["method"] == method)
            ]
            if len(rows) != 1:
                raise RuntimeError(
                    f"Expected one approximate-action row for {condition}/{method}."
                )
            row = rows.iloc[0]
            stress_lines.append(
                f"{condition_label} & {_method_label(method)} & "
                f"{_number(row['relative_feature_error'])} & "
                f"{_number(row['absolute_statistic_change'])} & "
                f"{_number(row['absolute_p_value_change'])}\\\\"
            )
    stress_macro = "%\n" + "\n".join(stress_lines) + "\n"

    equivalence_required = {
        "exact_invariance_gate_pass",
        "quotient_exact_max_abs_feature_error",
        "euler_secondary_max_abs_feature_error",
        "quotient_exact_max_abs_mmd2_difference",
        "quotient_exact_max_abs_p_value_difference",
    }
    if not equivalence_required.issubset(equivalence.columns):
        missing = sorted(equivalence_required - set(equivalence.columns))
        raise RuntimeError(f"Exact-equivalence table lacks columns: {missing}")
    if not equivalence["exact_invariance_gate_pass"].eq(True).all():
        raise RuntimeError("Exact-equivalence table contains a failed seed.")
    maximum_quotient_feature_error = float(
        equivalence["quotient_exact_max_abs_feature_error"].max()
    )
    maximum_euler_feature_error = float(
        equivalence["euler_secondary_max_abs_feature_error"].max()
    )
    maximum_quotient_statistic_error = float(
        equivalence["quotient_exact_max_abs_mmd2_difference"].max()
    )
    maximum_quotient_p_error = float(
        equivalence["quotient_exact_max_abs_p_value_difference"].max()
    )

    macros = [
        "% Generated by scripts/build_results_tex.py; do not edit manually.",
        f"% source fingerprint: {source_fingerprint}",
        r"\resultsavailabletrue",
        _renew("SoftwareCommit", f"source-{source_fingerprint}"),
        _renew("SoftwareTestsPassed", str(test_count)),
        "",
        _renew("SimNullReplicates", str(int(sim_raw_null["replicates"]))),
        _renew(
            "SimAlternativeReplicates",
            str(
                int(sim_raw_power["replicates"])
                * (len(configured_effects) - 1)
            ),
        ),
        _renew(
            "SimReplicatesPerEffect",
            str(int(simulation_audit["config"]["replicates"])),
        ),
        _renew(
            "SimBlocks",
            str(int(simulation_audit["config"]["experiment_pairs"])),
        ),
        _renew(
            "SimPermutationCount",
            str(2 ** int(simulation_audit["config"]["experiment_pairs"])),
        ),
        _renew(
            "SimEffectSizes",
            ", ".join(f"{effect:g}" for effect in configured_effects),
        ),
        _renew("SimInvariantAuditTrials", str(sim_invariance["trials"])),
        _renew("SimInvariantAuditFailures", str(sim_invariance["failures"])),
        _renew("SimRawTypeI", _number(sim_raw_null["rejection_fraction"])),
        _renew(
            "SimRawTypeICI",
            _interval(
                sim_raw_null["clopper_pearson_95_lower"],
                sim_raw_null["clopper_pearson_95_upper"],
            ),
        ),
        _renew(
            "SimCanonicalTypeI",
            _number(sim_quotient_null["rejection_fraction"]),
        ),
        _renew(
            "SimCanonicalTypeICI",
            _interval(
                sim_quotient_null["clopper_pearson_95_lower"],
                sim_quotient_null["clopper_pearson_95_upper"],
            ),
        ),
        _renew("SimEulerTypeI", _number(sim_euler_null["rejection_fraction"])),
        _renew(
            "SimEulerTypeICI",
            _interval(
                sim_euler_null["clopper_pearson_95_lower"],
                sim_euler_null["clopper_pearson_95_upper"],
            ),
        ),
        _renew("SimRawPower", _number(sim_raw_power["rejection_fraction"])),
        _renew(
            "SimCanonicalPower",
            _number(sim_quotient_power["rejection_fraction"]),
        ),
        _renew("SimEulerPower", _number(sim_euler_power["rejection_fraction"])),
        _renew("SimTableRows", simulation_macro),
        "",
        _renew("RxTreatmentA", rf"\texttt{{{_tex_text(primary['left_name'])}}}"),
        _renew("RxTreatmentB", rf"\texttt{{{_tex_text(primary['right_name'])}}}"),
        _renew("RxDiscoveryBatches", str(len(selection["discovery_experiments"]))),
        _renew(
            "RxConfirmationBatches",
            str(len(selection["validation_experiments"])),
        ),
        _renew("RxSelectedPairs", str(len(pair_specs))),
        _renew("RxReplicationPairs", str(len(replications))),
        _renew("RxConfirmationBlocks", str(len(selection["validation_experiments"]))),
        _renew("RxPlateAudit", "passed for all frozen pairs and blocks"),
        _renew("RxManifestHash", manifest_hash),
        _renew("RxPermutationCount", "256"),
        _renew("RxCanonicalMMD", canonical[0]),
        _renew("RxCanonicalMMDCI", canonical[1]),
        _renew("RxCanonicalP", canonical[2]),
        _renew("RxEulerMMD", euler[0]),
        _renew("RxEulerMMDCI", euler[1]),
        _renew("RxEulerP", euler[2]),
        _renew("RxRawMMD", raw[0]),
        _renew("RxRawMMDCI", raw[1]),
        _renew("RxRawP", raw[2]),
        _renew("RxMomentMMD", moment[0]),
        _renew("RxMomentMMDCI", moment[1]),
        _renew("RxMomentP", moment[2]),
        _renew("RxHolmCanonicalP", _number(quotient_replication_holm_min)),
        _renew("RxHolmEulerP", _number(euler_replication_holm_min)),
        _renew("RxInvariantAuditTrials", str(invariant_trials)),
        _renew("RxInvariantAuditFailures", str(invariant_failures)),
        _renew(
            "RxBootstrapReplicates",
            str(rx_audit["config"]["bootstrap_replicates"]),
        ),
        _renew("RxNuisanceSeeds", str(len(rx_audit["config"]["nuisance_seeds"]))),
        _renew("RxReplicationRows", replication_macro),
        _renew(
            "RxReplicationSummary",
            (
                f"{adjusted_significant} of the nine frozen secondary contrasts "
                "remained significant after Holm adjustment."
            ),
        ),
        _renew("RxAcquisitionNullRows", acquisition_macro),
        _renew("RxApproximateStressRows", stress_macro),
        _renew(
            "RxMaxQuotientFeatureError",
            _number(maximum_quotient_feature_error),
        ),
        _renew(
            "RxMaxEulerFeatureError",
            _number(maximum_euler_feature_error),
        ),
        _renew(
            "RxMaxQuotientStatisticError",
            _number(maximum_quotient_statistic_error),
        ),
        _renew("RxMaxQuotientPError", _number(maximum_quotient_p_error)),
        "",
        _renew(
            "AbstractSimulationResult",
            (
                "Under the sharp null, the maximal-invariant test rejected in "
                f"{_number(sim_quotient_null['rejection_fraction'])} of replicates; "
                f"at effect strength {_number(alternative_effect)}, its power was "
                f"{_number(sim_quotient_power['rejection_fraction'])}."
            ),
        ),
        _renew(
            "AbstractRxResult",
            (
                "For the primary RxRx1 contrast, the canonical quotient "
                "comparison gave an enumerated paired-swap "
                f"\\(p\\)-value of {canonical[2]}."
            ),
        ),
    ]
    text = "\n".join(macros) + "\n"
    _validate_macro_coverage(
        text,
        main_tex=ROOT / "paper/main.tex",
        template_tex=ROOT / "paper/results_template.tex",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(text)
    temporary.replace(args.output)
    print(
        json.dumps(
            {
                "status": "completed",
                "output": str(args.output.resolve()),
                "sha256": _sha256(args.output),
                "replication_rows": len(replication_lines),
                "simulation_rows": len(simulation_lines),
                "acquisition_null_rows": len(acquisition_lines) - 1,
                "approximate_action_rows": len(stress_lines),
                "source_fingerprint": source_fingerprint,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
