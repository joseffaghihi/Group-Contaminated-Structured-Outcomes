from __future__ import annotations

import numpy as np

from .experiment import finite_directional_euler_transform


def rotate_c4(array: np.ndarray, quarter_turns: int) -> np.ndarray:
    """Apply a counterclockwise quarter-turn rotation."""
    return np.rot90(
        np.asarray(array),
        k=int(quarter_turns) % 4,
        axes=(-2, -1),
    ).copy()


def canonical_c4(array: np.ndarray) -> np.ndarray:
    """Lexicographically minimal representative of a finite C4 orbit.

    This compatibility helper is used only by the low-level tests. The
    confirmatory well representation is
    :func:`cqoi.experiment.canonical_translation_c4`, which also removes
    integer translations by support normalization.
    """
    candidates = [rotate_c4(array, k) for k in range(4)]
    keys = [
        (
            int(candidate.shape[-2]),
            int(candidate.shape[-1]),
            candidate.tobytes(order="C"),
        )
        for candidate in candidates
    ]
    return candidates[min(range(4), key=keys.__getitem__)]


def finite_ect(mask: np.ndarray, thresholds: int = 25) -> np.ndarray:
    """Compatibility name for the experiment's planar finite Euler transform."""
    return finite_directional_euler_transform(mask, levels=thresholds)
