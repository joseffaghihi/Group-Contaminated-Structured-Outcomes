"""Exact Rosenbaum sensitivity bounds for paired randomization tests.

This module is deliberately separate from :mod:`cqoi.statistics`, whose hash
was frozen before the confirmatory RxRx1 analysis.  The calculations here are
post-analysis sensitivity diagnostics and do not alter the original test.
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np

from .statistics import mmd2_unbiased_from_kernel, paired_swap_labels


def binary_table(number_of_bits: int) -> np.ndarray:
    """Return all binary rows in lexicographic product order."""
    if number_of_bits < 0:
        raise ValueError("number_of_bits must be nonnegative.")
    if number_of_bits == 0:
        return np.empty((1, 0), dtype=np.int8)
    return np.asarray(
        list(itertools.product((0, 1), repeat=number_of_bits)),
        dtype=np.int8,
    ).reshape(-1, number_of_bits)


def observed_paired_bits(labels: np.ndarray, pair_ids: np.ndarray) -> np.ndarray:
    """Encode the observed orientation using ``paired_swap_labels`` ordering."""
    labels = np.asarray(labels, dtype=int)
    pair_ids = np.asarray(pair_ids)
    if labels.ndim != 1 or pair_ids.ndim != 1 or labels.shape != pair_ids.shape:
        raise ValueError("labels and pair_ids must be one-dimensional and aligned.")
    bits: list[int] = []
    for pair_id in np.unique(pair_ids):
        indices = np.flatnonzero(pair_ids == pair_id)
        if len(indices) != 2:
            raise ValueError(f"Pair {pair_id!r} must contain exactly two units.")
        pair_labels = labels[indices]
        if sorted(pair_labels.tolist()) != [0, 1]:
            raise ValueError(f"Pair {pair_id!r} must contain labels zero and one.")
        bits.append(int(pair_labels[0]))
    return np.asarray(bits, dtype=np.int8)


def enumerate_paired_mmd(
    kernel: np.ndarray,
    pair_ids: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Enumerate assignment bits and their unbiased squared-MMD statistics."""
    kernel = np.asarray(kernel, dtype=np.float64)
    pair_ids = np.asarray(pair_ids)
    if kernel.ndim != 2 or kernel.shape[0] != kernel.shape[1]:
        raise ValueError("kernel must be square.")
    if kernel.shape[0] != len(pair_ids):
        raise ValueError("kernel and pair_ids have incompatible dimensions.")
    number_of_pairs = len(np.unique(pair_ids))
    if number_of_pairs > 20:
        raise ValueError("Exact enumeration is restricted to at most 20 pairs.")
    assignments = binary_table(number_of_pairs)
    statistics = np.empty(len(assignments), dtype=np.float64)
    for index, bits in enumerate(assignments):
        labels = paired_swap_labels(pair_ids, bits)
        statistics[index] = mmd2_unbiased_from_kernel(kernel, labels)
    return assignments, statistics


def rosenbaum_event_probability_bounds(
    event: np.ndarray,
    gamma: float,
    *,
    assignments: np.ndarray | None = None,
) -> dict[str, Any]:
    r"""Optimize an assignment-event probability over Rosenbaum's Gamma box.

    Conditional on fixed potential outcomes, this calculation assumes the
    paired assignment bits are independent, with each probability satisfying
    ``1/(1+Gamma) <= pi_b <= Gamma/(1+Gamma)``.  The event probability is a
    multilinear function of the vector of probabilities, so both extrema are
    attained at vertices of this box.  All vertices are enumerated exactly.
    """
    if not math.isfinite(gamma) or gamma < 1.0:
        raise ValueError("gamma must be finite and at least one.")
    event = np.asarray(event, dtype=bool)
    if event.ndim != 1 or len(event) == 0:
        raise ValueError("event must be a nonempty one-dimensional array.")
    number_of_assignments = len(event)
    number_of_pairs = int(round(math.log2(number_of_assignments)))
    if 2**number_of_pairs != number_of_assignments:
        raise ValueError("event length must be a power of two.")
    if assignments is None:
        assignments = binary_table(number_of_pairs)
    if number_of_pairs > 12:
        raise ValueError(
            "Exact Gamma-box optimization is restricted to at most 12 pairs."
        )
    assignments = np.asarray(assignments, dtype=np.int8)
    if assignments.shape != (number_of_assignments, number_of_pairs):
        raise ValueError("assignments has the wrong shape.")
    if not np.all((assignments == 0) | (assignments == 1)):
        raise ValueError("assignments must be binary.")

    vertices = binary_table(number_of_pairs)
    # Compute endpoint probabilities in log space.  Forming Gamma/(1+Gamma)
    # directly rounds to one for very large finite Gamma, whereas the exact
    # log probability -log(1+1/Gamma) remains representable.
    log_lower = -math.log1p(gamma)
    log_upper = -math.log1p(1.0 / gamma)
    assignment_ones = assignments.sum(axis=1, dtype=np.int64)
    vertex_ones = vertices.sum(axis=1, dtype=np.int64)
    both_one = assignments.astype(np.int64) @ vertices.astype(np.int64).T
    matching_bits = (
        number_of_pairs
        - assignment_ones[:, None]
        - vertex_ones[None, :]
        + 2 * both_one
    )
    # Rows index assignments and columns index vertices of the Gamma box.  A
    # bit matching the vertex orientation receives the upper endpoint.
    log_weights = (
        matching_bits * log_upper
        + (number_of_pairs - matching_bits) * log_lower
    )
    weights = np.exp(log_weights)
    column_sums = weights.sum(axis=0)
    if not np.allclose(column_sums, 1.0, atol=2e-14, rtol=2e-14):
        raise RuntimeError("Assignment probabilities did not normalize to one.")
    event_probabilities = weights[event].sum(axis=0)
    lower_index = int(np.argmin(event_probabilities))
    upper_index = int(np.argmax(event_probabilities))
    return {
        "gamma": float(gamma),
        "lower_probability": float(event_probabilities[lower_index]),
        "upper_probability": float(event_probabilities[upper_index]),
        "lower_endpoint_bits": vertices[lower_index].astype(int).tolist(),
        "upper_endpoint_bits": vertices[upper_index].astype(int).tolist(),
        "box_vertices": int(len(vertices)),
        "event_assignments": int(event.sum()),
        "total_assignments": int(len(event)),
    }


def exact_paired_mmd_rosenbaum_bounds(
    kernel: np.ndarray,
    observed_labels: np.ndarray,
    pair_ids: np.ndarray,
    gamma: float,
    *,
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    """Return exact one-sided Gamma bounds for the paired MMD tail event."""
    if tolerance < 0:
        raise ValueError("tolerance must be nonnegative.")
    pair_ids = np.asarray(pair_ids)
    observed_labels = np.asarray(observed_labels, dtype=int)
    assignments, statistics = enumerate_paired_mmd(kernel, pair_ids)
    observed_bits = observed_paired_bits(observed_labels, pair_ids)
    matches = np.all(assignments == observed_bits[None, :], axis=1)
    if int(matches.sum()) != 1:
        raise RuntimeError("The observed assignment was not uniquely enumerated.")
    observed_statistic = float(statistics[np.flatnonzero(matches)[0]])
    event = statistics >= observed_statistic - tolerance
    bounds = rosenbaum_event_probability_bounds(
        event,
        gamma,
        assignments=assignments,
    )
    bounds.update(
        observed_statistic=observed_statistic,
        observed_bits=observed_bits.astype(int).tolist(),
        tail="greater_than_or_equal_with_fixed_numerical_tolerance",
        tolerance=float(tolerance),
    )
    return bounds


def critical_gamma(
    kernel: np.ndarray,
    observed_labels: np.ndarray,
    pair_ids: np.ndarray,
    *,
    alpha: float = 0.05,
    maximum_gamma: float = 1_000.0,
    gamma_tolerance: float = 1e-8,
) -> dict[str, float | bool]:
    """Find where the worst-case upper p-value first reaches ``alpha``.

    The feasible Gamma box expands with Gamma, hence the optimized upper tail
    probability is nondecreasing.  Bisection therefore brackets the crossing.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between zero and one.")
    if maximum_gamma < 1.0 or not math.isfinite(maximum_gamma):
        raise ValueError("maximum_gamma must be finite and at least one.")
    if gamma_tolerance <= 0.0:
        raise ValueError("gamma_tolerance must be positive.")

    def upper(gamma: float) -> float:
        return float(
            exact_paired_mmd_rosenbaum_bounds(
                kernel,
                observed_labels,
                pair_ids,
                gamma,
            )["upper_probability"]
        )

    p_at_one = upper(1.0)
    if p_at_one >= alpha:
        return {
            "crossed": True,
            "critical_gamma": 1.0,
            "upper_p_at_critical_gamma": p_at_one,
            "lower_bracket_gamma": 1.0,
            "upper_bracket_gamma": 1.0,
        }

    lower_gamma = 1.0
    upper_gamma = min(2.0, maximum_gamma)
    upper_p = upper(upper_gamma)
    while upper_p < alpha and upper_gamma < maximum_gamma:
        lower_gamma = upper_gamma
        upper_gamma = min(2.0 * upper_gamma, maximum_gamma)
        upper_p = upper(upper_gamma)
    if upper_p < alpha:
        return {
            "crossed": False,
            "critical_gamma": float("nan"),
            "upper_p_at_critical_gamma": upper_p,
            "lower_bracket_gamma": lower_gamma,
            "upper_bracket_gamma": upper_gamma,
        }

    while upper_gamma - lower_gamma > gamma_tolerance:
        midpoint = (lower_gamma + upper_gamma) / 2.0
        if upper(midpoint) >= alpha:
            upper_gamma = midpoint
        else:
            lower_gamma = midpoint
    return {
        "crossed": True,
        "critical_gamma": upper_gamma,
        "upper_p_at_critical_gamma": upper(upper_gamma),
        "lower_bracket_gamma": lower_gamma,
        "upper_bracket_gamma": upper_gamma,
    }
