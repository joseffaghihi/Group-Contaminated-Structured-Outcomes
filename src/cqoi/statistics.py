from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.stats import beta


def squared_euclidean_matrix(x: np.ndarray, y: np.ndarray | None = None) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    y = x if y is None else np.asarray(y, dtype=np.float64)
    x_norm = np.sum(x * x, axis=1)[:, None]
    y_norm = np.sum(y * y, axis=1)[None, :]
    return np.maximum(0.0, x_norm + y_norm - 2.0 * x @ y.T)


def median_bandwidth(x: np.ndarray) -> float:
    distances = squared_euclidean_matrix(x)
    upper = distances[np.triu_indices_from(distances, k=1)]
    positive = upper[upper > 0]
    if len(positive) == 0:
        return 1.0
    return float(math.sqrt(0.5 * np.median(positive)))


def rbf_kernel(x: np.ndarray, bandwidth: float) -> np.ndarray:
    if bandwidth <= 0:
        raise ValueError("Bandwidth must be positive.")
    return np.exp(-squared_euclidean_matrix(x) / (2.0 * bandwidth * bandwidth))


def mmd2_unbiased_from_kernel(kernel: np.ndarray, labels: np.ndarray) -> float:
    labels = np.asarray(labels, dtype=int)
    left = np.flatnonzero(labels == 0)
    right = np.flatnonzero(labels == 1)
    if len(left) < 2 or len(right) < 2:
        raise ValueError("Unbiased MMD requires at least two observations per group.")
    k_left = kernel[np.ix_(left, left)]
    k_right = kernel[np.ix_(right, right)]
    k_cross = kernel[np.ix_(left, right)]
    within_left = (k_left.sum() - np.trace(k_left)) / (len(left) * (len(left) - 1))
    within_right = (k_right.sum() - np.trace(k_right)) / (
        len(right) * (len(right) - 1)
    )
    return float(within_left + within_right - 2.0 * k_cross.mean())


def paired_swap_labels(pair_ids: np.ndarray, swap_bits: np.ndarray) -> np.ndarray:
    unique_pairs = np.unique(pair_ids)
    if len(unique_pairs) != len(swap_bits):
        raise ValueError("One swap bit is required per pair.")
    labels = np.empty(len(pair_ids), dtype=int)
    for pair_position, pair_id in enumerate(unique_pairs):
        indices = np.flatnonzero(pair_ids == pair_id)
        if len(indices) != 2:
            raise ValueError(f"Pair {pair_id!r} has {len(indices)} observations, expected two.")
        labels[indices] = [swap_bits[pair_position], 1 - swap_bits[pair_position]]
    return labels


def exact_paired_mmd_test(
    kernel: np.ndarray,
    observed_labels: np.ndarray,
    pair_ids: np.ndarray,
) -> dict:
    pair_ids = np.asarray(pair_ids)
    observed_labels = np.asarray(observed_labels, dtype=int)
    unique_pairs = np.unique(pair_ids)
    if len(unique_pairs) > 20:
        raise ValueError("Exact enumeration is restricted to at most 20 pairs.")
    observed = mmd2_unbiased_from_kernel(kernel, observed_labels)
    permutation_statistics = []
    for bits in itertools.product((0, 1), repeat=len(unique_pairs)):
        labels = paired_swap_labels(pair_ids, np.asarray(bits, dtype=int))
        permutation_statistics.append(mmd2_unbiased_from_kernel(kernel, labels))
    permutation_statistics = np.asarray(permutation_statistics)
    tolerance = 1e-12
    exceedances = int(np.sum(permutation_statistics >= observed - tolerance))
    p_value = exceedances / len(permutation_statistics)
    return {
        "statistic": observed,
        "p_value": float(p_value),
        "permutations": int(len(permutation_statistics)),
        "exceedances": exceedances,
        "null_mean": float(permutation_statistics.mean()),
        "null_sd": float(permutation_statistics.std(ddof=1)),
    }


def paired_cluster_bootstrap_mmd(
    features: np.ndarray,
    labels: np.ndarray,
    pair_ids: np.ndarray,
    bandwidth: float,
    *,
    replicates: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    pair_ids = np.asarray(pair_ids)
    unique_pairs = np.unique(pair_ids)
    lookup = {
        pair_id: np.flatnonzero(pair_ids == pair_id)
        for pair_id in unique_pairs
    }
    statistics = np.empty(replicates, dtype=np.float64)
    for replicate in range(replicates):
        sampled_pairs = rng.choice(unique_pairs, size=len(unique_pairs), replace=True)
        indices = np.concatenate([lookup[pair_id] for pair_id in sampled_pairs])
        sampled_features = features[indices]
        sampled_labels = labels[indices]
        statistics[replicate] = mmd2_unbiased_from_kernel(
            rbf_kernel(sampled_features, bandwidth), sampled_labels
        )
    lower, upper = np.quantile(statistics, [0.025, 0.975])
    return {
        "replicates": int(replicates),
        "seed": int(seed),
        "percentile_95_ci": [float(lower), float(upper)],
        "bootstrap_mean": float(statistics.mean()),
        "bootstrap_sd": float(statistics.std(ddof=1)),
    }


def clopper_pearson(successes: int, trials: int, confidence: float = 0.95) -> list[float]:
    if not 0 <= successes <= trials or trials <= 0:
        raise ValueError("Invalid binomial counts.")
    alpha = 1.0 - confidence
    lower = 0.0 if successes == 0 else beta.ppf(alpha / 2, successes, trials - successes + 1)
    upper = (
        1.0
        if successes == trials
        else beta.ppf(1 - alpha / 2, successes + 1, trials - successes)
    )
    return [float(lower), float(upper)]


def holm_adjust(p_values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    count = len(ordered)
    adjusted = {}
    running = 0.0
    for rank, (name, value) in enumerate(ordered):
        candidate = min(1.0, (count - rank) * value)
        running = max(running, candidate)
        adjusted[name] = running
    return adjusted

