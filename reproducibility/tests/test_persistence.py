from __future__ import annotations

import itertools

import numpy as np

from cqoi.persistence import (
    PersistenceDiagram0D,
    bottleneck_distance_0d,
    l2_from_rbf_rkhs_distance,
    rbf_rkhs_distance,
    zero_dimensional_persistence,
)


def _brute_force_bottleneck(
    first: PersistenceDiagram0D,
    second: PersistenceDiagram0D,
) -> float:
    """Independent exhaustive oracle for small diagonal-augmented diagrams."""
    left = np.asarray(first.finite, dtype=float)
    right = np.asarray(second.finite, dtype=float)
    n_left, n_right = len(left), len(right)
    total = n_left + n_right
    if len(first.essential_births) != len(second.essential_births):
        return float("inf")
    essential_cost = (
        0.0
        if len(first.essential_births) == 0
        else float(
            np.max(
                np.abs(
                    np.sort(first.essential_births)
                    - np.sort(second.essential_births)
                )
            )
        )
    )
    if total == 0:
        return essential_cost
    costs = np.full((total, total), np.inf)
    if n_left and n_right:
        costs[:n_left, :n_right] = np.max(
            np.abs(left[:, None, :] - right[None, :, :]),
            axis=2,
        )
    for index, (birth, death) in enumerate(left):
        costs[index, n_right + index] = (death - birth) / 2.0
    for index, (birth, death) in enumerate(right):
        costs[n_left + index, index] = (death - birth) / 2.0
    if n_left and n_right:
        costs[n_left:, n_right:] = 0.0
    optimum = min(
        max(costs[row, column] for row, column in enumerate(permutation))
        for permutation in itertools.permutations(range(total))
    )
    return max(float(optimum), essential_cost)


def test_known_three_vertex_lower_star_diagram() -> None:
    diagram = zero_dimensional_persistence(np.asarray([[0.0, 2.0, 0.0]]))
    assert np.array_equal(diagram.finite, np.asarray([[0.0, 2.0]]))
    assert np.array_equal(diagram.essential_births, np.asarray([0.0]))


def test_known_five_vertex_multibar_lower_star_diagram() -> None:
    diagram = zero_dimensional_persistence(
        np.asarray([[0.0, 3.0, 1.0, 4.0, 0.0]])
    )
    assert np.array_equal(
        diagram.finite,
        np.asarray([[0.0, 4.0], [1.0, 3.0]]),
    )
    assert np.array_equal(diagram.essential_births, np.asarray([0.0]))


def test_multibar_bottleneck_matches_exhaustive_oracle() -> None:
    rng = np.random.default_rng(8675309)
    for _ in range(40):
        left_count = int(rng.integers(0, 4))
        right_count = int(rng.integers(0, 4))
        left_births = rng.uniform(-1.0, 1.0, size=left_count)
        right_births = rng.uniform(-1.0, 1.0, size=right_count)
        left = PersistenceDiagram0D(
            finite=np.column_stack(
                [left_births, left_births + rng.uniform(0.05, 1.0, size=left_count)]
            ).reshape(-1, 2),
            essential_births=np.asarray([rng.uniform(-1.0, 1.0)]),
        )
        right = PersistenceDiagram0D(
            finite=np.column_stack(
                [
                    right_births,
                    right_births + rng.uniform(0.05, 1.0, size=right_count),
                ]
            ).reshape(-1, 2),
            essential_births=np.asarray([rng.uniform(-1.0, 1.0)]),
        )
        observed = bottleneck_distance_0d(left, right)
        expected = _brute_force_bottleneck(left, right)
        assert abs(observed - expected) < 1e-14


def test_bottleneck_distance_for_a_vertical_shift() -> None:
    first = zero_dimensional_persistence(np.asarray([[0.0, 2.0, 0.0]]))
    second = zero_dimensional_persistence(np.asarray([[0.3, 2.3, 0.3]]))
    assert abs(bottleneck_distance_0d(first, second) - 0.3) < 1e-14


def test_bottleneck_stability_on_a_fixed_grid() -> None:
    rng = np.random.default_rng(1729)
    first_image = rng.normal(size=(6, 7))
    perturbation = rng.uniform(-0.07, 0.07, size=first_image.shape)
    second_image = first_image + perturbation
    first = zero_dimensional_persistence(first_image)
    second = zero_dimensional_persistence(second_image)
    bottleneck = bottleneck_distance_0d(first, second)
    sup_norm = float(np.max(np.abs(perturbation)))
    assert bottleneck <= sup_norm + 1e-12


def test_grid_isometries_preserve_the_diagram() -> None:
    image = np.asarray(
        [[0.0, 3.0, 2.0], [1.0, 4.0, 0.5], [2.5, 1.5, 5.0]]
    )
    original = zero_dimensional_persistence(image)
    rotated = zero_dimensional_persistence(np.rot90(image))
    reflected = zero_dimensional_persistence(np.fliplr(image))
    assert bottleneck_distance_0d(original, rotated) == 0.0
    assert bottleneck_distance_0d(original, reflected) == 0.0


def test_gaussian_feature_distance_inversion_recovers_l2() -> None:
    first = np.asarray([0.0, 0.5, 1.0, 0.2])
    second = np.asarray([0.1, 0.4, 0.9, 0.0])
    bandwidth = 1.7
    feature_distance = rbf_rkhs_distance(first, second, bandwidth)
    recovered = l2_from_rbf_rkhs_distance(feature_distance, bandwidth)
    expected = float(np.linalg.norm(first - second))
    assert abs(recovered - expected) < 1e-14
