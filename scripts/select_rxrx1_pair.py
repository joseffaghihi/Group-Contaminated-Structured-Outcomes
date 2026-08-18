#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.selection import (
    DISCOVERY_EXPERIMENTS,
    VALIDATION_EXPERIMENTS,
    load_huvec_well_embeddings,
    select_discovery_pairs,
    sha256_file,
    write_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Select and seal ten disjoint RxRx1 non-control pairs using only "
            "HUVEC-01..12 embeddings and discovery metadata."
        )
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT / "data/raw/rxrx1/rxrx1/metadata.csv",
    )
    parser.add_argument(
        "--embeddings",
        type=Path,
        default=ROOT / "data/raw/rxrx1/rxrx1/embeddings.csv",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "data/manifests/selection_manifest.json",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=ROOT / "logs/progress_selection.json",
    )
    parser.add_argument("--pair-count", type=int, default=10)
    args = parser.parse_args()

    wells = load_huvec_well_embeddings(
        args.metadata,
        args.embeddings,
        args.progress,
        discovery_experiments=DISCOVERY_EXPERIMENTS,
    )
    # The selector filters this table to HUVEC-01..12 before evaluating either
    # eligibility or plate grouping; HUVEC-17..24 rows do not enter selection.
    metadata = pd.read_csv(args.metadata)
    manifest = select_discovery_pairs(
        wells,
        metadata,
        discovery_experiments=DISCOVERY_EXPERIMENTS,
        validation_experiments=VALIDATION_EXPERIMENTS,
        pair_count=args.pair_count,
    )
    manifest["sealed_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["source_files"] = {
        "metadata": {
            "path": str(args.metadata.resolve()),
            "sha256": sha256_file(args.metadata),
        },
        "embeddings": {
            "path": str(args.embeddings.resolve()),
            "sha256": sha256_file(args.embeddings),
            "usage": "HUVEC-01..12 rows only",
        },
    }
    manifest["selection_code_sha256"] = {
        "src/cqoi/selection.py": sha256_file(ROOT / "src/cqoi/selection.py"),
        "scripts/select_rxrx1_pair.py": sha256_file(Path(__file__)),
    }
    digest = write_manifest(manifest, args.manifest)

    summary = {
        "manifest": str(args.manifest),
        "manifest_sha256": digest,
        "primary_pair": manifest["primary_pair"],
        "replication_pairs": manifest["replication_pairs"],
        "expected_validation_png_files": manifest["expected_validation_png_files"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"FROZEN selection manifest SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
