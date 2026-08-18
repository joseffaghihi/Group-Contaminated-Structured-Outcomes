from __future__ import annotations

import itertools

import numpy as np

from cqoi.sensitivity import (
    binary_table,
    critical_gamma,
    exact_paired_mmd_rosenbaum_bounds,
    rosenbaum_event_probability_bounds,
)
from cqoi.statistics import exact_paired_mmd_test, median_bandwidth, rbf_kernel


def test_gamma_one_recovers_the_exact_randomization_p_value() -> None:
    features = np.asarray(
        [[0.0], [1.0], [0.1], [1.2], [0.2], [1.4], [0.3], [1.7]],
        dtype=float,
    )
    labels = np.tile([0, 1], 4)
    pairs = np.repeat(np.arange(4), 2)
    kernel = rbf_kernel(features, median_bandwidth(features))
    exact = exact_paired_mmd_test(kernel, labels, pairs)
    sensitivity = exact_paired_mmd_rosenbaum_bounds(
        kernel,
        labels,
        pairs,
        gamma=1.0,
    )
    assert abs(sensitivity["lower_probability"] - exact["p_value"]) < 1e-14
    assert abs(sensitivity["upper_probability"] - exact["p_value"]) < 1e-14


def test_zero_bit_binary_table_has_one_empty_assignment() -> None:
    table = binary_table(0)
    assert table.shape == (1, 0)
    assert table.dtype == np.int8


def test_pairwise_row_flips_preserve_exact_and_sensitivity_results() -> None:
    features = np.asarray(
        [[0.0], [1.0], [0.1], [1.2], [0.2], [1.4], [0.3], [1.7]],
        dtype=float,
    )
    labels = np.tile([0, 1], 4)
    pairs = np.repeat(np.arange(4), 2)
    kernel = rbf_kernel(features, median_bandwidth(features))
    baseline_exact = exact_paired_mmd_test(kernel, labels, pairs)
    baseline_bound = exact_paired_mmd_rosenbaum_bounds(
        kernel,
        labels,
        pairs,
        gamma=2.0,
    )

    permutation = np.asarray([1, 0, 2, 3, 5, 4, 6, 7])
    flipped_kernel = kernel[np.ix_(permutation, permutation)]
    flipped_labels = labels[permutation]
    flipped_pairs = pairs[permutation]
    flipped_exact = exact_paired_mmd_test(
        flipped_kernel,
        flipped_labels,
        flipped_pairs,
    )
    flipped_bound = exact_paired_mmd_rosenbaum_bounds(
        flipped_kernel,
        flipped_labels,
        flipped_pairs,
        gamma=2.0,
    )
    assert abs(flipped_exact["statistic"] - baseline_exact["statistic"]) < 1e-14
    assert flipped_exact["p_value"] == baseline_exact["p_value"]
    assert abs(
        flipped_bound["upper_probability"]
        - baseline_bound["upper_probability"]
    ) < 1e-14


def test_critical_gamma_respects_a_maximum_below_two() -> None:
    features = np.asarray(
        [[0.0], [1.0], [0.1], [1.2], [0.2], [1.4], [0.3], [1.7]],
        dtype=float,
    )
    labels = np.tile([0, 1], 4)
    pairs = np.repeat(np.arange(4), 2)
    kernel = rbf_kernel(features, median_bandwidth(features))
    result = critical_gamma(
        kernel,
        labels,
        pairs,
        alpha=0.99,
        maximum_gamma=1.5,
    )
    assert not result["crossed"]
    assert result["upper_bracket_gamma"] == 1.5


def test_vertex_optimization_matches_independent_brute_force() -> None:
    assignments = binary_table(3)
    event = np.asarray([sum(row) >= 2 for row in assignments], dtype=bool)
    gamma = 2.5
    result = rosenbaum_event_probability_bounds(
        event,
        gamma,
        assignments=assignments,
    )
    lower, upper = 1.0 / (1.0 + gamma), gamma / (1.0 + gamma)
    values = []
    for endpoint_choice in itertools.product((lower, upper), repeat=3):
        probability = 0.0
        for row, included in zip(assignments, event, strict=True):
            if included:
                probability += np.prod(
                    [p if bit else 1.0 - p for bit, p in zip(row, endpoint_choice)]
                )
        values.append(probability)
    assert abs(result["lower_probability"] - min(values)) < 1e-14
    assert abs(result["upper_probability"] - max(values)) < 1e-14


def test_rosenbaum_bounds_expand_monotonically_with_gamma() -> None:
    assignments = binary_table(4)
    event = np.asarray([row[0] + row[1] + row[2] >= 2 for row in assignments])
    at_one = rosenbaum_event_probability_bounds(event, 1.0)
    at_two = rosenbaum_event_probability_bounds(event, 2.0)
    assert at_two["lower_probability"] <= at_one["lower_probability"]
    assert at_two["upper_probability"] >= at_one["upper_probability"]


def test_extreme_finite_gamma_is_stable_in_log_space() -> None:
    assignments = binary_table(3)
    event = np.asarray([np.array_equal(row, [1, 0, 1]) for row in assignments])
    result = rosenbaum_event_probability_bounds(event, 1e100)
    assert np.isfinite(result["lower_probability"])
    assert np.isfinite(result["upper_probability"])
    assert 0.0 <= result["lower_probability"] <= result["upper_probability"] <= 1.0
    assert result["upper_probability"] > 1.0 - 1e-14
