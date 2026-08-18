from __future__ import annotations

import numpy as np

from cqoi.simulation import (
    SimulationConfig,
    calibration_small_seed_set,
    generate_simulation_replicate,
    synthetic_potential_well,
)


def _shared_parameters() -> dict[str, float]:
    return {
        "center_y": 9.5,
        "center_x": 10.0,
        "radius": 4.5,
        "satellite_dy": -3.0,
        "satellite_dx": 4.0,
    }


def test_sharp_null_potential_outcomes_are_byte_identical() -> None:
    control = synthetic_potential_well(
        unit_seed=7741,
        shared_parameters=_shared_parameters(),
        treatment=0,
        effect_size=0.0,
        image_size=20,
    )
    treated = synthetic_potential_well(
        unit_seed=7741,
        shared_parameters=_shared_parameters(),
        treatment=1,
        effect_size=0.0,
        image_size=20,
    )
    assert np.array_equal(control, treated)

    alternative = synthetic_potential_well(
        unit_seed=7741,
        shared_parameters=_shared_parameters(),
        treatment=1,
        effect_size=0.7,
        image_size=20,
    )
    assert not np.array_equal(control, alternative)


def test_simulation_assigns_one_treatment_per_block() -> None:
    config = SimulationConfig(
        replicates=1,
        image_size=16,
        padding=6,
        max_integer_shift=4,
        effect_sizes=(0.0,),
        ect_levels=7,
    )
    _, labels, blocks = generate_simulation_replicate(
        replicate_seed=9401,
        effect_size=0.0,
        config=config,
    )
    for block in np.unique(blocks):
        assert sorted(labels[blocks == block].tolist()) == [0, 1]


def test_small_null_calibration_is_deterministic_and_exact() -> None:
    first = calibration_small_seed_set(seeds=(0, 1), image_size=16)
    second = calibration_small_seed_set(seeds=(0, 1), image_size=16)
    assert first == second
    assert first["tests"] == 2
    assert all(
        abs(p_value * 256 - round(p_value * 256)) < 1e-12
        for p_value in first["p_values"]
    )
