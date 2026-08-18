from __future__ import annotations

import numpy as np

from cqoi.invariants import canonical_c4, finite_ect, rotate_c4


def test_c4_canonicalization_is_exactly_invariant() -> None:
    rng = np.random.default_rng(73)
    image = rng.integers(0, 256, size=(6, 16, 16), dtype=np.uint8)
    reference = canonical_c4(image)
    for quarter_turns in range(4):
        transformed = rotate_c4(image, quarter_turns)
        assert np.array_equal(canonical_c4(transformed), reference)


def test_finite_ect_is_c4_invariant_after_canonicalization() -> None:
    mask = np.zeros((21, 21), dtype=bool)
    mask[2:8, 3:7] = True
    mask[12:18, 11:19] = True
    mask[14:16, 14:17] = False
    reference = finite_ect(canonical_c4(mask), thresholds=17)
    for quarter_turns in range(4):
        transformed = rotate_c4(mask, quarter_turns)
        candidate = finite_ect(canonical_c4(transformed), thresholds=17)
        assert np.array_equal(candidate, reference)

