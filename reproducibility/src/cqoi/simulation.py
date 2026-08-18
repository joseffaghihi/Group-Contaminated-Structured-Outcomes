from __future__ import annotations

import math
import os
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from .experiment import (
    ExperimentConfig,
    apply_exact_action,
    compute_method_features,
    derive_hidden_nuisance,
    exact_invariant_features,
    kernel_from_features,
    morphology_score,
    write_json,
    zero_pad,
)
from .progress import ProgressTracker
from .statistics import clopper_pearson, exact_paired_mmd_test


@dataclass(frozen=True)
class SimulationConfig:
    replicates: int = 250
    experiment_pairs: int = 8
    image_size: int = 28
    padding: int = 8
    max_integer_shift: int = 5
    effect_sizes: tuple[float, ...] = (0.0, 0.35, 0.70, 1.0)
    alpha: float = 0.05
    seed: int = 51_907
    invariance_audit_trials: int = 1000
    ect_levels: int = 25
    ect_min_component_size: int = 4
    nuclear_channel: int = 0

    def validate(self) -> None:
        if self.replicates < 1:
            raise ValueError("replicates must be positive.")
        if self.experiment_pairs != 8:
            raise ValueError(
                "The frozen benchmark uses eight experiment pairs and exactly 2^8 swaps."
            )
        if self.padding < self.max_integer_shift:
            raise ValueError("padding must be at least max_integer_shift.")
        if not self.effect_sizes or self.effect_sizes[0] != 0.0:
            raise ValueError("effect_sizes must begin with the sharp-null value 0.")
        if not 0 < self.alpha < 1:
            raise ValueError("alpha must be in (0,1).")
        if self.invariance_audit_trials < 1:
            raise ValueError("invariance_audit_trials must be positive.")
        if self.ect_levels < 2:
            raise ValueError("ect_levels must be at least two.")
        if self.ect_min_component_size < 1:
            raise ValueError("ect_min_component_size must be positive.")
        if not 0 <= self.nuclear_channel < 6:
            raise ValueError("nuclear_channel must be one of the six channels.")


def _disk(
    yy: np.ndarray,
    xx: np.ndarray,
    center_y: float,
    center_x: float,
    radius: float,
) -> np.ndarray:
    return (yy - center_y) ** 2 + (xx - center_x) ** 2 <= radius**2


def _ring(
    yy: np.ndarray,
    xx: np.ndarray,
    center_y: float,
    center_x: float,
    inner_radius: float,
    outer_radius: float,
) -> np.ndarray:
    distance2 = (yy - center_y) ** 2 + (xx - center_x) ** 2
    return (distance2 >= inner_radius**2) & (distance2 <= outer_radius**2)


def _synthetic_well(
    *,
    rng: np.random.Generator,
    shared_parameters: dict[str, float],
    effect_size: float,
    label: int,
    image_size: int,
) -> np.ndarray:
    yy, xx = np.mgrid[:image_size, :image_size]
    output = np.zeros((2, 6, image_size, image_size), dtype=np.float64)
    for site in range(2):
        site_jitter_y, site_jitter_x = rng.normal(0.0, 0.45, size=2)
        center_y = shared_parameters["center_y"] + site_jitter_y
        center_x = shared_parameters["center_x"] + site_jitter_x
        radius = max(2.0, shared_parameters["radius"] + rng.normal(0.0, 0.25))
        body = _disk(yy, xx, center_y, center_x, radius)
        satellite = _disk(
            yy,
            xx,
            center_y + shared_parameters["satellite_dy"] + rng.normal(0.0, 0.2),
            center_x + shared_parameters["satellite_dx"] + rng.normal(0.0, 0.2),
            max(1.2, 0.35 * radius),
        )
        active_support = body | satellite
        for channel in range(6):
            channel_scale = 75.0 + 18.0 * channel + rng.normal(0.0, 4.0)
            output[site, channel, body] = channel_scale
            output[site, channel, satellite] = 0.75 * channel_scale
            noise = rng.normal(0.0, 8.0, size=(image_size, image_size))
            output[site, channel, active_support] += noise[active_support]

        if label == 1 and effect_size > 0:
            treatment_ring = _ring(
                yy,
                xx,
                center_y,
                center_x,
                inner_radius=max(1.0, 0.38 * radius),
                outer_radius=max(1.8, 0.67 * radius),
            )
            amplitude = 125.0 * effect_size
            output[site, 0, treatment_ring] += amplitude
            output[site, 1, treatment_ring] += 0.65 * amplitude
            output[site, 4, treatment_ring] += 0.35 * amplitude
    return np.clip(np.rint(output), 0, 255).astype(np.uint8)


def synthetic_potential_well(
    *,
    unit_seed: int,
    shared_parameters: dict[str, float],
    treatment: int,
    effect_size: float,
    image_size: int,
) -> np.ndarray:
    """Frozen potential outcome for one unit under a specified treatment."""
    if treatment not in (0, 1):
        raise ValueError("treatment must equal zero or one.")
    return _synthetic_well(
        rng=np.random.default_rng(unit_seed),
        shared_parameters=shared_parameters,
        effect_size=effect_size,
        label=treatment,
        image_size=image_size,
    )


def generate_simulation_replicate(
    *,
    replicate_seed: int,
    effect_size: float,
    config: SimulationConfig,
) -> tuple[list[np.ndarray], np.ndarray, np.ndarray]:
    rng = np.random.default_rng(replicate_seed)
    clean: list[np.ndarray] = []
    labels: list[int] = []
    experiment_ids: list[int] = []
    unit_ids: list[str] = []
    for experiment in range(config.experiment_pairs):
        shared = {
            "center_y": (config.image_size - 1) / 2 + rng.normal(0.0, 1.2),
            "center_x": (config.image_size - 1) / 2 + rng.normal(0.0, 1.2),
            "radius": rng.uniform(4.0, 6.5),
            "satellite_dy": rng.uniform(-5.0, 5.0),
            "satellite_dx": rng.uniform(-5.0, 5.0),
        }
        unit_seeds = rng.integers(
            0,
            np.iinfo(np.uint32).max,
            size=2,
            dtype=np.uint32,
        )
        assignment_bit = int(rng.integers(0, 2))
        assigned_labels = (assignment_bit, 1 - assignment_bit)
        for unit, (unit_seed, label) in enumerate(
            zip(unit_seeds, assigned_labels, strict=True)
        ):
            clean.append(
                zero_pad(
                    synthetic_potential_well(
                        unit_seed=int(unit_seed),
                        shared_parameters=shared,
                        treatment=label,
                        effect_size=effect_size,
                        image_size=config.image_size,
                    ),
                    config.padding,
                )
            )
            labels.append(label)
            experiment_ids.append(experiment)
            unit_ids.append(f"sim-{replicate_seed}-block-{experiment}-unit-{unit}")

    morphology = np.asarray(
        [
            [morphology_score(array[site]) for site in range(2)]
            for array in clean
        ]
    )
    pooled_median = float(np.median(morphology))
    contaminated: list[np.ndarray] = []
    for array, label, site_scores, experiment, unit_id in zip(
        clean,
        labels,
        morphology,
        experiment_ids,
        unit_ids,
        strict=True,
    ):
        transformed_sites = []
        for site in range(2):
            quarter_turns, dy, dx = derive_hidden_nuisance(
                well_id=f"{unit_id}|site={site + 1}",
                label=label,
                morphology=float(site_scores[site]),
                pooled_median=pooled_median,
                seed=replicate_seed + 10_003,
                max_shift=config.max_integer_shift,
            )
            transformed_sites.append(
                apply_exact_action(
                    array[site],
                    quarter_turns=quarter_turns,
                    dy=dy,
                    dx=dx,
                )
            )
        contaminated.append(np.stack(transformed_sites, axis=0))
    return (
        contaminated,
        np.asarray(labels, dtype=int),
        np.asarray(experiment_ids, dtype=int),
    )


def simulate_one(
    *,
    replicate_seed: int,
    effect_size: float,
    config: SimulationConfig,
    methods: Sequence[str] = (
        "quotient_exact",
        "raw_coordinates",
        "moment_registration",
        "euler_secondary",
    ),
) -> list[dict[str, Any]]:
    arrays, labels, experiment_ids = generate_simulation_replicate(
        replicate_seed=replicate_seed,
        effect_size=effect_size,
        config=config,
    )
    experiment_config = ExperimentConfig(
        image_size=config.image_size,
        padding=config.padding,
        max_integer_shift=config.max_integer_shift,
        nuisance_seeds=(replicate_seed,),
        bootstrap_replicates=1,
        ect_levels=config.ect_levels,
        ect_min_component_size=config.ect_min_component_size,
        nuclear_channel=config.nuclear_channel,
    )
    feature_map = compute_method_features(arrays, experiment_config)
    rows: list[dict[str, Any]] = []
    for method in methods:
        kernel, bandwidth = kernel_from_features(feature_map[method])
        result = exact_paired_mmd_test(kernel, labels, experiment_ids)
        rows.append(
            {
                "replicate_seed": int(replicate_seed),
                "effect_size": float(effect_size),
                "method": method,
                "statistic": result["statistic"],
                "p_value": result["p_value"],
                "permutations": result["permutations"],
                "bandwidth": bandwidth,
                "rejected": bool(result["p_value"] <= config.alpha),
            }
        )
    return rows


def calibration_small_seed_set(
    seeds: Sequence[int] = tuple(range(12)),
    *,
    image_size: int = 20,
) -> dict[str, Any]:
    config = SimulationConfig(
        replicates=len(seeds),
        image_size=image_size,
        padding=6,
        max_integer_shift=4,
        effect_sizes=(0.0,),
    )
    rows = [
        row
        for seed in seeds
        for row in simulate_one(
            replicate_seed=90_000 + int(seed),
            effect_size=0.0,
            config=config,
            methods=("quotient_exact",),
        )
    ]
    rejections = sum(bool(row["rejected"]) for row in rows)
    return {
        "seeds": [int(seed) for seed in seeds],
        "tests": len(rows),
        "rejections": int(rejections),
        "rejection_fraction": rejections / max(len(rows), 1),
        "p_values": [float(row["p_value"]) for row in rows],
    }


def run_invariance_audit(
    *,
    trials: int,
    image_size: int,
    padding: int,
    max_integer_shift: int,
    seed: int,
    progress_callback: Any | None = None,
) -> dict[str, Any]:
    """Bytewise product-action audit of the implemented maximal invariant."""
    rng = np.random.default_rng(seed)
    canvas_size = image_size + 2 * padding
    failures: list[dict[str, int]] = []
    for trial in range(trials):
        well = np.zeros((2, 6, canvas_size, canvas_size), dtype=np.uint8)
        for site in range(2):
            support_height = int(rng.integers(max(3, image_size // 3), image_size + 1))
            support_width = int(rng.integers(max(3, image_size // 3), image_size + 1))
            y0 = padding + (image_size - support_height) // 2
            x0 = padding + (image_size - support_width) // 2
            support = rng.integers(
                1,
                256,
                size=(6, support_height, support_width),
                dtype=np.uint8,
            )
            well[site, :, y0 : y0 + support_height, x0 : x0 + support_width] = support
        transformed_sites = []
        for site in range(2):
            transformed_sites.append(
                apply_exact_action(
                    well[site],
                    quarter_turns=int(rng.integers(0, 4)),
                    dy=int(rng.integers(-max_integer_shift, max_integer_shift + 1)),
                    dx=int(rng.integers(-max_integer_shift, max_integer_shift + 1)),
                )
            )
        transformed = np.stack(transformed_sites, axis=0)
        reference = exact_invariant_features([well], canvas_size)
        candidate = exact_invariant_features([transformed], canvas_size)
        if not np.array_equal(reference, candidate):
            failures.append({"trial": trial})
        if progress_callback is not None:
            progress_callback(trial + 1)
    return {
        "trials": int(trials),
        "failures": int(len(failures)),
        "failure_records": failures,
        "bytewise_equal_for_all_trials": not failures,
    }


def _plot_power(summary: pd.DataFrame, output_directory: Path) -> list[str]:
    os.environ.setdefault("MPLCONFIGDIR", str(output_directory / ".mplconfig"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_directory.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    labels = {
        "quotient_exact": "Exact quotient",
        "raw_coordinates": "Raw pixels",
        "moment_registration": "Moment alignment",
        "euler_secondary": "Euler secondary",
    }
    for method, group in summary.groupby("method", sort=False):
        group = group.sort_values("effect_size")
        axis.plot(
            group["effect_size"],
            group["rejection_fraction"],
            marker="o",
            linewidth=2,
            label=labels.get(method, method),
        )
    axis.axhline(0.05, linestyle="--", linewidth=1, color="black", label="Nominal 0.05")
    axis.set_ylim(0.0, 1.02)
    axis.set_xlabel("Intrinsic morphological effect strength")
    axis.set_ylabel("Paired-swap rejection fraction")
    axis.set_title("Paired structured-outcome simulation: size and power")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.tight_layout()
    png = output_directory / "simulation_power.png"
    pdf = output_directory / "simulation_power.pdf"
    figure.savefig(png, dpi=180)
    figure.savefig(pdf)
    plt.close(figure)
    return [str(png), str(pdf)]


def run_simulation_study(
    *,
    output_directory: str | Path,
    figure_directory: str | Path,
    progress_path: str | Path,
    config: SimulationConfig,
) -> dict[str, Any]:
    config.validate()
    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)
    simulation_total = config.replicates * len(config.effect_sizes)
    total = config.invariance_audit_trials + simulation_total
    tracker = ProgressTracker("simulation", total, progress_path)
    seed_sequence = np.random.SeedSequence(config.seed)
    child_sequences = seed_sequence.spawn(simulation_total)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    completed = 0

    try:
        audit = run_invariance_audit(
            trials=config.invariance_audit_trials,
            image_size=config.image_size,
            padding=config.padding,
            max_integer_shift=config.max_integer_shift,
            seed=config.seed + 7_919,
            progress_callback=lambda trial: tracker.update(
                trial,
                message=(
                    f"bytewise product-action audit "
                    f"{trial}/{config.invariance_audit_trials}"
                ),
            ),
        )
        completed = config.invariance_audit_trials
        if audit["failures"]:
            raise RuntimeError(
                f"Product-action invariance audit had {audit['failures']} failures."
            )
        simulation_index = 0
        for effect_size in config.effect_sizes:
            for replicate in range(config.replicates):
                replicate_seed = int(
                    child_sequences[simulation_index].generate_state(
                        1, dtype=np.uint64
                    )[0]
                )
                try:
                    replicate_rows = simulate_one(
                        replicate_seed=replicate_seed,
                        effect_size=effect_size,
                        config=config,
                    )
                    for row in replicate_rows:
                        row["replicate"] = replicate
                    rows.extend(replicate_rows)
                except Exception as error:
                    failures.append(
                        {
                            "effect_size": effect_size,
                            "replicate": replicate,
                            "replicate_seed": replicate_seed,
                            "error": repr(error),
                        }
                    )
                    tracker.state.failures = len(failures)
                    raise
                completed += 1
                simulation_index += 1
                tracker.update(
                    completed,
                    message=(
                        f"effect={effect_size:g}, replicate "
                        f"{replicate + 1}/{config.replicates}"
                    ),
                )

        frame = pd.DataFrame(rows)
        frame.to_csv(output_root / "simulation_replicates.csv", index=False)
        summaries: list[dict[str, Any]] = []
        for (effect_size, method), group in frame.groupby(
            ["effect_size", "method"], sort=False
        ):
            rejections = int(group["rejected"].sum())
            trials = int(len(group))
            summaries.append(
                {
                    "effect_size": float(effect_size),
                    "method": str(method),
                    "rejections": rejections,
                    "replicates": trials,
                    "rejection_fraction": rejections / trials,
                    "monte_carlo_se": math.sqrt(
                        (rejections / trials) * (1.0 - rejections / trials) / trials
                    ),
                    "clopper_pearson_95_lower": clopper_pearson(
                        rejections, trials
                    )[0],
                    "clopper_pearson_95_upper": clopper_pearson(
                        rejections, trials
                    )[1],
                    "mean_mmd2": float(group["statistic"].mean()),
                    "sd_mmd2": float(group["statistic"].std(ddof=1)),
                    "exact_permutations": int(group["permutations"].iloc[0]),
                }
            )
        summary_frame = pd.DataFrame(summaries)
        summary_frame.to_csv(output_root / "simulation_summary.csv", index=False)
        figures = _plot_power(summary_frame, Path(figure_directory))

        audit = {
            "status": "completed",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "config": asdict(config),
            "exact_group": (
                "product action (Z^2 semidirect C4)^2 on two-site "
                "finite-support arrays"
            ),
            "null_definition": (
                "Each block contains two fixed units and a fair within-block assignment. "
                "At effect size zero every unit satisfies Y(1)=Y(0) byte-for-byte; "
                "treatment- and morphology-dependent sitewise acquisition is then applied."
            ),
            "test": {
                "statistic": "unbiased RBF-kernel MMD squared",
                "randomization": f"all 2^{config.experiment_pairs} paired label swaps",
                "alpha": config.alpha,
            },
            "invariance_audit": audit,
            "ci_coverage": {
                "evaluated": False,
                "reason": (
                    "The unbiased MMD-squared estimator is degenerate at the null; "
                    "a naive percentile bootstrap interval does not have generally "
                    "valid null coverage. Exact randomization size is evaluated instead."
                ),
            },
            "software": {
                "python": sys.version,
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
            "outputs": {
                "replicates": str(
                    (output_root / "simulation_replicates.csv").resolve()
                ),
                "summary": str((output_root / "simulation_summary.csv").resolve()),
                "figures": figures,
            },
            "failures": failures,
        }
        write_json(output_root / "simulation_audit.json", audit)
        tracker.complete("simulation completed")
        return audit
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
        raise
