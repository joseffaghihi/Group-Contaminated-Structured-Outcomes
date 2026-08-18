#!/usr/bin/env python3
from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.progress import ProgressTracker
from cqoi.remote_zip import RemoteZipEntry, extract_members, remote_zip_entries


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def crc32(path: Path, chunk_size: int = 1 << 20) -> int:
    checksum = 0
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            checksum = binascii.crc32(chunk, checksum)
    return checksum & 0xFFFFFFFF


def verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.is_file():
        raise FileNotFoundError(f"Missing frozen-manifest sidecar: {sidecar}")
    fields = sidecar.read_text().strip().split()
    if not fields:
        raise ValueError(f"Empty SHA-256 sidecar: {sidecar}")
    expected = fields[0].lower()
    observed = sha256(path)
    if observed != expected:
        raise RuntimeError(
            f"Selection manifest SHA-256 mismatch: expected {expected}, observed {observed}"
        )
    return observed


def archive_identity(url: str) -> dict[str, str | int | None]:
    request = urllib.request.Request(url, method="HEAD")
    with urllib.request.urlopen(request, timeout=120.0) as response:
        return {
            "content_length": int(response.headers["Content-Length"]),
            "etag": response.headers.get("ETag", "").strip('"') or None,
            "last_modified": response.headers.get("Last-Modified"),
        }


def selected_validation_sites(
    metadata: pd.DataFrame,
    selection: dict,
) -> pd.DataFrame:
    selected_ids = [int(value) for value in selection["selected_sirna_ids"]]
    experiments = [int(value) for value in selection["validation_experiments"]]
    frame = metadata.copy()
    frame["experiment_number"] = (
        frame["experiment"].astype(str).str.split("-").str[-1].astype(int)
    )
    frame = frame[
        (frame["cell_type"] == selection["cell_type"])
        & (frame["well_type"] == selection["well_type"])
        & frame["sirna_id"].isin(selected_ids)
        & frame["experiment_number"].isin(experiments)
    ].copy()

    if frame["site_id"].duplicated().any():
        raise ValueError("Validation metadata contains duplicate site identifiers.")
    expected_sites = int(selection["expected_validation_sites"])
    if len(frame) != expected_sites:
        raise RuntimeError(
            f"Expected {expected_sites} validation sites, found {len(frame)}."
        )
    per_condition_experiment = frame.groupby(
        ["sirna_id", "experiment"], sort=True
    ).agg(
        sites=("site", "nunique"),
        wells=("well_id", "nunique"),
        plates=("plate", "nunique"),
    )
    invalid = per_condition_experiment[
        (per_condition_experiment["sites"] != 2)
        | (per_condition_experiment["wells"] != 1)
        | (per_condition_experiment["plates"] != 1)
    ]
    if not invalid.empty:
        raise RuntimeError(
            "Selected validation conditions are not complete two-site single-well "
            f"assignments; first invalid row={invalid.iloc[0].to_dict()}"
        )

    # Check the frozen pairs' same-plate occurrence using confirmation metadata.
    for pair in selection["selected_pairs"]:
        left, right = [int(value) for value in pair["sirna_ids"]]
        pair_frame = (
            frame[frame["sirna_id"].isin([left, right])]
            .drop_duplicates(["sirna_id", "experiment"])
            .pivot(index="experiment", columns="sirna_id", values="plate")
        )
        if list(pair_frame.columns) != sorted([left, right]):
            pair_frame = pair_frame.reindex(columns=sorted([left, right]))
        if pair_frame.isna().any().any() or not (
            pair_frame[left].astype(int) == pair_frame[right].astype(int)
        ).all():
            raise RuntimeError(
                f"Sealed pair {left}/{right} does not share a plate in every "
                "validation experiment."
            )
    return frame.sort_values(
        ["experiment_number", "sirna_id", "site"], kind="mergesort"
    )


def member_names(frame: pd.DataFrame) -> list[str]:
    members = []
    for row in frame.itertuples(index=False):
        for channel in range(1, 7):
            members.append(
                f"rxrx1/images/{row.experiment}/Plate{row.plate}/"
                f"{row.well}_s{row.site}_w{channel}.png"
            )
    if len(members) != len(set(members)):
        raise ValueError("The requested archive-member list contains duplicates.")
    return sorted(members)


def _local_matches(path: Path, entry: RemoteZipEntry) -> bool:
    if not path.is_file() or path.stat().st_size != entry.file_size:
        return False
    return crc32(path) == entry.crc


def quarantine_invalid(path: Path) -> Path:
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = path.with_suffix(path.suffix + f".invalid-{suffix}")
    os.replace(path, target)
    return target


def verify_files(
    destination: Path,
    members: list[str],
    entries: dict[str, RemoteZipEntry],
    progress_path: Path,
) -> tuple[list[dict], str]:
    tracker = ProgressTracker("verify-rxrx1-subset-crc-sha256", len(members), progress_path)
    records: list[dict] = []
    aggregate = hashlib.sha256()
    failures: list[str] = []
    for index, member in enumerate(members, start=1):
        path = destination / member
        entry = entries[member]
        try:
            if not path.is_file():
                raise FileNotFoundError(path)
            size = path.stat().st_size
            observed_crc = crc32(path)
            observed_sha = sha256(path)
            with path.open("rb") as handle:
                signature = handle.read(len(PNG_SIGNATURE))
            if size != entry.file_size:
                raise RuntimeError(f"size {size} != expected {entry.file_size}")
            if observed_crc != entry.crc:
                raise RuntimeError(
                    f"CRC32 {observed_crc:08x} != expected {entry.crc:08x}"
                )
            if signature != PNG_SIGNATURE:
                raise RuntimeError("invalid PNG signature")
            aggregate.update(member.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(observed_sha.encode("ascii"))
            aggregate.update(b"\n")
            records.append(
                {
                    "path": member,
                    "bytes": size,
                    "crc32": f"{observed_crc:08x}",
                    "sha256": observed_sha,
                }
            )
            message = f"{member} CRC={observed_crc:08x}"
        except Exception as exc:
            failures.append(f"{member}: {exc}")
            tracker.state.failures = len(failures)
            message = f"FAILED {member}: {exc}"
        tracker.update(index, message=message)
    if failures:
        tracker.fail(f"{len(failures)} integrity failure(s); first={failures[0]}")
        raise RuntimeError("\n".join(failures))
    tracker.complete(message=f"verified {len(records)} PNG files")
    return records, aggregate.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch only the frozen RxRx1 validation images by ZIP byte ranges, "
            "checking remote CRC32 and local SHA-256."
        )
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=ROOT / "data/raw/rxrx1/rxrx1/metadata.csv",
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "data/manifests/selection_manifest.json",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=ROOT / "data/rxrx1_validation_subset",
    )
    parser.add_argument(
        "--url",
        default=(
            "https://www.googleapis.com/download/storage/v1/b/rxrx/o/"
            "rxrx1%2Frxrx1-images.zip?alt=media"
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Concurrent HTTP range workers. The conservative default of 1 avoids "
            "exhausting file descriptors in restricted/shared execution environments."
        ),
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=ROOT / "logs/progress_download.json",
    )
    args = parser.parse_args()

    selection_digest = verify_sidecar(args.selection)
    selection = json.loads(args.selection.read_text())
    if (
        selection.get("status")
        != "frozen_discovery_only_before_validation_image_analysis"
    ):
        raise RuntimeError("Selection manifest is not the frozen discovery-only version.")
    if selection.get("validation_image_outcomes_used_for_selection") is not False:
        raise RuntimeError("Selection manifest does not certify outcome-blind validation.")

    expected_metadata_digest = str(
        selection.get("source_files", {})
        .get("metadata", {})
        .get("sha256", "")
    ).lower()
    if len(expected_metadata_digest) != 64:
        raise RuntimeError(
            "Selection manifest does not contain a valid frozen metadata SHA-256."
        )
    metadata_digest = sha256(args.metadata)
    if metadata_digest != expected_metadata_digest:
        raise RuntimeError(
            "Current metadata differ from the source frozen by the selection "
            f"manifest: expected {expected_metadata_digest}, "
            f"observed {metadata_digest}."
        )

    metadata = pd.read_csv(args.metadata)
    selected = selected_validation_sites(metadata, selection)
    members = member_names(selected)
    expected_files = int(selection["expected_validation_png_files"])
    if len(members) != expected_files:
        raise RuntimeError(f"Expected {expected_files} PNG members, found {len(members)}.")

    print(
        f"FROZEN preflight: {len(selection['selected_pairs'])} disjoint pairs, "
        f"{len(selected)} sites, {len(members)} PNGs; indexing remote archive...",
        flush=True,
    )
    entries = remote_zip_entries(args.url, members)
    args.destination.mkdir(parents=True, exist_ok=True)

    valid_existing: list[str] = []
    pending: list[str] = []
    quarantined: list[str] = []
    for member in members:
        path = args.destination / member
        if _local_matches(path, entries[member]):
            valid_existing.append(member)
        else:
            if path.exists():
                quarantined.append(str(quarantine_invalid(path)))
            pending.append(member)

    print(
        f"Download preflight: valid_existing={len(valid_existing)}, "
        f"pending={len(pending)}, quarantined={len(quarantined)}, failures=0",
        flush=True,
    )
    # Passing only absent members avoids treating a merely nonempty partial file as
    # reusable inside the generic range downloader.
    if pending:
        extract_members(
            args.url,
            pending,
            args.destination,
            args.progress,
            workers=args.workers,
        )
    else:
        tracker = ProgressTracker("download-rxrx1-selected-images", 1, args.progress)
        tracker.complete(message=f"reused {len(valid_existing)} CRC-verified files")

    records, aggregate_digest = verify_files(
        args.destination, members, entries, args.progress
    )
    actual_pngs = {
        str(path.relative_to(args.destination))
        for path in args.destination.rglob("*.png")
    }
    extras = sorted(actual_pngs - set(members))
    missing = sorted(set(members) - actual_pngs)
    if extras or missing:
        raise RuntimeError(
            f"Destination is not exact: extra PNGs={len(extras)}, missing PNGs={len(missing)}"
        )

    identity = archive_identity(args.url)
    integrity_manifest = {
        "schema_version": "2.0",
        "status": "complete_crc_and_sha256_verified",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": args.url,
        "source_archive": identity,
        "selection_manifest": str(args.selection.resolve()),
        "selection_manifest_sha256": selection_digest,
        "metadata_sha256": metadata_digest,
        "cell_type": selection["cell_type"],
        "validation_experiments": selection["validation_experiments"],
        "selected_pairs": [
            {
                "role": pair["role"],
                "sirna_ids": pair["sirna_ids"],
                "sirnas": pair["sirnas"],
            }
            for pair in selection["selected_pairs"]
        ],
        "well_count": int(selection["expected_validation_wells"]),
        "site_count": int(len(selected)),
        "file_count": int(len(records)),
        "total_bytes": int(sum(record["bytes"] for record in records)),
        "reused_crc_verified_files": len(valid_existing),
        "downloaded_files": len(pending),
        "quarantined_invalid_files": quarantined,
        "aggregate_path_sha256_digest": aggregate_digest,
        "validation_outcomes_inspected": False,
        "integrity_operations_only": ["size", "CRC32", "SHA-256", "PNG signature"],
        "files": records,
    }
    manifest_path = ROOT / "data/manifests/rxrx1_subset_integrity.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(integrity_manifest, indent=2, sort_keys=True) + "\n"
    )
    manifest_digest = sha256(manifest_path)
    manifest_path.with_suffix(".json.sha256").write_text(
        f"{manifest_digest}  {manifest_path.name}\n"
    )
    print(
        f"Downloaded/reused and verified {len(records)} PNG files for "
        f"{len(selected)} validation sites; failures=0.\n"
        f"Integrity manifest SHA-256: {manifest_digest}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
