#!/usr/bin/env python3
"""Run post-analysis Rosenbaum and stable-persistence diagnostics with progress."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.experiment import (  # noqa: E402
    apply_exact_action,
    canonical_translation_c4,
    exact_invariant_features,
    kernel_from_features,
    load_well_array,
    resolve_well_records,
    sha256_file,
    write_json,
    zero_pad,
)
from cqoi.persistence import (  # noqa: E402
    bottleneck_distance_0d,
    l2_from_rbf_rkhs_distance,
    rbf_rkhs_distance,
    zero_dimensional_persistence,
)
from cqoi.progress import ProgressTracker  # noqa: E402
from cqoi.sensitivity import (  # noqa: E402
    critical_gamma,
    exact_paired_mmd_rosenbaum_bounds,
)
from cqoi.statistics import exact_paired_mmd_test  # noqa: E402


def _diagnostic_resize(image: np.ndarray, resolution: int) -> np.ndarray:
    if image.ndim != 2 or image.dtype != np.uint8:
        raise ValueError("diagnostic image must be a two-dimensional uint8 array.")
    resized = Image.fromarray(image).resize(
        (resolution, resolution),
        Image.Resampling.BOX,
    )
    return np.asarray(resized, dtype=np.float64) / 255.0


def _load_truth_lookup(path: Path, nuisance_seed: int) -> dict[tuple[str, int], dict]:
    frame = pd.read_csv(path)
    selected = frame.loc[frame["nuisance_seed"] == nuisance_seed]
    lookup: dict[tuple[str, int], dict] = {}
    for row in selected.to_dict(orient="records"):
        key = (str(row["well_id"]), int(row["site"]))
        if key in lookup:
            raise ValueError(f"Duplicate nuisance record for {key}.")
        lookup[key] = row
    return lookup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "data/manifests/selection_manifest.json",
    )
    parser.add_argument(
        "--amendment",
        type=Path,
        default=ROOT / "data/manifests/post_rxrx1_expert_review_extension.json",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT / "data/raw/rxrx1/rxrx1/metadata.csv",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=ROOT / "data/rxrx1_validation_subset",
    )
    parser.add_argument(
        "--nuisance-truth",
        type=Path,
        default=ROOT / "results/rxrx1/hidden_nuisance_truth_NOT_ANALYSIS.csv",
    )
    parser.add_argument(
        "--integrity-manifest",
        type=Path,
        default=ROOT / "data/manifests/rxrx1_subset_integrity.json",
    )
    parser.add_argument(
        "--original-results",
        type=Path,
        default=ROOT / "results/rxrx1/pair_seed_results.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/extensions",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=ROOT / "logs/progress_expert_review_extensions.json",
    )
    args = parser.parse_args()

    amendment = json.loads(args.amendment.read_text())
    if amendment.get("analysis_status") != "post_outcome_exploratory_extension":
        raise RuntimeError("The extension amendment must retain its post-outcome label.")
    sensitivity_plan = amendment["rosenbaum_sensitivity"]
    persistence_plan = amendment["persistence_diagnostic"]
    gamma_grid = [float(value) for value in sensitivity_plan["gamma_grid"]]
    nuisance_seed = int(persistence_plan["nuisance_seed"])
    resolution = int(persistence_plan["diagnostic_resolution"])
    epsilon = float(persistence_plan["perturbation_epsilon"])
    perturbation_seed = int(persistence_plan["perturbation_seed"])
    gaussian_bandwidth = float(persistence_plan["gaussian_bandwidth"])
    nuclear_channel = int(persistence_plan["nuclear_channel_zero_based"])

    selection = json.loads(args.selection.read_text())
    specs, records = resolve_well_records(
        selection,
        args.metadata,
        args.data_root,
        require_validation_experiments=8,
    )
    primary_pair = str(sensitivity_plan["primary_pair"])
    if primary_pair != str(persistence_plan["primary_pair"]):
        raise RuntimeError("Both extension analyses must use the same frozen pair.")
    if primary_pair not in {spec.pair_id for spec in specs}:
        raise RuntimeError(f"Unknown primary pair {primary_pair!r}.")
    primary_records = [record for record in records if record.pair_id == primary_pair]
    if len(primary_records) != 16:
        raise RuntimeError("The primary analysis must contain eight pairs (16 wells).")

    selection_digest = sha256_file(args.selection)
    expected_metadata_digest = str(
        selection.get("source_files", {}).get("metadata", {}).get("sha256", "")
    )
    if sha256_file(args.metadata) != expected_metadata_digest:
        raise RuntimeError("Metadata do not match the frozen selection manifest.")
    integrity = json.loads(args.integrity_manifest.read_text())
    if integrity.get("status") != "complete_crc_and_sha256_verified":
        raise RuntimeError("The RxRx1 image-integrity manifest is incomplete.")
    if integrity.get("selection_manifest_sha256") != selection_digest:
        raise RuntimeError("Image integrity and selection manifests disagree.")
    integrity_files = {
        str(item["path"]): item for item in integrity.get("files", [])
    }
    primary_paths = sorted(
        {
            Path(path)
            for record in primary_records
            for site_paths in record.site_paths
            for path in site_paths
        }
    )
    if len(primary_paths) != 192:
        raise RuntimeError("The primary extension must use exactly 192 PNG files.")

    total_steps = (
        len(primary_paths)
        + len(primary_records)
        + len(gamma_grid)
        + 2 * len(primary_records)
        + 5
    )
    tracker = ProgressTracker(
        "expert-review-extensions",
        total_steps,
        args.progress,
    )
    completed = 0
    for path in primary_paths:
        relative = path.resolve().relative_to(args.data_root.resolve()).as_posix()
        item = integrity_files.get(relative)
        if item is None:
            raise RuntimeError(f"Primary PNG is absent from integrity manifest: {relative}")
        if path.stat().st_size != int(item["bytes"]):
            raise RuntimeError(f"Primary PNG size mismatch: {relative}")
        if sha256_file(path) != str(item["sha256"]):
            raise RuntimeError(f"Primary PNG SHA-256 mismatch: {relative}")
        completed += 1
        tracker.update(completed, message=f"verified {relative}")

    clean_arrays: dict[str, np.ndarray] = {}
    for record in primary_records:
        clean_arrays[record.well_id] = zero_pad(
            load_well_array(record, image_size=64),
            padding=16,
        )
        completed += 1
        tracker.update(completed, message=f"loaded {record.well_id}")

    # The frozen loader stores the two condition members in label order.  For
    # this post-analysis audit, reconstruct the paired test in a label-blind,
    # pretreatment order and verify that its result equals the frozen result.
    # The accompanying theorem proves invariance to these within-pair flips.
    sensitivity_records = sorted(
        primary_records,
        key=lambda record: (record.experiment_number, record.well_id),
    )
    ordered_clean = [clean_arrays[record.well_id] for record in sensitivity_records]
    exact_features = exact_invariant_features(ordered_clean, canvas_size=96)
    kernel, bandwidth = kernel_from_features(exact_features)
    labels = np.asarray([record.label for record in sensitivity_records], dtype=int)
    pair_ids = np.asarray(
        [record.experiment_number for record in sensitivity_records],
        dtype=int,
    )
    exact_result = exact_paired_mmd_test(kernel, labels, pair_ids)
    original_frame = pd.read_csv(args.original_results)
    original_row = original_frame.loc[
        (original_frame["analysis"] == "observed")
        & (original_frame["method"] == "quotient_exact")
        & (original_frame["pair_id"] == primary_pair)
        & (original_frame["nuisance_seed"] == nuisance_seed)
    ]
    if len(original_row) != 1:
        raise RuntimeError("Could not uniquely recover the frozen primary result row.")
    original_record = original_row.iloc[0]
    if abs(exact_result["statistic"] - float(original_record["statistic"])) > 1e-12:
        raise RuntimeError("Reconstructed quotient statistic differs from frozen result.")
    if abs(exact_result["p_value"] - float(original_record["p_value"])) > 1e-14:
        raise RuntimeError("Reconstructed exact p-value differs from frozen result.")

    sensitivity_rows: list[dict] = []
    for gamma in gamma_grid:
        bounds = exact_paired_mmd_rosenbaum_bounds(
            kernel,
            labels,
            pair_ids,
            gamma,
        )
        sensitivity_rows.append(bounds)
        completed += 1
        tracker.update(
            completed,
            message=f"Rosenbaum exact bound Gamma={gamma:g}",
        )
    critical = critical_gamma(
        kernel,
        labels,
        pair_ids,
        alpha=float(sensitivity_plan["alpha"]),
        gamma_tolerance=float(
            sensitivity_plan["critical_gamma_bisection_tolerance"]
        ),
    )
    completed += 1
    tracker.update(completed, message="located Rosenbaum sensitivity crossing")

    truth_lookup = _load_truth_lookup(args.nuisance_truth, nuisance_seed)
    rng = np.random.default_rng(perturbation_seed)
    persistence_rows: list[dict] = []
    exact_array_checks = 0
    exact_diagram_checks = 0
    for record in primary_records:
        clean_well = clean_arrays[record.well_id]
        for site_index in range(2):
            truth_key = (record.well_id, site_index + 1)
            if truth_key not in truth_lookup:
                raise RuntimeError(f"Missing nuisance record for {truth_key}.")
            nuisance = truth_lookup[truth_key]
            contaminated_site = apply_exact_action(
                clean_well[site_index],
                quarter_turns=int(nuisance["quarter_turns"]),
                dy=int(nuisance["dy"]),
                dx=int(nuisance["dx"]),
            )
            canonical_clean = canonical_translation_c4(clean_well[site_index])
            canonical_contaminated = canonical_translation_c4(contaminated_site)
            array_equal = bool(np.array_equal(canonical_clean, canonical_contaminated))
            if not array_equal:
                raise RuntimeError(f"Exact canonical equality failed for {truth_key}.")
            exact_array_checks += 1

            diagnostic_clean = _diagnostic_resize(
                canonical_clean[nuclear_channel],
                resolution,
            )
            diagnostic_contaminated = _diagnostic_resize(
                canonical_contaminated[nuclear_channel],
                resolution,
            )
            clean_diagram = zero_dimensional_persistence(diagnostic_clean)
            contaminated_diagram = zero_dimensional_persistence(
                diagnostic_contaminated
            )
            exact_bottleneck = bottleneck_distance_0d(
                clean_diagram,
                contaminated_diagram,
            )
            if exact_bottleneck != 0.0:
                raise RuntimeError(f"Persistence invariance failed for {truth_key}.")
            exact_diagram_checks += 1

            noise = rng.uniform(-epsilon, epsilon, size=diagnostic_clean.shape)
            perturbed = np.clip(diagnostic_clean + noise, 0.0, 1.0)
            realized_difference = perturbed - diagnostic_clean
            perturbed_diagram = zero_dimensional_persistence(perturbed)
            bottleneck = bottleneck_distance_0d(clean_diagram, perturbed_diagram)
            sup_norm = float(np.max(np.abs(realized_difference)))
            l2_norm = float(np.linalg.norm(realized_difference))
            kernel_distance = rbf_rkhs_distance(
                diagnostic_clean,
                perturbed,
                gaussian_bandwidth,
            )
            recovered_l2 = l2_from_rbf_rkhs_distance(
                kernel_distance,
                gaussian_bandwidth,
            )
            tolerance = 2e-12
            if bottleneck > sup_norm + tolerance:
                raise RuntimeError(f"Bottleneck stability failed for {truth_key}.")
            if sup_norm > l2_norm + tolerance:
                raise RuntimeError(f"Norm ordering failed for {truth_key}.")
            if abs(l2_norm - recovered_l2) > tolerance:
                raise RuntimeError(f"Gaussian metric inversion failed for {truth_key}.")
            persistence_rows.append(
                {
                    "pair_id": primary_pair,
                    "experiment": record.experiment,
                    "well_id": record.well_id,
                    "label": record.label,
                    "site": site_index + 1,
                    "nuisance_seed": nuisance_seed,
                    "canonical_array_equal": array_equal,
                    "exact_action_bottleneck": exact_bottleneck,
                    "finite_bars": int(len(clean_diagram.finite)),
                    "essential_bars": int(len(clean_diagram.essential_births)),
                    "perturbation_epsilon": epsilon,
                    "realized_sup_norm": sup_norm,
                    "realized_l2_norm": l2_norm,
                    "perturbation_bottleneck": bottleneck,
                    "gaussian_bandwidth": gaussian_bandwidth,
                    "gaussian_rkhs_distance": kernel_distance,
                    "l2_recovered_from_rkhs": recovered_l2,
                    "bottleneck_le_sup_norm": bool(bottleneck <= sup_norm + tolerance),
                    "sup_norm_le_l2": bool(sup_norm <= l2_norm + tolerance),
                }
            )
            completed += 1
            tracker.update(
                completed,
                message=f"persistence invariance/stability {record.well_id} site {site_index + 1}",
            )

    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    sensitivity_path = output / "rosenbaum_sensitivity.csv"
    persistence_path = output / "persistence_stability.csv"
    sensitivity_summary_path = output / "rosenbaum_summary.json"
    persistence_summary_path = output / "persistence_summary.json"
    audit_path = output / "expert_review_extension_audit.json"

    pd.DataFrame(sensitivity_rows).to_csv(sensitivity_path, index=False)
    completed += 1
    tracker.update(completed, message="wrote Rosenbaum sensitivity table")
    pd.DataFrame(persistence_rows).to_csv(persistence_path, index=False)
    completed += 1
    tracker.update(completed, message="wrote persistence stability table")

    sensitivity_summary = {
        "analysis_status": amendment["analysis_status"],
        "primary_pair": primary_pair,
        "pairs": int(len(np.unique(pair_ids))),
        "observed_statistic": exact_result["statistic"],
        "exact_randomization_p_value": exact_result["p_value"],
        "permutations": exact_result["permutations"],
        "tail_event_assignments": int(sensitivity_rows[0]["event_assignments"]),
        "observed_assignment_bits": sensitivity_rows[0]["observed_bits"],
        "within_pair_order": "ascending_well_id_label_blind",
        "matches_frozen_condition_order_result": True,
        "feature_bandwidth": bandwidth,
        "critical_gamma": critical,
        "model": sensitivity_plan["model"],
    }
    write_json(sensitivity_summary_path, sensitivity_summary)
    persistence_frame = pd.DataFrame(persistence_rows)
    persistence_summary = {
        "analysis_status": amendment["analysis_status"],
        "primary_pair": primary_pair,
        "sites": int(len(persistence_frame)),
        "exact_canonical_array_checks_passed": exact_array_checks,
        "exact_persistence_invariance_checks_passed": exact_diagram_checks,
        "stability_checks_passed": int(
            persistence_frame["bottleneck_le_sup_norm"].sum()
        ),
        "kernel_link_checks_passed": int(
            persistence_frame["sup_norm_le_l2"].sum()
        ),
        "maximum_exact_action_bottleneck": float(
            persistence_frame["exact_action_bottleneck"].max()
        ),
        "maximum_perturbation_bottleneck": float(
            persistence_frame["perturbation_bottleneck"].max()
        ),
        "maximum_realized_sup_norm": float(
            persistence_frame["realized_sup_norm"].max()
        ),
        "diagnostic_resolution": resolution,
        "perturbation_epsilon": epsilon,
        "gaussian_bandwidth": gaussian_bandwidth,
    }
    write_json(persistence_summary_path, persistence_summary)
    completed += 1
    tracker.update(completed, message="wrote extension summaries")

    audit = {
        "analysis_status": amendment["analysis_status"],
        "amendment": {
            "path": str(args.amendment.resolve()),
            "sha256": sha256_file(args.amendment),
        },
        "frozen_inputs": {
            "selection_manifest_sha256": selection_digest,
            "metadata_sha256": sha256_file(args.metadata),
            "image_integrity_manifest_sha256": sha256_file(
                args.integrity_manifest
            ),
            "primary_image_files_verified": len(primary_paths),
            "nuisance_truth_sha256": sha256_file(args.nuisance_truth),
            "original_pair_results_sha256": sha256_file(args.original_results),
        },
        "implementation": {
            "runner_sha256": sha256_file(Path(__file__)),
            "sensitivity_module_sha256": sha256_file(
                ROOT / "src/cqoi/sensitivity.py"
            ),
            "persistence_module_sha256": sha256_file(
                ROOT / "src/cqoi/persistence.py"
            ),
            "frozen_experiment_module_sha256": sha256_file(
                ROOT / "src/cqoi/experiment.py"
            ),
            "frozen_invariants_module_sha256": sha256_file(
                ROOT / "src/cqoi/invariants.py"
            ),
            "frozen_statistics_module_sha256": sha256_file(
                ROOT / "src/cqoi/statistics.py"
            ),
            "python": sys.version,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "source_files": {},
        "outputs": {},
    }
    for path in (
        ROOT / "src/cqoi/experiment.py",
        ROOT / "src/cqoi/invariants.py",
        ROOT / "src/cqoi/statistics.py",
        ROOT / "src/cqoi/sensitivity.py",
        ROOT / "src/cqoi/persistence.py",
        ROOT / "scripts/run_expert_review_extensions.py",
    ):
        audit["source_files"][str(path.relative_to(ROOT))] = sha256_file(path)
    for path in (
        sensitivity_path,
        persistence_path,
        sensitivity_summary_path,
        persistence_summary_path,
    ):
        audit["outputs"][path.name] = {
            "path": str(path.resolve()),
            "sha256": sha256_file(path),
        }
    write_json(audit_path, audit)
    completed += 1
    tracker.update(completed, message="wrote extension audit and hashes")
    tracker.complete("post-analysis expert-review extensions completed")
    print(json.dumps({**sensitivity_summary, **persistence_summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
