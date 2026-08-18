"""Stable zero-dimensional persistence diagnostics for quotient images.

The confirmatory Euler signature thresholds and cleans a binary mask, operations
that are not continuous in pixel intensity.  This separate module instead uses
the lower-star filtration of a fixed four-neighbour pixel grid, for which the
standard bottleneck stability inequality applies.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching


@dataclass(frozen=True)
class PersistenceDiagram0D:
    """Finite birth--death pairs and births of essential zero-dimensional bars."""

    finite: np.ndarray
    essential_births: np.ndarray


def _validate_diagram(diagram: PersistenceDiagram0D) -> tuple[np.ndarray, np.ndarray]:
    finite = np.asarray(diagram.finite, dtype=np.float64)
    essential = np.asarray(diagram.essential_births, dtype=np.float64)
    if finite.ndim != 2 or finite.shape[1] != 2:
        raise ValueError("finite diagram must have shape (n, 2).")
    if essential.ndim != 1:
        raise ValueError("essential_births must be one-dimensional.")
    if not np.all(np.isfinite(finite)) or not np.all(np.isfinite(essential)):
        raise ValueError("diagram coordinates must be finite.")
    if np.any(finite[:, 1] < finite[:, 0]):
        raise ValueError("a death time cannot precede its birth time.")
    return finite, essential


def zero_dimensional_persistence(
    image: np.ndarray,
    *,
    drop_zero_persistence: bool = True,
) -> PersistenceDiagram0D:
    r"""Compute lower-star H0 persistence on a four-neighbour rectangular grid.

    A vertex enters at its pixel value and an edge enters at the maximum of its
    two endpoint values.  Union--find with the elder rule gives the finite bars;
    zero-length bars may be omitted because they lie on the persistence-diagram
    diagonal and do not affect bottleneck distance.
    """
    values_2d = np.asarray(image, dtype=np.float64)
    if values_2d.ndim != 2 or values_2d.size == 0:
        raise ValueError("image must be a nonempty two-dimensional array.")
    if not np.all(np.isfinite(values_2d)):
        raise ValueError("image values must be finite.")

    height, width = values_2d.shape
    values = values_2d.reshape(-1)
    number_of_vertices = len(values)
    parent = np.full(number_of_vertices, -1, dtype=np.int64)
    rank = np.zeros(number_of_vertices, dtype=np.int16)
    births = np.empty(number_of_vertices, dtype=np.float64)
    active = np.zeros(number_of_vertices, dtype=bool)
    finite_pairs: list[tuple[float, float]] = []

    def find(vertex: int) -> int:
        root = vertex
        while parent[root] != root:
            root = int(parent[root])
        while parent[vertex] != vertex:
            next_vertex = int(parent[vertex])
            parent[vertex] = root
            vertex = next_vertex
        return root

    def merge(first: int, second: int, death: float) -> None:
        first_root, second_root = find(first), find(second)
        if first_root == second_root:
            return
        first_key = (births[first_root], first_root)
        second_key = (births[second_root], second_root)
        if first_key <= second_key:
            survivor, deceased = first_root, second_root
        else:
            survivor, deceased = second_root, first_root
        finite_pairs.append((float(births[deceased]), float(death)))
        parent[deceased] = survivor
        if rank[survivor] == rank[deceased]:
            rank[survivor] += 1

    # Stable sorting makes the arbitrary handling of equal-time zero bars
    # deterministic.  Positive-length persistence is independent of this tie
    # ordering.
    for vertex in np.argsort(values, kind="stable"):
        vertex = int(vertex)
        active[vertex] = True
        parent[vertex] = vertex
        births[vertex] = values[vertex]
        row, column = divmod(vertex, width)
        neighbours = []
        if row > 0:
            neighbours.append(vertex - width)
        if row + 1 < height:
            neighbours.append(vertex + width)
        if column > 0:
            neighbours.append(vertex - 1)
        if column + 1 < width:
            neighbours.append(vertex + 1)
        for neighbour in neighbours:
            if active[neighbour]:
                merge(vertex, neighbour, float(values[vertex]))

    roots = sorted({find(vertex) for vertex in range(number_of_vertices)})
    essential = np.asarray([births[root] for root in roots], dtype=np.float64)
    finite = np.asarray(finite_pairs, dtype=np.float64).reshape(-1, 2)
    if drop_zero_persistence and len(finite):
        finite = finite[finite[:, 1] > finite[:, 0]]
    if len(finite):
        finite = finite[np.lexsort((finite[:, 1], finite[:, 0]))]
    essential.sort()
    return PersistenceDiagram0D(finite=finite, essential_births=essential)


def _finite_matching_exists(
    first: np.ndarray,
    second: np.ndarray,
    epsilon: float,
) -> bool:
    """Test the diagonal-augmented bottleneck matching at radius epsilon."""
    first_count, second_count = len(first), len(second)
    total = first_count + second_count
    if total == 0:
        return True
    rows: list[int] = []
    columns: list[int] = []

    if first_count and second_count:
        cross_distances = np.max(
            np.abs(first[:, None, :] - second[None, :, :]),
            axis=2,
        )
        eligible_first, eligible_second = np.nonzero(
            cross_distances <= epsilon
        )
        rows.extend(eligible_first.astype(int).tolist())
        columns.extend(eligible_second.astype(int).tolist())

    first_diagonal_cost = (first[:, 1] - first[:, 0]) / 2.0
    for index in np.flatnonzero(first_diagonal_cost <= epsilon):
        rows.append(int(index))
        columns.append(second_count + int(index))
    second_diagonal_cost = (second[:, 1] - second[:, 0]) / 2.0
    for index in np.flatnonzero(second_diagonal_cost <= epsilon):
        rows.append(first_count + int(index))
        columns.append(int(index))

    # Diagonal copies represent the same infinite-multiplicity diagonal, so
    # every left copy may match every right copy at zero cost.
    if first_count and second_count:
        diagonal_left = np.repeat(
            first_count + np.arange(second_count, dtype=int),
            first_count,
        )
        diagonal_right = np.tile(
            second_count + np.arange(first_count, dtype=int),
            second_count,
        )
        rows.extend(diagonal_left.tolist())
        columns.extend(diagonal_right.tolist())

    graph = csr_matrix(
        (
            np.ones(len(rows), dtype=np.int8),
            (np.asarray(rows, dtype=int), np.asarray(columns, dtype=int)),
        ),
        shape=(total, total),
    )
    matching = maximum_bipartite_matching(graph, perm_type="column")
    return bool(np.all(matching >= 0))


def bottleneck_distance_0d(
    first_diagram: PersistenceDiagram0D,
    second_diagram: PersistenceDiagram0D,
) -> float:
    """Compute the exact bottleneck distance between two finite H0 diagrams."""
    first, first_essential = _validate_diagram(first_diagram)
    second, second_essential = _validate_diagram(second_diagram)
    if len(first_essential) != len(second_essential):
        return math.inf
    essential_cost = (
        0.0
        if len(first_essential) == 0
        else float(
            np.max(
                np.abs(np.sort(first_essential) - np.sort(second_essential))
            )
        )
    )

    candidates = [0.0, essential_cost]
    if len(first):
        candidates.extend(((first[:, 1] - first[:, 0]) / 2.0).tolist())
    if len(second):
        candidates.extend(((second[:, 1] - second[:, 0]) / 2.0).tolist())
    if len(first) and len(second):
        candidates.extend(
            np.max(
                np.abs(first[:, None, :] - second[None, :, :]),
                axis=2,
            ).reshape(-1).tolist()
        )
    candidate_array = np.unique(np.asarray(candidates, dtype=np.float64))
    candidate_array.sort()

    lower, upper = 0, len(candidate_array) - 1
    while lower < upper:
        middle = (lower + upper) // 2
        epsilon = float(candidate_array[middle])
        feasible = (
            epsilon >= essential_cost
            and _finite_matching_exists(first, second, epsilon)
        )
        if feasible:
            upper = middle
        else:
            lower = middle + 1
    distance = float(candidate_array[lower])
    if distance < essential_cost or not _finite_matching_exists(
        first,
        second,
        distance,
    ):
        raise RuntimeError("Failed to find a valid bottleneck matching.")
    return distance


def rbf_rkhs_distance(
    first: np.ndarray,
    second: np.ndarray,
    bandwidth: float,
) -> float:
    r"""Distance between Gaussian-kernel feature maps of two vectors."""
    if bandwidth <= 0.0 or not math.isfinite(bandwidth):
        raise ValueError("bandwidth must be finite and positive.")
    first = np.asarray(first, dtype=np.float64).reshape(-1)
    second = np.asarray(second, dtype=np.float64).reshape(-1)
    if first.shape != second.shape:
        raise ValueError("inputs must have the same number of coordinates.")
    squared_distance = float(np.sum((first - second) ** 2))
    kernel_value = math.exp(-squared_distance / (2.0 * bandwidth**2))
    return math.sqrt(max(0.0, 2.0 - 2.0 * kernel_value))


def l2_from_rbf_rkhs_distance(distance: float, bandwidth: float) -> float:
    r"""Invert the Gaussian feature-distance formula below its saturation."""
    if bandwidth <= 0.0 or not math.isfinite(bandwidth):
        raise ValueError("bandwidth must be finite and positive.")
    if distance < 0.0 or distance >= math.sqrt(2.0):
        raise ValueError("distance must lie in [0, sqrt(2)).")
    return bandwidth * math.sqrt(-2.0 * math.log1p(-(distance**2) / 2.0))
