#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.experiment import ExperimentConfig, run_rxrx1_experiment
from cqoi.progress import ProgressTracker


FROZEN_SELECTION_SHA256 = (
    "b6f350ca96fb9e7a6271845dd6e432ed9dca556144a1a332d8f5af168642b968"
)
FROZEN_ANALYSIS_SOURCE_SHA256 = {
    "experiment.py": (
        "da741a882bc8ee176d5655c1c1ebf50467a465d7fb7a9e448dd83131d53c557e"
    ),
    "invariants.py": (
        "fdf2fb64cc577cbec4e3fce412dc7ff54f84f198ac48ebd492fdd2b35832c3ea"
    ),
    "statistics.py": (
        "3b597db2171c002915a54b501f9337383e5591388cf5715d76cd407fc1a2b965"
    ),
}
FROZEN_CONFIG = {
    "image_size": 64,
    "padding": 16,
    "max_integer_shift": 8,
    "bootstrap_replicates": 10_000,
    "ect_levels": 25,
}


def _sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_sidecar(path: Path, *, label: str) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(f"Missing {label} SHA-256 sidecar: {sidecar}")
    fields = sidecar.read_text().strip().split()
    if not fields:
        raise ValueError(f"Empty {label} SHA-256 sidecar: {sidecar}")
    expected = fields[0].lower()
    observed = _sha256(path)
    if observed != expected:
        raise RuntimeError(
            f"{label} SHA-256 mismatch: expected {expected}, observed {observed}"
        )
    return observed


def _verify_frozen_metadata(selection: dict, metadata_path: Path) -> str:
    expected = str(
        selection.get("source_files", {})
        .get("metadata", {})
        .get("sha256", "")
    ).lower()
    if len(expected) != 64:
        raise RuntimeError(
            "Selection manifest does not contain a valid frozen metadata SHA-256."
        )
    observed = _sha256(metadata_path)
    if observed != expected:
        raise RuntimeError(
            "Current metadata differ from the source frozen by the selection "
            f"manifest: expected {expected}, observed {observed}."
        )
    return observed


def _verify_image_subset(
    *,
    integrity_manifest_path: Path,
    selection_digest: str,
    metadata_path: Path,
    data_root: Path,
    progress_path: Path,
) -> dict:
    _verify_sidecar(integrity_manifest_path, label="image-integrity manifest")
    integrity = json.loads(integrity_manifest_path.read_text())
    if integrity.get("status") != "complete_crc_and_sha256_verified":
        raise RuntimeError("The image-integrity manifest is not complete.")
    if integrity.get("selection_manifest_sha256") != selection_digest:
        raise RuntimeError(
            "Image-integrity and selection manifests have different SHA-256 values."
        )
    if integrity.get("metadata_sha256") != _sha256(metadata_path):
        raise RuntimeError(
            "Current metadata do not match the image-integrity manifest."
        )

    records = integrity.get("files", [])
    if int(integrity.get("file_count", -1)) != 1_920 or len(records) != 1_920:
        raise RuntimeError("The frozen confirmation subset must contain 1,920 files.")
    expected_paths = {str(record["path"]) for record in records}
    if len(expected_paths) != 1_920:
        raise RuntimeError("The image-integrity manifest contains duplicate paths.")
    actual_paths = {
        str(path.relative_to(data_root)) for path in data_root.rglob("*.png")
    }
    if actual_paths != expected_paths:
        raise RuntimeError(
            "Current confirmation subset differs from the integrity manifest: "
            f"missing={len(expected_paths - actual_paths)}, "
            f"extra={len(actual_paths - expected_paths)}."
        )

    tracker = ProgressTracker(
        "verify-rxrx1-analysis-inputs", len(records), progress_path
    )
    for index, record in enumerate(records, start=1):
        relative = str(record["path"])
        path = data_root / relative
        size = path.stat().st_size
        digest = _sha256(path)
        if size != int(record["bytes"]) or digest != str(record["sha256"]):
            tracker.fail(f"Integrity mismatch: {relative}")
            raise RuntimeError(f"Integrity mismatch before analysis: {relative}")
        tracker.update(index, message=relative)
    tracker.complete("all 1,920 confirmation PNGs match the integrity manifest")
    return integrity


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen RxRx1 two-site product-quotient experiment, "
            "paired randomization tests, negative control, and robustness audits."
        )
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "data/manifests/selection_manifest.json",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT.parent / "data/raw/rxrx1/rxrx1/metadata.csv",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=ROOT / "data/rxrx1_validation_subset",
    )
    parser.add_argument(
        "--integrity-manifest",
        type=Path,
        default=ROOT / "data/manifests/rxrx1_subset_integrity.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/rxrx1",
    )
    parser.add_argument(
        "--figures",
        type=Path,
        default=ROOT / "paper/figures",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=ROOT / "logs/progress_rxrx1_experiment.json",
    )
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--padding", type=int, default=16)
    parser.add_argument("--max-integer-shift", type=int, default=8)
    parser.add_argument("--bootstrap-replicates", type=int, default=10_000)
    parser.add_argument("--ect-levels", type=int, default=25)
    args = parser.parse_args()

    requested_config = {
        "image_size": args.image_size,
        "padding": args.padding,
        "max_integer_shift": args.max_integer_shift,
        "bootstrap_replicates": args.bootstrap_replicates,
        "ect_levels": args.ect_levels,
    }
    if requested_config != FROZEN_CONFIG:
        raise ValueError(
            "The confirmatory runner accepts only the frozen configuration: "
            f"{FROZEN_CONFIG}; received {requested_config}."
        )
    selection_digest = _verify_sidecar(args.selection, label="selection manifest")
    if selection_digest != FROZEN_SELECTION_SHA256:
        raise RuntimeError(
            "The selected manifest is not the frozen confirmatory manifest: "
            f"{selection_digest}."
        )
    selection = json.loads(args.selection.read_text())
    _verify_frozen_metadata(selection, args.metadata)
    for source_name, expected_digest in FROZEN_ANALYSIS_SOURCE_SHA256.items():
        observed_digest = _sha256(ROOT / "src/cqoi" / source_name)
        if observed_digest != expected_digest:
            raise RuntimeError(
                f"The analysis source {source_name} differs from the frozen "
                f"version: expected {expected_digest}, observed {observed_digest}."
            )
    _verify_image_subset(
        integrity_manifest_path=args.integrity_manifest,
        selection_digest=selection_digest,
        metadata_path=args.metadata,
        data_root=args.data_root,
        progress_path=args.progress.with_name("progress_rxrx1_preflight.json"),
    )

    # These twenty seeds are part of the frozen statistical plan. The experiment
    # module independently checks them against the manifest before reading images.
    nuisance_seeds = tuple(range(20_260_731, 20_260_751))
    config = ExperimentConfig(
        image_size=args.image_size,
        padding=args.padding,
        max_integer_shift=args.max_integer_shift,
        nuisance_seeds=nuisance_seeds,
        bootstrap_replicates=args.bootstrap_replicates,
        ect_levels=args.ect_levels,
    )
    summary = run_rxrx1_experiment(
        selection_manifest_path=args.selection,
        metadata_path=args.metadata,
        data_root=args.data_root,
        output_directory=args.output,
        figure_directory=args.figures,
        progress_path=args.progress,
        config=config,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
