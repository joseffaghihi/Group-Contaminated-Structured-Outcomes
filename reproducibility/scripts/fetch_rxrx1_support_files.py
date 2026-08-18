#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, BinaryIO, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cqoi.progress import ProgressTracker


JSON_MEDIA_ROOT = "https://storage.googleapis.com/download/storage/v1/b/rxrx/o"
CHUNK_BYTES = 1 << 20


@dataclass(frozen=True)
class SupportFileSpec:
    name: str
    manifest_key: str
    archive_name: str
    archive_member: str
    target_relative_path: str
    media_url: str


SUPPORT_FILES = (
    SupportFileSpec(
        name="metadata",
        manifest_key="metadata",
        archive_name="rxrx1-metadata.zip",
        archive_member="rxrx1/metadata.csv",
        target_relative_path="rxrx1/metadata.csv",
        media_url=(
            f"{JSON_MEDIA_ROOT}/rxrx1%2Frxrx1-metadata.zip?alt=media"
        ),
    ),
    SupportFileSpec(
        name="embeddings",
        manifest_key="embeddings",
        archive_name="rxrx1-dl-embeddings.zip",
        archive_member="rxrx1/embeddings.csv",
        target_relative_path="rxrx1/embeddings.csv",
        media_url=(
            f"{JSON_MEDIA_ROOT}/rxrx1%2Frxrx1-dl-embeddings.zip?alt=media"
        ),
    ),
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    os.replace(temporary, destination)


def sealed_hashes(selection_manifest: Mapping[str, Any]) -> dict[str, str]:
    source_files = selection_manifest.get("source_files")
    if not isinstance(source_files, Mapping):
        raise ValueError("Selection manifest has no source_files mapping.")
    hashes: dict[str, str] = {}
    for spec in SUPPORT_FILES:
        source = source_files.get(spec.manifest_key)
        if not isinstance(source, Mapping):
            raise ValueError(
                f"Selection manifest has no source_files.{spec.manifest_key}."
            )
        digest = str(source.get("sha256", "")).lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(
                f"Invalid sealed SHA-256 for {spec.manifest_key}: {digest!r}"
            )
        hashes[spec.manifest_key] = digest
    return hashes


def verify_target(
    spec: SupportFileSpec,
    *,
    data_root: str | Path,
    expected_sha256: str,
) -> dict[str, Any]:
    target = Path(data_root) / spec.target_relative_path
    if not target.is_file():
        raise FileNotFoundError(f"Missing extracted support file: {target}")
    observed = sha256_file(target)
    if observed != expected_sha256:
        raise RuntimeError(
            f"{spec.name} SHA-256 mismatch: expected {expected_sha256}, "
            f"observed {observed}"
        )
    return {
        "name": spec.name,
        "path": str(target.resolve()),
        "bytes": target.stat().st_size,
        "sha256": observed,
        "media_url": spec.media_url,
        "verified_against": "sealed selection-manifest extracted-file SHA-256",
    }


def verify_support_files(
    *,
    selection_manifest: Mapping[str, Any],
    data_root: str | Path,
    specs: Sequence[SupportFileSpec] = SUPPORT_FILES,
    progress_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    expected = sealed_hashes(selection_manifest)
    tracker = (
        ProgressTracker("verify-rxrx1-support-files", len(specs), progress_path)
        if progress_path is not None
        else None
    )
    records: list[dict[str, Any]] = []
    try:
        for index, spec in enumerate(specs, start=1):
            record = verify_target(
                spec,
                data_root=data_root,
                expected_sha256=expected[spec.manifest_key],
            )
            records.append(record)
            if tracker is not None:
                tracker.update(
                    index,
                    message=(
                        f"{spec.name}: {record['bytes'] / (1 << 20):.1f} MiB, "
                        f"SHA-256 {record['sha256'][:12]}…"
                    ),
                )
        if tracker is not None:
            tracker.complete(f"verified {len(records)} sealed support files")
        return records
    except Exception as error:
        if tracker is not None:
            tracker.fail(f"{type(error).__name__}: {error}")
        raise


def _progress_child_path(base: Path, name: str) -> Path:
    return base.with_name(f"{base.stem}_{name}{base.suffix or '.json'}")


def _completed_partial_zip(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except (OSError, zipfile.BadZipFile):
        return False


def _response_total(response: BinaryIO, offset: int) -> int:
    content_range = response.headers.get("Content-Range")
    if content_range:
        match = re.fullmatch(r"bytes \d+-\d+/(\d+)", content_range.strip())
        if match:
            return int(match.group(1))
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        return offset + int(content_length)
    return max(offset + 1, 1)


def download_archive(
    spec: SupportFileSpec,
    *,
    data_root: str | Path,
    progress_path: str | Path,
    timeout_seconds: float = 120.0,
) -> Path:
    root = Path(data_root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / spec.archive_name
    partial = destination.with_suffix(destination.suffix + ".part")
    if destination.is_file():
        if _completed_partial_zip(destination):
            return destination
        quarantine = destination.with_suffix(
            destination.suffix
            + datetime.now(timezone.utc).strftime(".invalid-%Y%m%dT%H%M%SZ")
        )
        os.replace(destination, quarantine)
    if _completed_partial_zip(partial):
        os.replace(partial, destination)
        return destination

    offset = partial.stat().st_size if partial.is_file() else 0
    headers = {"User-Agent": "cqoi-rxrx1-reproducibility/1.0"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = urllib.request.Request(spec.media_url, headers=headers)
    try:
        response = urllib.request.urlopen(request, timeout=timeout_seconds)
    except urllib.error.HTTPError as error:
        if error.code == 416 and _completed_partial_zip(partial):
            os.replace(partial, destination)
            return destination
        raise

    with response:
        status = int(getattr(response, "status", response.getcode()))
        append = offset > 0 and status == 206
        if not append:
            offset = 0
        total = _response_total(response, offset)
        tracker = ProgressTracker(
            f"download-rxrx1-{spec.name}",
            total,
            progress_path,
        )
        if offset:
            tracker.update(
                offset,
                message=f"resuming at {offset / (1 << 20):.1f} MiB",
            )
        mode = "ab" if append else "wb"
        completed = offset
        try:
            with partial.open(mode) as handle:
                while chunk := response.read(CHUNK_BYTES):
                    handle.write(chunk)
                    completed += len(chunk)
                    tracker.update(
                        min(completed, total),
                        message=(
                            f"{completed / (1 << 20):.1f}/"
                            f"{total / (1 << 20):.1f} MiB"
                        ),
                    )
                handle.flush()
                os.fsync(handle.fileno())
            if completed != total:
                raise RuntimeError(
                    f"{spec.name} download ended at {completed} bytes; "
                    f"expected {total}."
                )
            if not _completed_partial_zip(partial):
                raise RuntimeError(
                    f"Downloaded {spec.archive_name} is not a valid ZIP archive."
                )
            os.replace(partial, destination)
            tracker.complete(
                f"downloaded {destination.name}; ZIP structure verified"
            )
            return destination
        except Exception as error:
            tracker.fail(f"{type(error).__name__}: {error}")
            raise


def extract_verified_member(
    spec: SupportFileSpec,
    *,
    archive_path: str | Path,
    data_root: str | Path,
    expected_sha256: str,
) -> dict[str, Any]:
    archive_path = Path(archive_path)
    target = Path(data_root) / spec.target_relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    digest = hashlib.sha256()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = set(archive.namelist())
            if spec.archive_member not in members:
                raise RuntimeError(
                    f"{archive_path.name} lacks {spec.archive_member!r}."
                )
            with archive.open(spec.archive_member) as source, temporary.open(
                "wb"
            ) as destination:
                while chunk := source.read(CHUNK_BYTES):
                    destination.write(chunk)
                    digest.update(chunk)
                destination.flush()
                os.fsync(destination.fileno())
        observed = digest.hexdigest()
        if observed != expected_sha256:
            raise RuntimeError(
                f"Extracted {spec.name} SHA-256 mismatch: expected "
                f"{expected_sha256}, observed {observed}"
            )
        os.replace(temporary, target)
        return {
            "name": spec.name,
            "path": str(target.resolve()),
            "bytes": target.stat().st_size,
            "sha256": observed,
            "archive": {
                "path": str(archive_path.resolve()),
                "bytes": archive_path.stat().st_size,
                "sha256": sha256_file(archive_path),
                "member": spec.archive_member,
                "media_url": spec.media_url,
            },
            "verified_against": (
                "sealed selection-manifest extracted-file SHA-256"
            ),
        }
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def fetch_support_files(
    *,
    selection_manifest_path: str | Path,
    data_root: str | Path,
    progress_path: str | Path,
    integrity_manifest_path: str | Path,
    verify_only: bool = False,
    specs: Sequence[SupportFileSpec] = SUPPORT_FILES,
) -> dict[str, Any]:
    selection_path = Path(selection_manifest_path)
    selection = json.loads(selection_path.read_text())
    expected = sealed_hashes(selection)
    progress = Path(progress_path)
    tracker = ProgressTracker(
        "rxrx1-support-files",
        len(specs),
        progress,
    )
    records: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    try:
        for index, spec in enumerate(specs, start=1):
            try:
                record = verify_target(
                    spec,
                    data_root=data_root,
                    expected_sha256=expected[spec.manifest_key],
                )
                record["source"] = "existing sealed-hash match"
            except (FileNotFoundError, RuntimeError):
                if verify_only:
                    raise
                archive = download_archive(
                    spec,
                    data_root=data_root,
                    progress_path=_progress_child_path(progress, spec.name),
                )
                record = extract_verified_member(
                    spec,
                    archive_path=archive,
                    data_root=data_root,
                    expected_sha256=expected[spec.manifest_key],
                )
                record["source"] = "official RxRx1 Google Cloud JSON media API"
            records.append(record)
            tracker.update(
                index,
                message=(
                    f"{spec.name}: verified SHA-256 "
                    f"{record['sha256'][:12]}…"
                ),
            )
        audit = {
            "schema_version": "1.0",
            "status": "completed",
            "mode": "verify-only" if verify_only else "fetch-or-verify",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "selection_manifest": {
                "path": str(selection_path.resolve()),
                "sha256": sha256_file(selection_path),
            },
            "data_root": str(Path(data_root).resolve()),
            "official_source_page": "https://www.rxrx.ai/rxrx1",
            "download_api": "Google Cloud Storage JSON API with alt=media",
            "files": records,
            "failures": failures,
        }
        atomic_json(integrity_manifest_path, audit)
        tracker.complete(f"verified {len(records)} RxRx1 support files")
        return audit
    except Exception as error:
        failures.append(
            {
                "type": type(error).__name__,
                "message": str(error),
            }
        )
        tracker.fail(f"{type(error).__name__}: {error}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch or verify the official RxRx1 metadata and deep-learning "
            "embeddings, accepting them only when their extracted SHA-256 "
            "digests match the sealed selection manifest."
        )
    )
    parser.add_argument(
        "--selection",
        type=Path,
        default=ROOT / "data/manifests/selection_manifest.json",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=ROOT.parent / "data/raw/rxrx1",
    )
    parser.add_argument(
        "--progress",
        type=Path,
        default=ROOT / "logs/progress_support_files.json",
    )
    parser.add_argument(
        "--integrity-manifest",
        type=Path,
        default=ROOT / "data/manifests/rxrx1_support_integrity.json",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Perform no network request; require both extracted files to exist.",
    )
    args = parser.parse_args()

    audit = fetch_support_files(
        selection_manifest_path=args.selection,
        data_root=args.data_root,
        progress_path=args.progress,
        integrity_manifest_path=args.integrity_manifest,
        verify_only=args.verify_only,
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
