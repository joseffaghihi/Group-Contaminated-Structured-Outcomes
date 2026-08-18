from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_runner():
    path = ROOT / "scripts/run_rxrx1_experiment.py"
    specification = importlib.util.spec_from_file_location(
        "run_rxrx1_experiment_freeze_test",
        path,
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def test_discovery_only_replay_preserves_the_ordered_pair_family() -> None:
    current = json.loads(
        (ROOT / "data/manifests/selection_manifest.json").read_text()
    )
    prior = json.loads(
        (
            ROOT
            / "data/manifests/invalidated/"
            "selection_manifest_validation_completeness_filter.json"
        ).read_text()
    )
    score_fields = (
        "sirna_ids",
        "sirnas",
        "discovery_split_half_stable_score",
        "discovery_minimum_half_snr",
        "discovery_mean_half_snr",
        "discovery_half_direction_cosine",
        "discovery_leave_one_experiment_out_direction_agreement",
    )
    assert len(current["selected_pairs"]) == len(prior["selected_pairs"]) == 10
    for current_pair, prior_pair in zip(
        current["selected_pairs"],
        prior["selected_pairs"],
        strict=True,
    ):
        for field in score_fields:
            assert current_pair[field] == prior_pair[field]
    assert current["validation_metadata_used_for_selection"] is False
    assert current["validation_metadata_fields_used_for_selection"] == []


def test_frozen_manifest_and_analysis_sources_match_runner_constants() -> None:
    runner = _load_runner()
    manifest = ROOT / "data/manifests/selection_manifest.json"
    assert _sha256(manifest) == runner.FROZEN_SELECTION_SHA256
    for source_name, expected_digest in (
        runner.FROZEN_ANALYSIS_SOURCE_SHA256.items()
    ):
        assert _sha256(ROOT / "src/cqoi" / source_name) == expected_digest
    sidecar_digest = manifest.with_suffix(".json.sha256").read_text().split()[0]
    assert sidecar_digest == runner.FROZEN_SELECTION_SHA256


def test_runner_configuration_equals_experiment_defaults() -> None:
    runner = _load_runner()
    config = runner.ExperimentConfig()
    observed = {
        "image_size": config.image_size,
        "padding": config.padding,
        "max_integer_shift": config.max_integer_shift,
        "bootstrap_replicates": config.bootstrap_replicates,
        "ect_levels": config.ect_levels,
    }
    assert observed == runner.FROZEN_CONFIG


def test_runner_enforces_metadata_hash_from_frozen_selection() -> None:
    runner = _load_runner()
    selection = json.loads(
        (ROOT / "data/manifests/selection_manifest.json").read_text()
    )
    with tempfile.TemporaryDirectory() as directory:
        metadata = Path(directory) / "metadata.csv"
        metadata.write_bytes(b"synthetic metadata for the hash-gate unit test\n")
        expected = _sha256(metadata)
        synthetic_selection = json.loads(json.dumps(selection))
        synthetic_selection["source_files"]["metadata"]["sha256"] = expected
        assert (
            runner._verify_frozen_metadata(synthetic_selection, metadata)
            == expected
        )

        changed = Path(directory) / "changed_metadata.csv"
        changed.write_bytes(metadata.read_bytes() + b"changed")
        try:
            runner._verify_frozen_metadata(synthetic_selection, changed)
        except RuntimeError as error:
            assert "differ from the source frozen" in str(error)
        else:
            raise AssertionError("Changed metadata passed the frozen-hash gate.")
