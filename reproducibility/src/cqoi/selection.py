from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .progress import ProgressTracker


DISCOVERY_EXPERIMENTS = tuple(range(1, 13))
VALIDATION_EXPERIMENTS = tuple(range(17, 25))


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def experiment_number(name: str) -> int:
    return int(str(name).split("-")[-1])


def _as_experiment_tuple(values: Iterable[int]) -> tuple[int, ...]:
    result = tuple(int(value) for value in values)
    if len(result) != len(set(result)):
        raise ValueError("Experiment identifiers must be unique.")
    return result


def load_huvec_well_embeddings(
    metadata_path: str | Path,
    embeddings_path: str | Path,
    progress_path: str | Path,
    *,
    discovery_experiments: Sequence[int] = DISCOVERY_EXPERIMENTS,
    embedding_chunksize: int = 25_000,
) -> pd.DataFrame:
    """Load only discovery-site embeddings and aggregate the two sites per well."""

    discovery_experiments = _as_experiment_tuple(discovery_experiments)
    tracker = ProgressTracker("load-discovery-metadata", 5, progress_path)
    metadata = pd.read_csv(metadata_path)
    metadata["experiment_number"] = metadata["experiment"].map(experiment_number)
    discovery_metadata = metadata[
        (metadata["cell_type"] == "HUVEC")
        & (metadata["well_type"] == "treatment")
        & metadata["experiment_number"].isin(discovery_experiments)
    ].copy()
    if not discovery_metadata["site_id"].is_unique:
        raise ValueError("Discovery metadata contains duplicate site identifiers.")
    discovery_site_ids = set(discovery_metadata["site_id"])
    tracker.update(
        1,
        message=(
            f"discovery metadata sites={len(discovery_metadata):,}; "
            f"experiments={len(discovery_experiments)}"
        ),
    )

    # The public embeddings are one CSV. Reading it in chunks lets the selector
    # retain only rows whose site IDs belong to the discovery experiments.
    selected_chunks: list[pd.DataFrame] = []
    feature_columns: list[str] | None = None
    for chunk in pd.read_csv(embeddings_path, chunksize=embedding_chunksize):
        if feature_columns is None:
            feature_columns = [
                column for column in chunk.columns if column.startswith("feature_")
            ]
            if not feature_columns:
                raise ValueError("No feature_* columns were found in the embedding file.")
        selected = chunk[chunk["site_id"].isin(discovery_site_ids)]
        if not selected.empty:
            selected_chunks.append(selected[["site_id", *feature_columns]])
    if not selected_chunks or feature_columns is None:
        raise RuntimeError("No discovery embeddings matched the metadata.")
    embeddings = pd.concat(selected_chunks, ignore_index=True)
    if embeddings["site_id"].duplicated().any():
        raise ValueError("Embedding file contains duplicate discovery site identifiers.")
    tracker.update(
        2,
        message=f"retained discovery embeddings={len(embeddings):,}; features={len(feature_columns)}",
    )

    merged = discovery_metadata.merge(
        embeddings, on="site_id", how="left", validate="one_to_one"
    )
    missing_embeddings = int(merged[feature_columns].isna().all(axis=1).sum())
    if missing_embeddings:
        raise RuntimeError(
            f"{missing_embeddings} discovery sites have no embedding; selection aborted."
        )
    tracker.update(3, message=f"matched discovery sites={len(merged):,}")

    well_columns = [
        "well_id",
        "experiment",
        "experiment_number",
        "plate",
        "well",
        "sirna",
        "sirna_id",
    ]
    grouped = merged.groupby(well_columns, as_index=False, sort=True)
    wells = grouped[feature_columns].mean()
    site_counts = (
        merged.groupby(well_columns, as_index=False, sort=True)["site_id"]
        .nunique()
        .rename(columns={"site_id": "site_count"})
    )
    wells = wells.merge(site_counts, on=well_columns, validate="one_to_one")
    tracker.update(4, message=f"aggregated discovery wells={len(wells):,}")

    # Robust normalization is computed separately inside each discovery batch
    # using all non-control discovery wells, without consulting validation data.
    normalized_parts: list[pd.DataFrame] = []
    for _, frame in wells.groupby("experiment", sort=True):
        values = frame[feature_columns].to_numpy(dtype=np.float64)
        center = np.median(values, axis=0)
        scale = np.median(np.abs(values - center), axis=0) * 1.4826
        scale[scale < 1e-6] = 1.0
        normalized = frame.copy()
        normalized.loc[:, feature_columns] = (values - center) / scale
        normalized_parts.append(normalized)
    result = pd.concat(normalized_parts, ignore_index=True)
    tracker.complete(message="discovery-only well aggregation and normalization complete")
    return result


def _complete_treatment_table(
    metadata: pd.DataFrame,
    experiments: Sequence[int],
) -> pd.DataFrame:
    experiments = _as_experiment_tuple(experiments)
    frame = metadata.copy()
    if "experiment_number" not in frame:
        frame["experiment_number"] = frame["experiment"].map(experiment_number)
    frame = frame[
        (frame["cell_type"] == "HUVEC")
        & (frame["well_type"] == "treatment")
        & frame["experiment_number"].isin(experiments)
    ].copy()

    grouped = frame.groupby(
        ["sirna_id", "sirna", "experiment", "experiment_number"],
        as_index=False,
        sort=True,
    ).agg(
        site_count=("site_id", "nunique"),
        well_count=("well_id", "nunique"),
        plate_count=("plate", "nunique"),
        plate=("plate", "first"),
        well=("well", "first"),
    )
    return grouped


def _plate_signatures(
    complete: pd.DataFrame,
    eligible_ids: set[int],
    all_experiments: Sequence[int],
) -> dict[int, tuple[int, ...]]:
    all_experiments = _as_experiment_tuple(all_experiments)
    signatures: dict[int, tuple[int, ...]] = {}
    for sirna_id, frame in complete[complete["sirna_id"].isin(eligible_ids)].groupby(
        "sirna_id", sort=True
    ):
        frame = frame.sort_values("experiment_number")
        observed = tuple(int(value) for value in frame["experiment_number"])
        if observed != all_experiments:
            continue
        signatures[int(sirna_id)] = tuple(int(value) for value in frame["plate"])
    return signatures


def _leave_one_out_direction_agreement(left: np.ndarray, right: np.ndarray) -> float:
    agreements: list[float] = []
    for held_out in range(left.shape[0]):
        keep = np.arange(left.shape[0]) != held_out
        training_direction = left[keep].mean(axis=0) - right[keep].mean(axis=0)
        held_out_difference = left[held_out] - right[held_out]
        agreements.append(float(np.dot(training_direction, held_out_difference) > 0.0))
    return float(np.mean(agreements))


def select_discovery_pairs(
    wells: pd.DataFrame,
    metadata: pd.DataFrame,
    *,
    discovery_experiments: Sequence[int] = DISCOVERY_EXPERIMENTS,
    validation_experiments: Sequence[int] = VALIDATION_EXPERIMENTS,
    pair_count: int = 10,
) -> dict:
    """Select disjoint, plate-compatible pairs without validation outcomes.

    The score is split-half robust. For each candidate pair, a signal-to-noise
    ratio is computed separately in experiments 1--6 and 7--12. The pair score is
    the smaller half-specific ratio multiplied by the nonnegative cosine agreement
    of the two half-specific effect directions. Candidates are sorted by this
    score and selected greedily subject to disjointness. All ties are resolved by
    ascending integer siRNA IDs.
    """

    discovery_experiments = _as_experiment_tuple(discovery_experiments)
    validation_experiments = _as_experiment_tuple(validation_experiments)
    if len(discovery_experiments) < 4 or len(discovery_experiments) % 2:
        raise ValueError("Discovery experiments must have an even size of at least four.")
    if pair_count < 1:
        raise ValueError("pair_count must be positive.")

    feature_columns = [column for column in wells if column.startswith("feature_")]
    if not feature_columns:
        raise ValueError("No discovery feature columns were supplied.")
    discovery = wells[
        wells["experiment_number"].isin(discovery_experiments)
        & (wells["site_count"] == 2)
    ].copy()

    # Candidate eligibility and plate grouping are functions of discovery rows
    # only. Confirmation metadata are deliberately excluded from pair selection.
    complete_metadata = _complete_treatment_table(metadata, discovery_experiments)
    complete_metadata = complete_metadata[
        (complete_metadata["site_count"] == 2)
        & (complete_metadata["well_count"] == 1)
        & (complete_metadata["plate_count"] == 1)
    ].copy()

    required_discovery = len(discovery_experiments)
    discovery_counts = discovery.groupby("sirna_id")["experiment_number"].nunique()
    metadata_discovery_counts = (
        complete_metadata[
            complete_metadata["experiment_number"].isin(discovery_experiments)
        ]
        .groupby("sirna_id")["experiment_number"]
        .nunique()
    )
    eligible_ids = {
        int(sirna_id)
        for sirna_id, count in discovery_counts.items()
        if count == required_discovery
        and int(metadata_discovery_counts.get(sirna_id, 0)) == required_discovery
    }
    if len(eligible_ids) < 2 * pair_count:
        raise RuntimeError(
            f"Only {len(eligible_ids)} complete siRNAs are eligible for {pair_count} pairs."
        )

    all_experiments = discovery_experiments
    signatures = _plate_signatures(complete_metadata, eligible_ids, all_experiments)
    eligible_ids &= set(signatures)

    arrays: dict[int, np.ndarray] = {}
    sirna_names: dict[int, str] = {}
    for sirna_id, frame in discovery[discovery["sirna_id"].isin(eligible_ids)].groupby(
        "sirna_id", sort=True
    ):
        frame = frame.sort_values("experiment_number")
        observed = tuple(int(value) for value in frame["experiment_number"])
        if observed != discovery_experiments:
            continue
        identifier = int(sirna_id)
        arrays[identifier] = frame[feature_columns].to_numpy(dtype=np.float64)
        sirna_names[identifier] = str(frame["sirna"].iloc[0])
    eligible_ids &= set(arrays)

    half = len(discovery_experiments) // 2
    summary: dict[int, dict[str, np.ndarray | float]] = {}
    for sirna_id in sorted(eligible_ids):
        x = arrays[sirna_id]
        first, second = x[:half], x[half:]
        mean_first = first.mean(axis=0)
        mean_second = second.mean(axis=0)
        noise_first = float(np.mean(np.sum((first - mean_first) ** 2, axis=1)))
        noise_second = float(np.mean(np.sum((second - mean_second) ** 2, axis=1)))
        summary[sirna_id] = {
            "mean_first": mean_first,
            "mean_second": mean_second,
            "noise_first": noise_first,
            "noise_second": noise_second,
        }

    by_plate_signature: dict[tuple[int, ...], list[int]] = {}
    for sirna_id in sorted(eligible_ids):
        by_plate_signature.setdefault(signatures[sirna_id], []).append(sirna_id)

    epsilon = 1e-12
    candidates: list[tuple[float, float, float, float, int, int]] = []
    for group_ids in by_plate_signature.values():
        for left_position, left in enumerate(group_ids):
            left_summary = summary[left]
            for right in group_ids[left_position + 1 :]:
                right_summary = summary[right]
                delta_first = (
                    left_summary["mean_first"] - right_summary["mean_first"]
                )
                delta_second = (
                    left_summary["mean_second"] - right_summary["mean_second"]
                )
                signal_first = float(np.dot(delta_first, delta_first))
                signal_second = float(np.dot(delta_second, delta_second))
                snr_first = signal_first / (
                    float(left_summary["noise_first"])
                    + float(right_summary["noise_first"])
                    + epsilon
                )
                snr_second = signal_second / (
                    float(left_summary["noise_second"])
                    + float(right_summary["noise_second"])
                    + epsilon
                )
                cosine = float(
                    np.dot(delta_first, delta_second)
                    / np.sqrt((signal_first + epsilon) * (signal_second + epsilon))
                )
                stable_score = min(snr_first, snr_second) * max(cosine, 0.0)
                mean_snr = 0.5 * (snr_first + snr_second)
                candidates.append(
                    (
                        stable_score,
                        min(snr_first, snr_second),
                        cosine,
                        mean_snr,
                        left,
                        right,
                    )
                )

    # Descending scientific scores, then ascending integer identifiers.
    candidates.sort(
        key=lambda value: (
            -value[0],
            -value[1],
            -value[2],
            -value[3],
            value[4],
            value[5],
        )
    )
    selected: list[dict] = []
    used: set[int] = set()
    for stable_score, minimum_snr, cosine, mean_snr, left, right in candidates:
        if left in used or right in used:
            continue
        if stable_score <= 0.0:
            continue
        plate_by_experiment = {
            f"HUVEC-{experiment:02d}": int(plate)
            for experiment, plate in zip(all_experiments, signatures[left], strict=True)
        }
        if signatures[left] != signatures[right]:
            raise AssertionError("Internal error: a selected pair crosses plate groups.")
        selected.append(
            {
                "pair_index": len(selected) + 1,
                "role": "primary" if not selected else "replication",
                "sirna_ids": [left, right],
                "sirnas": [sirna_names[left], sirna_names[right]],
                "discovery_split_half_stable_score": float(stable_score),
                "discovery_minimum_half_snr": float(minimum_snr),
                "discovery_mean_half_snr": float(mean_snr),
                "discovery_half_direction_cosine": float(cosine),
                "discovery_leave_one_experiment_out_direction_agreement": (
                    _leave_one_out_direction_agreement(arrays[left], arrays[right])
                ),
                "plate_by_experiment": plate_by_experiment,
            }
        )
        used.update((left, right))
        if len(selected) == pair_count:
            break

    if len(selected) != pair_count:
        raise RuntimeError(
            f"Only {len(selected)} disjoint positive-score pairs could be selected."
        )

    flattened_ids = [
        sirna_id for pair in selected for sirna_id in pair["sirna_ids"]
    ]
    if len(flattened_ids) != len(set(flattened_ids)):
        raise AssertionError("Selected pairs are not disjoint.")

    return {
        "schema_version": "2.0",
        "status": "frozen_discovery_only_before_validation_image_analysis",
        "cell_type": "HUVEC",
        "well_type": "treatment",
        "experimental_unit": "well",
        "sites_per_well": 2,
        "channels_per_site": 6,
        "discovery_experiments": list(discovery_experiments),
        "validation_experiments": list(validation_experiments),
        "pair_count": pair_count,
        "primary_pair": selected[0],
        "replication_pairs": selected[1:],
        "selected_pairs": selected,
        "selected_sirna_ids": flattened_ids,
        "eligible_sirna_count": int(len(eligible_ids)),
        "plate_signature_group_sizes": sorted(
            len(group) for group in by_plate_signature.values()
        ),
        "feature_count": int(len(feature_columns)),
        "selection_algorithm": {
            "name": "split-half robust same-plate greedy matching",
            "site_aggregation": "arithmetic mean of the two site embeddings per well",
            "normalization": (
                "within each discovery experiment, feature-wise median centering and "
                "MAD scaling (1.4826 multiplier; scales below 1e-6 set to 1)"
            ),
            "eligibility": (
                "non-control HUVEC siRNA with exactly two sites in every discovery "
                "experiment and the same discovery plate signature as its pair"
            ),
            "discovery_halves": [
                list(discovery_experiments[:half]),
                list(discovery_experiments[half:]),
            ],
            "score": (
                "min(SNR_half_1,SNR_half_2) * max(cos(delta_half_1,"
                "delta_half_2),0)"
            ),
            "half_snr": (
                "squared Euclidean distance between treatment centroids divided by "
                "the sum of the two within-treatment mean squared residual norms"
            ),
            "matching": (
                "sort all within-plate-signature candidates by descending stable "
                "score, minimum half-SNR, direction cosine, and mean half-SNR; "
                "break ties by ascending integer IDs; greedily accept disjoint pairs"
            ),
        },
        "random_seed": 20260731,
        "preprocessing": {
            "raw_image_shape": [512, 512],
            "channels": [1, 2, 3, 4, 5, 6],
            "validation_site_aggregation": (
                "the two sites remain repeated measurements and are aggregated to "
                "one well-level outcome before inference"
            ),
        },
        "statistical_plan": {
            "primary_test": (
                "orbit-kernel MMD for the primary pair with all 2^8=256 "
                "within-experiment treatment-label swaps"
            ),
            "replication_tests": (
                "the same exact paired randomization test for nine frozen pairs"
            ),
            "multiplicity": "Holm familywise correction at alpha=0.05 for replications",
            "confidence_intervals": (
                "10,000 experiment-level paired bootstrap resamples for effect sizes; "
                "exact randomization p-values are primary"
            ),
            "nuisance_seed": 20260731,
            "nuisance_robustness_seeds": list(range(20260731, 20260751)),
        },
        "validation_metadata_used_for_selection": False,
        "validation_metadata_fields_used_for_selection": [],
        "validation_embeddings_used_for_selection": False,
        "validation_image_outcomes_used_for_selection": False,
        "expected_validation_wells": int(
            pair_count * 2 * len(validation_experiments)
        ),
        "expected_validation_sites": int(
            pair_count * 2 * len(validation_experiments) * 2
        ),
        "expected_validation_png_files": int(
            pair_count * 2 * len(validation_experiments) * 2 * 6
        ),
    }


def write_manifest(manifest: dict, path: str | Path) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    digest = sha256_file(path)
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n")
    return digest
