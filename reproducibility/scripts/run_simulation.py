#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.simulation import SimulationConfig, run_simulation_study


def _effect_sizes(value: str) -> tuple[float, ...]:
    parsed = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    if not parsed:
        raise argparse.ArgumentTypeError("At least one effect size is required.")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the paired sharp-null simulation with exact 2^8 randomization "
            "tests, Clopper-Pearson intervals, power curves, and progress ETA."
        )
    )
    parser.add_argument("--replicates", type=int, default=250)
    parser.add_argument(
        "--effect-sizes",
        type=_effect_sizes,
        default=(0.0, 0.35, 0.70, 1.0),
        help="Comma-separated effect strengths; the first must be 0.",
    )
    parser.add_argument("--seed", type=int, default=51_907)
    parser.add_argument("--invariance-audit-trials", type=int, default=1000)
    parser.add_argument("--image-size", type=int, default=28)
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--max-integer-shift", type=int, default=5)
    parser.add_argument("--ect-levels", type=int, default=25)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/simulation",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=ROOT / "paper/figures",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=ROOT / "logs/progress_simulation.json",
    )
    args = parser.parse_args()

    config = SimulationConfig(
        replicates=args.replicates,
        image_size=args.image_size,
        padding=args.padding,
        max_integer_shift=args.max_integer_shift,
        effect_sizes=args.effect_sizes,
        seed=args.seed,
        invariance_audit_trials=args.invariance_audit_trials,
        ect_levels=args.ect_levels,
    )
    summary = run_simulation_study(
        output_directory=args.output,
        figure_directory=args.figures,
        progress_path=args.progress,
        config=config,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
