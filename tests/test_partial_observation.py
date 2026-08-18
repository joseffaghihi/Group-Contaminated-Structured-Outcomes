from __future__ import annotations

import numpy as np

from cqoi.experiment import canonical_translation_c4


def test_fixed_crop_can_merge_distinct_rigid_motion_orbits() -> None:
    """A crop collision witnesses failure of full-orbit observability."""
    with_hidden_support = np.zeros((1, 7, 7), dtype=np.uint8)
    with_hidden_support[0, 3, 3] = 255
    with_hidden_support[0, 0, 0] = 255

    visible_only = np.zeros((1, 7, 7), dtype=np.uint8)
    visible_only[0, 3, 3] = 255

    crop = (slice(None), slice(2, 5), slice(2, 5))
    np.testing.assert_array_equal(
        with_hidden_support[crop],
        visible_only[crop],
    )

    first_code = canonical_translation_c4(with_hidden_support)
    second_code = canonical_translation_c4(visible_only)
    assert first_code.shape != second_code.shape or not np.array_equal(
        first_code,
        second_code,
    )

