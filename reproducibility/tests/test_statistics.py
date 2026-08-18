from __future__ import annotations

import numpy as np

from cqoi.statistics import (
    exact_paired_mmd_test,
    median_bandwidth,
    rbf_kernel,
)


def test_exact_paired_test_enumerates_all_assignments() -> None:
    features = np.array([[0.0], [0.1], [1.0], [1.1], [2.0], [2.1]])
    labels = np.array([0, 1, 0, 1, 0, 1])
    pairs = np.array([0, 0, 1, 1, 2, 2])
    kernel = rbf_kernel(features, median_bandwidth(features))
    result = exact_paired_mmd_test(kernel, labels, pairs)
    assert result["permutations"] == 8
    assert 0.0 <= result["p_value"] <= 1.0


def test_exact_paired_test_enumerates_2_to_the_8_assignments() -> None:
    features = np.arange(16, dtype=float)[:, None]
    labels = np.tile([0, 1], 8)
    pairs = np.repeat(np.arange(8), 2)
    kernel = rbf_kernel(features, median_bandwidth(features))
    result = exact_paired_mmd_test(kernel, labels, pairs)
    assert result["permutations"] == 256
    assert result["exceedances"] == round(result["p_value"] * 256)


def test_identical_paired_features_do_not_reject() -> None:
    base = np.array([[0.0], [1.0], [2.0], [3.0]])
    features = np.repeat(base, 2, axis=0)
    labels = np.tile([0, 1], len(base))
    pairs = np.repeat(np.arange(len(base)), 2)
    kernel = rbf_kernel(features, median_bandwidth(features))
    result = exact_paired_mmd_test(kernel, labels, pairs)
    assert result["p_value"] == 1.0
