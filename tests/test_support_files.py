from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path


def _load_fetcher():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/fetch_rxrx1_support_files.py"
    specification = importlib.util.spec_from_file_location(
        "fetch_rxrx1_support_files",
        path,
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _fixture(root: Path):
    fetcher = _load_fetcher()
    payloads = {
        "metadata": b"site_id,well_id\nsite-1,well-1\n",
        "embeddings": b"site_id,feature_1\nsite-1,0.25\n",
    }
    selection = {
        "source_files": {
            name: {"sha256": _digest(payload)}
            for name, payload in payloads.items()
        }
    }
    selection_path = root / "selection.json"
    selection_path.write_text(json.dumps(selection))
    for spec in fetcher.SUPPORT_FILES:
        target = root / "raw" / spec.target_relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payloads[spec.name])
    return fetcher, payloads, selection, selection_path


def test_support_verify_only_never_opens_network() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        fetcher, _, _, selection_path = _fixture(root)
        original_urlopen = fetcher.urllib.request.urlopen

        def forbidden_network(*args, **kwargs):
            raise AssertionError("verify-only mode attempted a network request")

        fetcher.urllib.request.urlopen = forbidden_network
        try:
            audit = fetcher.fetch_support_files(
                selection_manifest_path=selection_path,
                data_root=root / "raw",
                progress_path=root / "progress.json",
                integrity_manifest_path=root / "integrity.json",
                verify_only=True,
            )
        finally:
            fetcher.urllib.request.urlopen = original_urlopen
        assert audit["status"] == "completed"
        assert audit["mode"] == "verify-only"
        assert len(audit["files"]) == 2
        assert json.loads((root / "integrity.json").read_text())["status"] == "completed"


def test_support_verify_only_rejects_corruption() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        fetcher, _, selection, _ = _fixture(root)
        embeddings = root / "raw/rxrx1/embeddings.csv"
        embeddings.write_bytes(embeddings.read_bytes() + b"corruption")
        try:
            fetcher.verify_support_files(
                selection_manifest=selection,
                data_root=root / "raw",
            )
        except RuntimeError as error:
            assert "SHA-256 mismatch" in str(error)
        else:
            raise AssertionError("Corrupted support file passed sealed-hash verification.")


def test_support_zip_member_is_atomically_extracted_and_verified() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        fetcher = _load_fetcher()
        spec = fetcher.SUPPORT_FILES[0]
        payload = b"site_id,well_id\nsite-1,well-1\n"
        archive = root / spec.archive_name
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            handle.writestr(spec.archive_member, payload)
        record = fetcher.extract_verified_member(
            spec,
            archive_path=archive,
            data_root=root / "raw",
            expected_sha256=_digest(payload),
        )
        target = root / "raw" / spec.target_relative_path
        assert target.read_bytes() == payload
        assert record["sha256"] == _digest(payload)
        assert not target.with_suffix(target.suffix + ".tmp").exists()
