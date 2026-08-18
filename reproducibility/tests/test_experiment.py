from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from cqoi.experiment import (
    ExperimentConfig,
    _clean_nuclear_mask,
    apply_exact_action,
    compute_method_features,
    derive_hidden_nuisance,
    exact_invariant_features,
    parse_pair_specs,
    planar_cubical_euler_characteristic,
    topology_euler_features,
)


def _two_site_well() -> np.ndarray:
    well = np.zeros((2, 6, 24, 24), dtype=np.uint8)
    well[0, 0, 4:11, 5:13] = 180
    well[0, 0, 6:8, 10:16] = 240
    well[0, 1, 5:12, 4:9] = 110
    well[1, 0, 9:18, 3:8] = 210
    well[1, 0, 14:20, 7:14] = 150
    well[1, 2, 8:16, 4:12] = 90
    return well


def test_product_action_codes_are_exactly_invariant() -> None:
    well = _two_site_well()
    transformed = np.stack(
        [
            apply_exact_action(well[0], quarter_turns=1, dy=2, dx=-1),
            apply_exact_action(well[1], quarter_turns=3, dy=-1, dx=1),
        ],
        axis=0,
    )
    reference_pixel = exact_invariant_features([well], canvas_size=24)
    candidate_pixel = exact_invariant_features([transformed], canvas_size=24)
    assert np.array_equal(reference_pixel, candidate_pixel)

    reference_euler = topology_euler_features(
        [well],
        levels=25,
        nuclear_channel=0,
        min_component_size=1,
    )
    candidate_euler = topology_euler_features(
        [transformed],
        levels=25,
        nuclear_channel=0,
        min_component_size=1,
    )
    assert np.array_equal(reference_euler, candidate_euler)


def test_planar_cubical_euler_known_masks() -> None:
    one_component = np.zeros((9, 9), dtype=bool)
    one_component[2:7, 2:7] = True
    assert planar_cubical_euler_characteristic(one_component) == 1

    ring = np.zeros((9, 9), dtype=bool)
    ring[2:7, 2:7] = True
    ring[3:6, 3:6] = False
    assert planar_cubical_euler_characteristic(ring) == 0

    two_components = np.zeros((9, 9), dtype=bool)
    two_components[1:3, 1:3] = True
    two_components[6:8, 6:8] = True
    assert planar_cubical_euler_characteristic(two_components) == 2


def test_euler_mask_removes_components_smaller_than_four_pixels() -> None:
    image = np.zeros((9, 9), dtype=np.uint8)
    image[1, 1] = 255
    image[5:7, 5:7] = 255
    cleaned = _clean_nuclear_mask(image, min_component_size=4)
    assert not cleaned[1, 1]
    assert int(cleaned.sum()) == 4


def test_frozen_manifest_has_primary_and_nine_secondary_contrasts() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (root / "data/manifests/selection_manifest.json").read_text()
    )
    pairs = parse_pair_specs(manifest)
    assert len(pairs) == 10
    assert sum(pair.role == "primary" for pair in pairs) == 1
    assert sum(pair.role != "primary" for pair in pairs) == 9
    assert len({member for pair in pairs for member in (pair.left_id, pair.right_id)}) == 20


def test_feature_map_preserves_well_as_one_row() -> None:
    wells = [_two_site_well(), np.flip(_two_site_well(), axis=-1).copy()]
    config = ExperimentConfig(
        image_size=8,
        padding=8,
        max_integer_shift=1,
        nuisance_seeds=(20_260_731,),
        bootstrap_replicates=1,
        ect_levels=9,
    )
    features = compute_method_features(wells, config)
    assert all(values.shape[0] == 2 for values in features.values())


def test_hidden_acquisition_law_is_treatment_and_outcome_informative() -> None:
    control = [
        derive_hidden_nuisance(
            well_id=f"well-{index}|site=1",
            label=0,
            morphology=0.4,
            pooled_median=0.5,
            seed=20_260_731,
            max_shift=5,
        )
        for index in range(50)
    ]
    treated = [
        derive_hidden_nuisance(
            well_id=f"well-{index}|site=1",
            label=1,
            morphology=0.4,
            pooled_median=0.5,
            seed=20_260_731,
            max_shift=5,
        )
        for index in range(50)
    ]
    assert {turn for turn, _, _ in control}.issubset({0, 1})
    assert {turn for turn, _, _ in treated}.issubset({2, 3})
    assert all(dy < 0 and dx < 0 for _, dy, dx in control)
    assert all(dy > 0 and dx > 0 for _, dy, dx in treated)

    below = derive_hidden_nuisance(
        well_id="fixed|site=1",
        label=0,
        morphology=0.4,
        pooled_median=0.5,
        seed=20_260_731,
        max_shift=5,
    )
    above = derive_hidden_nuisance(
        well_id="fixed|site=1",
        label=0,
        morphology=0.6,
        pooled_median=0.5,
        seed=20_260_731,
        max_shift=5,
    )
    assert below != above
