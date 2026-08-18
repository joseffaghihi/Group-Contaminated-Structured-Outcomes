from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage

from .progress import ProgressTracker
from .statistics import (
    clopper_pearson,
    exact_paired_mmd_test,
    holm_adjust,
    median_bandwidth,
    mmd2_unbiased_from_kernel,
    rbf_kernel,
)


@dataclass(frozen=True)
class PairSpec:
    pair_id: str
    left_id: int
    right_id: int
    left_name: str
    right_name: str
    role: str


@dataclass(frozen=True)
class WellRecord:
    pair_id: str
    experiment: str
    experiment_number: int
    plate: int
    well_id: str
    well: str
    sirna_id: int
    sirna: str
    label: int
    site_paths: tuple[tuple[str, ...], tuple[str, ...]]


@dataclass(frozen=True)
class ExperimentConfig:
    image_size: int = 64
    padding: int = 16
    max_integer_shift: int = 8
    nuisance_seeds: tuple[int, ...] = tuple(range(20_260_731, 20_260_751))
    bootstrap_replicates: int = 10_000
    bootstrap_seed: int = 926_031
    ect_levels: int = 25
    ect_min_component_size: int = 4
    nuclear_channel: int = 0
    invariance_tolerance: float = 1e-12
    approximate_angles: tuple[float, ...] = (5.0, 10.0, 20.0)
    approximate_crop_pixels: int = 2
    approximate_noise_sd: float = 2.0

    def validate(self) -> None:
        if self.image_size < 8:
            raise ValueError("image_size must be at least 8.")
        if self.padding < self.max_integer_shift:
            raise ValueError("padding must be at least max_integer_shift.")
        if self.max_integer_shift < 0:
            raise ValueError("max_integer_shift must be nonnegative.")
        if not self.nuisance_seeds:
            raise ValueError("At least one nuisance seed is required.")
        if self.bootstrap_replicates < 1:
            raise ValueError("bootstrap_replicates must be positive.")
        if self.ect_levels < 2:
            raise ValueError("ect_levels must be at least two.")
        if self.ect_min_component_size < 1:
            raise ValueError("ect_min_component_size must be positive.")
        if not 0 <= self.nuclear_channel < 6:
            raise ValueError("nuclear_channel must be one of the six channels.")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    temporary.replace(destination)


def _normalise_experiment_number(value: Any) -> int:
    text = str(value)
    try:
        return int(text.rsplit("-", 1)[-1])
    except ValueError as error:
        raise ValueError(f"Cannot parse experiment number from {value!r}.") from error


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any | None:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _member_id(member: Any) -> int:
    if isinstance(member, Mapping):
        value = _first_present(
            member,
            ("sirna_id", "id", "treatment_id", "intervention_id"),
        )
        if value is None:
            raise ValueError(f"Pair member lacks a siRNA identifier: {member!r}")
        return int(value)
    return int(member)


def _member_name(member: Any, fallback: str) -> str:
    if isinstance(member, Mapping):
        value = _first_present(
            member,
            ("sirna", "name", "treatment", "intervention"),
        )
        if value is not None:
            return str(value)
    return fallback


def parse_pair_specs(manifest: Mapping[str, Any]) -> list[PairSpec]:
    """Parse the corrected pair manifest without assuming one exact JSON spelling."""
    raw_pairs = manifest.get("selected_pairs")
    if raw_pairs is None:
        raise ValueError(
            "The manifest has no 'selected_pairs'. The invalidated legacy "
            "'selected_sirna_ids' manifest is intentionally not accepted."
        )
    if isinstance(raw_pairs, Mapping):
        iterable: list[tuple[str | None, Any]] = [
            (str(pair_id), value) for pair_id, value in raw_pairs.items()
        ]
    elif isinstance(raw_pairs, Sequence) and not isinstance(raw_pairs, (str, bytes)):
        iterable = [(None, value) for value in raw_pairs]
    else:
        raise TypeError("selected_pairs must be a list or mapping.")

    specs: list[PairSpec] = []
    for index, (mapping_pair_id, raw_pair) in enumerate(iterable):
        pair_id = mapping_pair_id or f"pair_{index + 1:02d}"
        role = "primary" if index == 0 else "replication"
        left_name = ""
        right_name = ""

        if isinstance(raw_pair, Mapping):
            pair_id = str(raw_pair.get("pair_id", raw_pair.get("id", pair_id)))
            if bool(raw_pair.get("primary", False)):
                role = "primary"
            else:
                role = str(raw_pair.get("role", role)).lower()

            members = _first_present(
                raw_pair,
                (
                    "members",
                    "sirna_ids",
                    "selected_sirna_ids",
                    "interventions",
                    "treatments",
                    "sirnas",
                ),
            )
            if members is None:
                left_value = _first_present(
                    raw_pair,
                    (
                        "left_sirna_id",
                        "sirna_a_id",
                        "control_sirna_id",
                        "first_sirna_id",
                    ),
                )
                right_value = _first_present(
                    raw_pair,
                    (
                        "right_sirna_id",
                        "sirna_b_id",
                        "treatment_sirna_id",
                        "second_sirna_id",
                    ),
                )
                if left_value is None or right_value is None:
                    raise ValueError(f"Cannot find two siRNA IDs in {raw_pair!r}.")
                members = [left_value, right_value]
                left_name = str(
                    _first_present(
                        raw_pair,
                        ("left_sirna", "sirna_a", "control_sirna", "first_sirna"),
                    )
                    or ""
                )
                right_name = str(
                    _first_present(
                        raw_pair,
                        ("right_sirna", "sirna_b", "treatment_sirna", "second_sirna"),
                    )
                    or ""
                )
        else:
            members = raw_pair

        if not isinstance(members, Sequence) or isinstance(members, (str, bytes)):
            raise TypeError(f"Pair members must be a two-element sequence: {members!r}")
        if len(members) != 2:
            raise ValueError(f"Pair {pair_id!r} has {len(members)} members, expected two.")
        left_id, right_id = (_member_id(members[0]), _member_id(members[1]))
        left_name = left_name or _member_name(members[0], str(left_id))
        right_name = right_name or _member_name(members[1], str(right_id))
        if isinstance(raw_pair, Mapping):
            named_members = raw_pair.get("sirnas")
            if (
                isinstance(named_members, Sequence)
                and not isinstance(named_members, (str, bytes))
                and len(named_members) == 2
            ):
                if left_name == str(left_id):
                    left_name = str(named_members[0])
                if right_name == str(right_id):
                    right_name = str(named_members[1])
        if left_id == right_id:
            raise ValueError(f"Pair {pair_id!r} contains the same siRNA twice.")
        specs.append(
            PairSpec(
                pair_id=pair_id,
                left_id=left_id,
                right_id=right_id,
                left_name=left_name,
                right_name=right_name,
                role=role,
            )
        )

    primary_indices = [index for index, spec in enumerate(specs) if spec.role == "primary"]
    if len(primary_indices) == 0:
        specs[0] = PairSpec(**{**asdict(specs[0]), "role": "primary"})
    elif len(primary_indices) > 1:
        raise ValueError("Exactly one pair may be marked primary.")
    pair_ids = [spec.pair_id for spec in specs]
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("Pair IDs must be unique.")
    all_members = [member for spec in specs for member in (spec.left_id, spec.right_id)]
    if len(all_members) != len(set(all_members)):
        raise ValueError("The corrected benchmark requires disjoint siRNA pairs.")
    return specs


def _candidate_image_paths(
    data_root: Path,
    experiment: str,
    plate: int,
    well: str,
    site: int,
    channel: int,
) -> Iterable[Path]:
    relative = Path(experiment) / f"Plate{plate}" / f"{well}_s{site}_w{channel}.png"
    yield data_root / "rxrx1" / "images" / relative
    yield data_root / "images" / relative
    yield data_root / relative


def _resolve_image_path(
    data_root: Path,
    experiment: str,
    plate: int,
    well: str,
    site: int,
    channel: int,
) -> Path:
    for candidate in _candidate_image_paths(
        data_root, experiment, plate, well, site, channel
    ):
        if candidate.is_file():
            return candidate
    expected = next(
        iter(
            _candidate_image_paths(
                data_root, experiment, plate, well, site, channel
            )
        )
    )
    raise FileNotFoundError(f"Missing RxRx1 image; first expected location: {expected}")


def resolve_well_records(
    manifest: Mapping[str, Any],
    metadata_path: str | Path,
    data_root: str | Path,
    *,
    require_validation_experiments: int | None = 8,
) -> tuple[list[PairSpec], list[WellRecord]]:
    specs = parse_pair_specs(manifest)
    experiments = [
        _normalise_experiment_number(value)
        for value in manifest.get("validation_experiments", [])
    ]
    if not experiments:
        raise ValueError("Manifest must declare validation_experiments.")
    if len(experiments) != len(set(experiments)):
        raise ValueError("validation_experiments contains duplicates.")
    if (
        require_validation_experiments is not None
        and len(experiments) != require_validation_experiments
    ):
        raise ValueError(
            f"Expected {require_validation_experiments} frozen validation experiments "
            f"for 2^{require_validation_experiments} exact swaps, found {len(experiments)}."
        )

    metadata = pd.read_csv(metadata_path)
    required_columns = {
        "site_id",
        "well_id",
        "cell_type",
        "experiment",
        "plate",
        "well",
        "site",
        "sirna",
        "sirna_id",
    }
    missing = sorted(required_columns - set(metadata.columns))
    if missing:
        raise ValueError(f"Metadata is missing columns: {missing}")
    metadata = metadata.copy()
    metadata["_experiment_number"] = metadata["experiment"].map(
        _normalise_experiment_number
    )
    cell_type = str(manifest.get("cell_type", "HUVEC"))
    metadata = metadata[
        (metadata["cell_type"].astype(str) == cell_type)
        & metadata["_experiment_number"].isin(experiments)
    ]
    root = Path(data_root)
    records: list[WellRecord] = []

    for spec in specs:
        for experiment_number in experiments:
            pair_rows = metadata[
                (metadata["_experiment_number"] == experiment_number)
                & metadata["sirna_id"].isin([spec.left_id, spec.right_id])
            ]
            member_records: list[WellRecord] = []
            for label, sirna_id in enumerate((spec.left_id, spec.right_id)):
                member_rows = pair_rows[pair_rows["sirna_id"] == sirna_id]
                wells = member_rows["well_id"].drop_duplicates().tolist()
                if len(wells) != 1:
                    raise ValueError(
                        f"{spec.pair_id}, experiment {experiment_number}, siRNA "
                        f"{sirna_id}: expected one well, found {len(wells)}."
                    )
                well_rows = member_rows[member_rows["well_id"] == wells[0]].sort_values(
                    "site"
                )
                sites = sorted(int(value) for value in well_rows["site"].unique())
                if sites != [1, 2]:
                    raise ValueError(
                        f"Well {wells[0]!r} must contain sites 1 and 2; found {sites}."
                    )
                first = well_rows.iloc[0]
                site_paths = tuple(
                    tuple(
                        str(
                            _resolve_image_path(
                                root,
                                str(first["experiment"]),
                                int(first["plate"]),
                                str(first["well"]),
                                site,
                                channel,
                            )
                        )
                        for channel in range(1, 7)
                    )
                    for site in sites
                )
                member_records.append(
                    WellRecord(
                        pair_id=spec.pair_id,
                        experiment=str(first["experiment"]),
                        experiment_number=experiment_number,
                        plate=int(first["plate"]),
                        well_id=str(first["well_id"]),
                        well=str(first["well"]),
                        sirna_id=sirna_id,
                        sirna=str(first["sirna"]),
                        label=label,
                        site_paths=site_paths,  # type: ignore[arg-type]
                    )
                )
            if member_records[0].plate != member_records[1].plate:
                raise ValueError(
                    f"Frozen pair {spec.pair_id!r} is not same-plate in experiment "
                    f"{experiment_number}: plates {member_records[0].plate} and "
                    f"{member_records[1].plate}."
                )
            records.extend(member_records)
    well_ids = [record.well_id for record in records]
    if len(well_ids) != len(set(well_ids)):
        raise ValueError("A well is reused across frozen pairs.")
    return specs, records


def load_well_array(record: WellRecord, image_size: int) -> np.ndarray:
    sites: list[np.ndarray] = []
    for paths in record.site_paths:
        channels: list[np.ndarray] = []
        for path in paths:
            with Image.open(path) as image:
                resized = image.convert("L").resize(
                    (image_size, image_size), Image.Resampling.BOX
                )
                channels.append(np.asarray(resized, dtype=np.uint8))
        sites.append(np.stack(channels, axis=0))
    return np.stack(sites, axis=0)


def zero_pad(array: np.ndarray, padding: int) -> np.ndarray:
    if padding < 0:
        raise ValueError("padding must be nonnegative.")
    widths = [(0, 0)] * (array.ndim - 2) + [(padding, padding), (padding, padding)]
    return np.pad(array, widths, mode="constant", constant_values=0)


def integer_translate(array: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Translate on Z^2, represented on a sufficiently padded finite canvas."""
    height, width = array.shape[-2:]
    if abs(dy) >= height or abs(dx) >= width:
        raise ValueError("Requested translation is larger than the finite canvas.")
    output = np.zeros_like(array)
    source_y0, source_y1 = max(0, -dy), min(height, height - dy)
    source_x0, source_x1 = max(0, -dx), min(width, width - dx)
    target_y0, target_y1 = source_y0 + dy, source_y1 + dy
    target_x0, target_x1 = source_x0 + dx, source_x1 + dx
    output[..., target_y0:target_y1, target_x0:target_x1] = array[
        ..., source_y0:source_y1, source_x0:source_x1
    ]
    if np.count_nonzero(output) != np.count_nonzero(array):
        raise ValueError(
            "Translation cropped nonzero support. Increase the exact padding."
        )
    return output


def apply_exact_action(
    array: np.ndarray,
    *,
    quarter_turns: int,
    dy: int,
    dx: int,
) -> np.ndarray:
    rotated = np.rot90(array, k=int(quarter_turns) % 4, axes=(-2, -1)).copy()
    return integer_translate(rotated, int(dy), int(dx))


def support_crop(array: np.ndarray) -> np.ndarray:
    leading_axes = tuple(range(array.ndim - 2))
    support = np.any(array != 0, axis=leading_axes) if leading_axes else array != 0
    rows, columns = np.flatnonzero(np.any(support, axis=1)), np.flatnonzero(
        np.any(support, axis=0)
    )
    if len(rows) == 0 or len(columns) == 0:
        return np.zeros(array.shape[:-2] + (1, 1), dtype=array.dtype)
    return array[..., rows[0] : rows[-1] + 1, columns[0] : columns[-1] + 1].copy()


def canonical_translation_c4(array: np.ndarray) -> np.ndarray:
    """Maximal canonical code for finite-support arrays modulo Z^2 semidirect C4."""
    candidates = [
        support_crop(np.rot90(array, k=quarter_turns, axes=(-2, -1)))
        for quarter_turns in range(4)
    ]
    keys = [
        (
            int(candidate.shape[-2]),
            int(candidate.shape[-1]),
            candidate.tobytes(order="C"),
        )
        for candidate in candidates
    ]
    return candidates[min(range(4), key=keys.__getitem__)]


def _embed_top_left(array: np.ndarray, canvas_size: int) -> np.ndarray:
    height, width = array.shape[-2:]
    if height > canvas_size or width > canvas_size:
        raise ValueError(
            f"Canonical support {height}x{width} exceeds {canvas_size}x{canvas_size}."
        )
    output = np.zeros(array.shape[:-2] + (canvas_size, canvas_size), dtype=array.dtype)
    output[..., :height, :width] = array
    return output


def exact_invariant_features(
    arrays: Sequence[np.ndarray], canvas_size: int
) -> np.ndarray:
    """Canonical pixel code for the product action, one rigid motion per site."""
    canonical_wells: list[np.ndarray] = []
    for array in arrays:
        if array.ndim != 4 or array.shape[0] != 2:
            raise ValueError(
                "Each RxRx1 well must have shape (2 sites, channels, height, width)."
            )
        canonical_sites = [
            _embed_top_left(
                canonical_translation_c4(array[site]),
                canvas_size,
            )
            for site in range(2)
        ]
        canonical_wells.append(np.stack(canonical_sites, axis=0))
    return (
        np.stack([array.reshape(-1) for array in canonical_wells]).astype(np.float32)
        / 255.0
    )


def raw_coordinate_features(arrays: Sequence[np.ndarray]) -> np.ndarray:
    return np.stack([array.reshape(-1) for array in arrays]).astype(np.float32) / 255.0


def _aggregate_intensity(array: np.ndarray) -> np.ndarray:
    leading_axes = tuple(range(array.ndim - 2))
    return np.sum(array.astype(np.float64), axis=leading_axes)


def _moment_register_site(array: np.ndarray) -> np.ndarray:
    """Register one six-channel site by estimated intensity moments."""
    if array.ndim != 3:
        raise ValueError("A site must have shape (channels, height, width).")
    intensity = _aggregate_intensity(array)
    total = float(intensity.sum())
    if total <= 0:
        return array.copy()
    height, width = intensity.shape
    yy, xx = np.mgrid[:height, :width]
    cy = float(np.sum(yy * intensity) / total)
    cx = float(np.sum(xx * intensity) / total)
    target_y = (height - 1) / 2.0
    target_x = (width - 1) / 2.0
    shifted = ndimage.shift(
        array.astype(np.float64),
        shift=(0,) * (array.ndim - 2) + (target_y - cy, target_x - cx),
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )
    shifted_intensity = _aggregate_intensity(shifted)
    total_shifted = float(shifted_intensity.sum())
    centered_y = yy - target_y
    centered_x = xx - target_x
    covariance = np.array(
        [
            [
                np.sum(shifted_intensity * centered_x * centered_x),
                np.sum(shifted_intensity * centered_x * centered_y),
            ],
            [
                np.sum(shifted_intensity * centered_x * centered_y),
                np.sum(shifted_intensity * centered_y * centered_y),
            ],
        ]
    ) / max(total_shifted, 1e-12)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    direction = eigenvectors[:, int(np.argmax(eigenvalues))]
    angle_degrees = math.degrees(math.atan2(direction[1], direction[0]))
    registered = ndimage.rotate(
        shifted,
        angle=-angle_degrees,
        axes=(-2, -1),
        reshape=False,
        order=1,
        mode="constant",
        cval=0.0,
        prefilter=False,
    )
    candidates = [
        np.rot90(registered, k=0, axes=(-2, -1)),
        np.rot90(registered, k=2, axes=(-2, -1)),
    ]
    chosen = min(candidates, key=lambda candidate: candidate.tobytes(order="C"))
    return np.clip(np.rint(chosen), 0, 255).astype(np.uint8)


def moment_register(array: np.ndarray) -> np.ndarray:
    """Sitewise estimated registration comparator for the product action."""
    if array.ndim != 4 or array.shape[0] != 2:
        raise ValueError(
            "Each RxRx1 well must have shape (2 sites, channels, height, width)."
        )
    return np.stack(
        [_moment_register_site(array[site]) for site in range(2)],
        axis=0,
    )


def moment_registration_features(arrays: Sequence[np.ndarray]) -> np.ndarray:
    return raw_coordinate_features([moment_register(array) for array in arrays])


def planar_cubical_euler_characteristic(mask: np.ndarray) -> int:
    """Euler characteristic V-E+F of the ordinary planar pixel cubical complex."""
    cells = np.asarray(mask, dtype=bool)
    if cells.ndim != 2:
        raise ValueError("The cubical Euler characteristic requires a 2D mask.")
    height, width = cells.shape
    faces = int(cells.sum())
    horizontal = np.zeros((height + 1, width), dtype=bool)
    horizontal[:-1, :] |= cells
    horizontal[1:, :] |= cells
    vertical = np.zeros((height, width + 1), dtype=bool)
    vertical[:, :-1] |= cells
    vertical[:, 1:] |= cells
    vertices = np.zeros((height + 1, width + 1), dtype=bool)
    vertices[:-1, :-1] |= cells
    vertices[1:, :-1] |= cells
    vertices[:-1, 1:] |= cells
    vertices[1:, 1:] |= cells
    edges = int(horizontal.sum() + vertical.sum())
    return int(vertices.sum()) - edges + faces


def finite_directional_euler_transform(
    mask: np.ndarray,
    *,
    levels: int,
) -> np.ndarray:
    """Eight-direction finite Euler characteristic transform on a planar mask."""
    cells = np.asarray(mask, dtype=bool)
    if cells.ndim != 2:
        raise ValueError("The finite Euler transform requires a 2D mask.")
    if levels < 2:
        raise ValueError("At least two height levels are required.")
    height, width = cells.shape
    yy, xx = np.mgrid[:height, :width]
    xx = 2 * xx - (width - 1)
    yy = 2 * yy - (height - 1)
    directions = np.asarray(
        [
            [1, 0],
            [1, 1],
            [0, 1],
            [-1, 1],
            [-1, 0],
            [-1, -1],
            [0, -1],
            [1, -1],
        ],
        dtype=int,
    )
    output = np.empty((len(directions), levels), dtype=np.int16)
    for direction_index, (dx, dy) in enumerate(directions):
        heights = dx * xx + dy * yy
        cutoffs = np.linspace(float(heights.min()), float(heights.max()), levels)
        for level_index, cutoff in enumerate(cutoffs):
            output[direction_index, level_index] = (
                planar_cubical_euler_characteristic(cells & (heights <= cutoff))
            )
    return output


def _otsu_threshold(image: np.ndarray) -> int:
    values = np.asarray(image, dtype=np.uint8).ravel()
    histogram = np.bincount(values, minlength=256).astype(np.float64)
    total = float(histogram.sum())
    if total <= 0:
        return 0
    probability = histogram / total
    omega = np.cumsum(probability)
    cumulative_mean = np.cumsum(probability * np.arange(256))
    total_mean = cumulative_mean[-1]
    denominator = omega * (1.0 - omega)
    between = np.zeros(256, dtype=np.float64)
    valid = denominator > 0
    between[valid] = (
        total_mean * omega[valid] - cumulative_mean[valid]
    ) ** 2 / denominator[valid]
    return int(np.argmax(between))


def _clean_nuclear_mask(image: np.ndarray, min_component_size: int) -> np.ndarray:
    threshold = _otsu_threshold(image)
    mask = np.asarray(image > threshold, dtype=bool)
    labels, count = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
    if count == 0:
        return mask
    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_component_size
    keep[0] = False
    return keep[labels]


def topology_euler_features(
    arrays: Sequence[np.ndarray],
    *,
    levels: int,
    nuclear_channel: int,
    min_component_size: int,
) -> np.ndarray:
    """Sitewise finite directional ECT after exact product-action canonicalization."""
    rows: list[np.ndarray] = []
    for array in arrays:
        if array.ndim != 4 or array.shape[0] != 2:
            raise ValueError(
                "Each RxRx1 well must have shape (2 sites, channels, height, width)."
            )
        values: list[float] = []
        for site in range(2):
            canonical_site = canonical_translation_c4(array[site])
            mask = _clean_nuclear_mask(
                canonical_site[nuclear_channel],
                min_component_size,
            )
            values.extend(
                finite_directional_euler_transform(mask, levels=levels)
                .reshape(-1)
                .astype(np.float64)
            )
        rows.append(np.asarray(values, dtype=np.float64))
    return np.stack(rows)


def morphology_score(array: np.ndarray) -> float:
    """Coordinate-free intensity functional used only to generate nuisance."""
    values = np.asarray(array, dtype=np.float64) / 255.0
    return float(values.mean() + 0.25 * values.std(ddof=0))


def derive_hidden_nuisance(
    *,
    well_id: str,
    label: int,
    morphology: float,
    pooled_median: float,
    seed: int,
    max_shift: int,
) -> tuple[int, int, int]:
    """Frozen informative acquisition law, hidden from every analysis method."""
    digest = hashlib.blake2b(
        f"{seed}|{well_id}".encode("utf-8"), digest_size=24
    ).digest()
    words = [
        int.from_bytes(digest[offset : offset + 8], "little")
        for offset in (0, 8, 16)
    ]
    morphology_bin = int(math.floor(abs(morphology) * 1_000_003))
    above_median = int(morphology > pooled_median)
    # The base orientation has deliberately nonuniform two-point support. Thus
    # treatment's half-turn shift is not erased by adding a uniform C4 draw.
    quarter_turns = int(
        ((words[0] % 2) + 2 * int(label) + above_median) % 4
    )
    if max_shift == 0:
        return quarter_turns, 0, 0
    direction = 1 if int(label) == 1 else -1
    dy_magnitude = 1 + int((words[1] + morphology_bin) % max_shift)
    dx_magnitude = 1 + int(
        (words[2] + 7 * morphology_bin + above_median) % max_shift
    )
    dy = direction * dy_magnitude
    dx = direction * dx_magnitude
    return quarter_turns, dy, dx


def contaminate_arrays(
    clean_arrays: Mapping[str, np.ndarray],
    records: Sequence[WellRecord],
    *,
    seed: int,
    max_shift: int,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    scores = {
        (well_id, site): morphology_score(array[site])
        for well_id, array in clean_arrays.items()
        for site in range(2)
    }
    pooled_median = float(np.median(list(scores.values())))
    contaminated: dict[str, np.ndarray] = {}
    truth: list[dict[str, Any]] = []
    for record in records:
        transformed_sites: list[np.ndarray] = []
        for site in range(2):
            score = scores[(record.well_id, site)]
            quarter_turns, dy, dx = derive_hidden_nuisance(
                well_id=f"{record.well_id}|site={site + 1}",
                label=record.label,
                morphology=score,
                pooled_median=pooled_median,
                seed=seed,
                max_shift=max_shift,
            )
            transformed_sites.append(
                apply_exact_action(
                    clean_arrays[record.well_id][site],
                    quarter_turns=quarter_turns,
                    dy=dy,
                    dx=dx,
                )
            )
            truth.append(
                {
                    "nuisance_seed": int(seed),
                    "well_id": record.well_id,
                    "site": site + 1,
                    "pair_id": record.pair_id,
                    "experiment": record.experiment,
                    "label": record.label,
                    "morphology_score": score,
                    "pooled_morphology_median": pooled_median,
                    "quarter_turns": quarter_turns,
                    "dy": dy,
                    "dx": dx,
                    "used_by_analyzer": False,
                }
            )
        contaminated[record.well_id] = np.stack(transformed_sites, axis=0)
    return contaminated, truth


def build_acquisition_only_null(
    clean_arrays: Mapping[str, np.ndarray],
    records: Sequence[WellRecord],
) -> dict[str, np.ndarray]:
    """Duplicate a label-blind pair prototype so only acquisition differs."""
    output: dict[str, np.ndarray] = {}
    grouped: dict[tuple[str, str], list[WellRecord]] = {}
    for record in records:
        grouped.setdefault((record.pair_id, record.experiment), []).append(record)
    for key, group in grouped.items():
        if len(group) != 2 or {record.label for record in group} != {0, 1}:
            raise ValueError(f"Invalid paired records for acquisition null: {key}")
        left, right = sorted(group, key=lambda record: record.label)
        prototype = np.rint(
            (
                clean_arrays[left.well_id].astype(np.float64)
                + clean_arrays[right.well_id].astype(np.float64)
            )
            / 2.0
        ).astype(np.uint8)
        output[left.well_id] = prototype.copy()
        output[right.well_id] = prototype.copy()
    return output


def compute_method_features(
    arrays: Sequence[np.ndarray],
    config: ExperimentConfig,
) -> dict[str, np.ndarray]:
    canvas_size = config.image_size + 2 * config.padding
    return {
        "quotient_exact": exact_invariant_features(arrays, canvas_size),
        "raw_coordinates": raw_coordinate_features(arrays),
        "moment_registration": moment_registration_features(arrays),
        "euler_secondary": topology_euler_features(
            arrays,
            levels=config.ect_levels,
            nuclear_channel=config.nuclear_channel,
            min_component_size=config.ect_min_component_size,
        ),
    }


def kernel_from_features(features: np.ndarray) -> tuple[np.ndarray, float]:
    bandwidth = median_bandwidth(features)
    return rbf_kernel(features, bandwidth), bandwidth


def paired_cluster_bootstrap_from_kernel(
    kernel: np.ndarray,
    labels: np.ndarray,
    pair_ids: np.ndarray,
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    unique_pairs = np.unique(pair_ids)
    lookup = {pair_id: np.flatnonzero(pair_ids == pair_id) for pair_id in unique_pairs}
    statistics = np.empty(replicates, dtype=np.float64)
    for replicate in range(replicates):
        sampled = rng.choice(unique_pairs, size=len(unique_pairs), replace=True)
        indices = np.concatenate([lookup[pair_id] for pair_id in sampled])
        statistics[replicate] = mmd2_unbiased_from_kernel(
            kernel[np.ix_(indices, indices)], labels[indices]
        )
    lower, upper = np.quantile(statistics, [0.025, 0.975])
    return {
        "replicates": int(replicates),
        "seed": int(seed),
        "percentile_95_ci": [float(lower), float(upper)],
        "bootstrap_mean": float(statistics.mean()),
        "bootstrap_sd": float(statistics.std(ddof=1)),
    }


def analyse_pair(
    features: np.ndarray,
    records: Sequence[WellRecord],
    indices: np.ndarray,
    *,
    bootstrap_replicates: int = 0,
    bootstrap_seed: int = 0,
) -> dict[str, Any]:
    pair_features = features[indices]
    labels = np.asarray([records[index].label for index in indices], dtype=int)
    experiment_ids = np.asarray(
        [records[index].experiment_number for index in indices], dtype=int
    )
    kernel, bandwidth = kernel_from_features(pair_features)
    result = exact_paired_mmd_test(kernel, labels, experiment_ids)
    result["bandwidth"] = float(bandwidth)
    if bootstrap_replicates > 0:
        result["cluster_bootstrap"] = paired_cluster_bootstrap_from_kernel(
            kernel,
            labels,
            experiment_ids,
            replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        )
    return result


def _pair_indices(records: Sequence[WellRecord]) -> dict[str, np.ndarray]:
    pair_ids = sorted({record.pair_id for record in records})
    return {
        pair_id: np.asarray(
            [index for index, record in enumerate(records) if record.pair_id == pair_id],
            dtype=int,
        )
        for pair_id in pair_ids
    }


def _apply_holm_columns(
    rows: list[dict[str, Any]], specs: Sequence[PairSpec]
) -> None:
    roles = {spec.pair_id: spec.role for spec in specs}
    group_keys = sorted(
        {
            (row["analysis"], row["method"], row["nuisance_seed"])
            for row in rows
        }
    )
    for analysis, method, seed in group_keys:
        group = [
            row
            for row in rows
            if row["analysis"] == analysis
            and row["method"] == method
            and row["nuisance_seed"] == seed
        ]
        all_adjusted = holm_adjust(
            {str(row["pair_id"]): float(row["p_value"]) for row in group}
        )
        replication = {
            str(row["pair_id"]): float(row["p_value"])
            for row in group
            if roles[str(row["pair_id"])] != "primary"
        }
        replication_adjusted = holm_adjust(replication) if replication else {}
        for row in group:
            pair_id = str(row["pair_id"])
            row["role"] = roles[pair_id]
            row["holm_all_pairs_p"] = all_adjusted[pair_id]
            row["holm_replication_p"] = (
                replication_adjusted[pair_id]
                if pair_id in replication_adjusted
                else float(row["p_value"])
            )


def _feature_invariance_error(
    reference: Mapping[str, np.ndarray],
    candidate: Mapping[str, np.ndarray],
) -> dict[str, float]:
    output: dict[str, float] = {}
    for method in reference:
        if reference[method].shape != candidate[method].shape:
            output[method] = float("inf")
        else:
            output[method] = float(
                np.max(np.abs(reference[method] - candidate[method]))
            )
    return output


def _crop_support_margins(array: np.ndarray, pixels: int) -> np.ndarray:
    if pixels <= 0:
        return array.copy()
    cropped = array.copy()
    leading_axes = tuple(range(array.ndim - 2))
    support = np.any(array != 0, axis=leading_axes)
    rows = np.flatnonzero(np.any(support, axis=1))
    columns = np.flatnonzero(np.any(support, axis=0))
    if len(rows) <= 2 * pixels or len(columns) <= 2 * pixels:
        return cropped
    y0, y1 = int(rows[0]), int(rows[-1]) + 1
    x0, x1 = int(columns[0]), int(columns[-1]) + 1
    cropped[..., y0 : y0 + pixels, x0:x1] = 0
    cropped[..., y1 - pixels : y1, x0:x1] = 0
    cropped[..., y0:y1, x0 : x0 + pixels] = 0
    cropped[..., y0:y1, x1 - pixels : x1] = 0
    return cropped


def _center_support_on_canvas(array: np.ndarray) -> np.ndarray:
    """Translate a finite-support site to the canvas center without interpolation."""
    cropped = support_crop(array)
    height, width = array.shape[-2:]
    crop_height, crop_width = cropped.shape[-2:]
    if crop_height > height or crop_width > width:
        raise ValueError("Support crop cannot exceed its source canvas.")
    output = np.zeros_like(array)
    y0 = (height - crop_height) // 2
    x0 = (width - crop_width) // 2
    output[..., y0 : y0 + crop_height, x0 : x0 + crop_width] = cropped
    return output


def _center_well_sites(array: np.ndarray) -> np.ndarray:
    return np.stack(
        [_center_support_on_canvas(array[site]) for site in range(2)],
        axis=0,
    )


def approximate_perturbation(
    arrays: Sequence[np.ndarray],
    condition: str,
    *,
    seed: int,
    crop_pixels: int,
    noise_sd: float,
) -> list[np.ndarray]:
    if condition.startswith("rotation_"):
        angle = float(condition.split("_", 1)[1])
        output: list[np.ndarray] = []
        for array in arrays:
            transformed_sites = []
            for site in range(2):
                site_angle = angle if site == 0 else -angle
                transformed_sites.append(
                    np.clip(
                        np.rint(
                            ndimage.rotate(
                                array[site].astype(np.float64),
                                angle=site_angle,
                                axes=(-2, -1),
                                reshape=False,
                                order=1,
                                mode="constant",
                                cval=0.0,
                                prefilter=False,
                            )
                        ),
                        0,
                        255,
                    ).astype(np.uint8)
                )
            output.append(np.stack(transformed_sites, axis=0))
        return output
    if condition == "crop":
        return [
            np.stack(
                [
                    _crop_support_margins(array[site], crop_pixels)
                    for site in range(2)
                ],
                axis=0,
            )
            for array in arrays
        ]
    if condition == "noise":
        rng = np.random.default_rng(seed)
        output = []
        for array in arrays:
            perturbed_sites = []
            for site in range(2):
                support_2d = np.any(array[site] != 0, axis=0)
                support = np.broadcast_to(support_2d, array[site].shape)
                noise = rng.normal(0.0, noise_sd, size=array[site].shape)
                perturbed = array[site].astype(np.float64)
                perturbed[support] += noise[support]
                perturbed[~support] = 0.0
                perturbed_sites.append(
                    np.clip(np.rint(perturbed), 0, 255).astype(np.uint8)
                )
            output.append(np.stack(perturbed_sites, axis=0))
        return output
    raise ValueError(f"Unknown approximate condition {condition!r}.")


def approximate_action_stress(
    baseline_arrays: Sequence[np.ndarray],
    records: Sequence[WellRecord],
    specs: Sequence[PairSpec],
    config: ExperimentConfig,
) -> list[dict[str, Any]]:
    primary_pair = next(spec.pair_id for spec in specs if spec.role == "primary")
    indices = _pair_indices(records)[primary_pair]
    primary_arrays = [
        _center_well_sites(baseline_arrays[index])
        for index in indices
    ]
    baseline_features = compute_method_features(primary_arrays, config)
    labels = np.asarray([records[index].label for index in indices], dtype=int)
    experiment_ids = np.asarray(
        [records[index].experiment_number for index in indices], dtype=int
    )
    baseline_tests = {}
    for method, features in baseline_features.items():
        kernel, _ = kernel_from_features(features)
        baseline_tests[method] = exact_paired_mmd_test(kernel, labels, experiment_ids)

    conditions = [f"rotation_{angle:g}" for angle in config.approximate_angles]
    conditions.extend(["crop", "noise"])
    rows: list[dict[str, Any]] = []
    for condition_index, condition in enumerate(conditions):
        perturbed = approximate_perturbation(
            primary_arrays,
            condition,
            seed=71_000 + condition_index,
            crop_pixels=config.approximate_crop_pixels,
            noise_sd=config.approximate_noise_sd,
        )
        features_by_method = compute_method_features(perturbed, config)
        for method, features in features_by_method.items():
            baseline = baseline_features[method]
            absolute = float(np.linalg.norm(features - baseline))
            denominator = max(float(np.linalg.norm(baseline)), 1e-12)
            kernel, _ = kernel_from_features(features)
            test = exact_paired_mmd_test(kernel, labels, experiment_ids)
            rows.append(
                {
                    "pair_id": primary_pair,
                    "condition": condition,
                    "method": method,
                    "relative_feature_error": absolute / denominator,
                    "baseline_statistic": baseline_tests[method]["statistic"],
                    "perturbed_statistic": test["statistic"],
                    "absolute_statistic_change": abs(
                        test["statistic"] - baseline_tests[method]["statistic"]
                    ),
                    "baseline_p_value": baseline_tests[method]["p_value"],
                    "perturbed_p_value": test["p_value"],
                    "absolute_p_value_change": abs(
                        test["p_value"] - baseline_tests[method]["p_value"]
                    ),
                    "interpretation": "approximate-action robustness; not exact invariance",
                }
            )
    return rows


def _plot_results(rows: pd.DataFrame, output_directory: Path) -> list[str]:
    import os

    os.environ.setdefault("MPLCONFIGDIR", str(output_directory / ".mplconfig"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_directory.mkdir(parents=True, exist_ok=True)
    methods = [
        "quotient_exact",
        "raw_coordinates",
        "moment_registration",
        "euler_secondary",
    ]
    labels = {
        "quotient_exact": "Exact quotient",
        "raw_coordinates": "Raw pixels",
        "moment_registration": "Moment alignment",
        "euler_secondary": "Euler secondary",
    }
    analysis = rows[rows["analysis"] == "observed"].copy()
    summary = (
        analysis.groupby("method", sort=False)["statistic"]
        .agg(["mean", "std"])
        .reindex(methods)
    )
    figure, axis = plt.subplots(figsize=(7.2, 4.2))
    positions = np.arange(len(methods))
    axis.bar(
        positions,
        summary["mean"].to_numpy(),
        yerr=summary["std"].fillna(0).to_numpy(),
        capsize=4,
        color=["#1f77b4", "#d62728", "#ff7f0e", "#2ca02c"],
    )
    axis.set_xticks(positions, [labels[method] for method in methods], rotation=15)
    axis.set_ylabel("Unbiased MMD$^2$")
    axis.set_title("RxRx1 quotient discrepancy across acquisition-transform seeds")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    png = output_directory / "rxrx1_mmd_by_method.png"
    pdf = output_directory / "rxrx1_mmd_by_method.pdf"
    figure.savefig(png, dpi=180)
    figure.savefig(pdf)
    plt.close(figure)
    return [str(png), str(pdf)]


def run_rxrx1_experiment(
    *,
    selection_manifest_path: str | Path,
    metadata_path: str | Path,
    data_root: str | Path,
    output_directory: str | Path,
    figure_directory: str | Path,
    progress_path: str | Path,
    config: ExperimentConfig,
) -> dict[str, Any]:
    config.validate()
    manifest_path = Path(selection_manifest_path)
    manifest = json.loads(manifest_path.read_text())
    sealed_seeds = tuple(
        int(value)
        for value in manifest.get("statistical_plan", {}).get(
            "nuisance_robustness_seeds",
            (),
        )
    )
    if sealed_seeds and tuple(config.nuisance_seeds) != sealed_seeds:
        raise ValueError(
            "ExperimentConfig.nuisance_seeds must equal the frozen manifest's "
            f"nuisance_robustness_seeds: {sealed_seeds}."
        )
    specs, records = resolve_well_records(
        manifest,
        metadata_path,
        data_root,
        require_validation_experiments=8,
    )
    pair_indices = _pair_indices(records)
    total_steps = (
        len(records)
        + 1
        + len(config.nuisance_seeds) * 3
        + 2
    )
    tracker = ProgressTracker("rxrx1-experiment", total_steps, progress_path)
    completed = 0
    failures: list[dict[str, str]] = []
    output_root = Path(output_directory)
    output_root.mkdir(parents=True, exist_ok=True)

    try:
        clean_arrays: dict[str, np.ndarray] = {}
        for record in records:
            try:
                clean_arrays[record.well_id] = zero_pad(
                    load_well_array(record, config.image_size), config.padding
                )
            except Exception as error:
                failures.append({"well_id": record.well_id, "error": repr(error)})
                tracker.state.failures = len(failures)
                raise
            completed += 1
            tracker.update(completed, message=f"loaded {record.well_id}")

        ordered_clean = [clean_arrays[record.well_id] for record in records]
        clean_features = compute_method_features(ordered_clean, config)
        exact_methods = ("quotient_exact", "euler_secondary")
        clean_exact_tests = {
            (method, spec.pair_id): analyse_pair(
                clean_features[method],
                records,
                pair_indices[spec.pair_id],
            )
            for method in exact_methods
            for spec in specs
        }
        completed += 1
        tracker.update(completed, message="computed label-blind clean references")

        result_rows: list[dict[str, Any]] = []
        nuisance_truth_rows: list[dict[str, Any]] = []
        equivalence_rows: list[dict[str, Any]] = []
        acquisition_null_rows: list[dict[str, Any]] = []
        null_clean = build_acquisition_only_null(clean_arrays, records)

        for seed_position, nuisance_seed in enumerate(config.nuisance_seeds):
            contaminated, truth = contaminate_arrays(
                clean_arrays,
                records,
                seed=nuisance_seed,
                max_shift=config.max_integer_shift,
            )
            nuisance_truth_rows.extend(truth)
            ordered = [contaminated[record.well_id] for record in records]
            features_by_method = compute_method_features(ordered, config)
            errors = _feature_invariance_error(clean_features, features_by_method)
            quotient_error = errors["quotient_exact"]
            euler_error = errors["euler_secondary"]
            gate_pass = (
                quotient_error <= config.invariance_tolerance
                and euler_error <= config.invariance_tolerance
            )
            if not gate_pass:
                raise RuntimeError(
                    f"Exact invariance gate failed for nuisance seed {nuisance_seed}: "
                    f"quotient={quotient_error}, Euler={euler_error}."
                )

            maximum_statistic_difference = {
                method: 0.0 for method in exact_methods
            }
            maximum_p_value_difference = {
                method: 0.0 for method in exact_methods
            }
            for method, features in features_by_method.items():
                for spec in specs:
                    bootstrap = (
                        config.bootstrap_replicates
                        if (
                            seed_position == 0
                            and spec.role == "primary"
                            and method
                            in (
                                "quotient_exact",
                                "raw_coordinates",
                                "moment_registration",
                                "euler_secondary",
                            )
                        )
                        else 0
                    )
                    test = analyse_pair(
                        features,
                        records,
                        pair_indices[spec.pair_id],
                        bootstrap_replicates=bootstrap,
                        bootstrap_seed=(
                            config.bootstrap_seed
                            + 1_003 * seed_position
                            + 17 * list(pair_indices).index(spec.pair_id)
                        ),
                    )
                    row: dict[str, Any] = {
                        "analysis": "observed",
                        "method": method,
                        "nuisance_seed": nuisance_seed,
                        "pair_id": spec.pair_id,
                        "statistic": test["statistic"],
                        "p_value": test["p_value"],
                        "permutations": test["permutations"],
                        "exceedances": test["exceedances"],
                        "bandwidth": test["bandwidth"],
                    }
                    if "cluster_bootstrap" in test:
                        bootstrap_result = test["cluster_bootstrap"]
                        row.update(
                            bootstrap_ci_lower=bootstrap_result[
                                "percentile_95_ci"
                            ][0],
                            bootstrap_ci_upper=bootstrap_result[
                                "percentile_95_ci"
                            ][1],
                            bootstrap_replicates=bootstrap_result["replicates"],
                        )
                    if method in exact_methods:
                        clean_test = clean_exact_tests[(method, spec.pair_id)]
                        maximum_statistic_difference[method] = max(
                            maximum_statistic_difference[method],
                            abs(
                                float(test["statistic"])
                                - float(clean_test["statistic"])
                            ),
                        )
                        maximum_p_value_difference[method] = max(
                            maximum_p_value_difference[method],
                            abs(
                                float(test["p_value"])
                                - float(clean_test["p_value"])
                            ),
                        )
                    result_rows.append(row)
            equivalence_rows.append(
                {
                    "nuisance_seed": nuisance_seed,
                    **{
                        f"{method}_max_abs_feature_error": value
                        for method, value in errors.items()
                    },
                    **{
                        f"{method}_max_abs_mmd2_difference": value
                        for method, value in maximum_statistic_difference.items()
                    },
                    **{
                        f"{method}_max_abs_p_value_difference": value
                        for method, value in maximum_p_value_difference.items()
                    },
                    "exact_invariance_gate_pass": gate_pass,
                    "tolerance": config.invariance_tolerance,
                }
            )
            completed += 1
            tracker.update(
                completed,
                message=f"seed {nuisance_seed}: observed analyses and exact gate",
            )

            null_contaminated, _ = contaminate_arrays(
                null_clean,
                records,
                seed=nuisance_seed,
                max_shift=config.max_integer_shift,
            )
            null_features = compute_method_features(
                [null_contaminated[record.well_id] for record in records], config
            )
            for method, features in null_features.items():
                for spec in specs:
                    test = analyse_pair(
                        features, records, pair_indices[spec.pair_id]
                    )
                    acquisition_null_rows.append(
                        {
                            "analysis": "acquisition_only_sharp_null",
                            "method": method,
                            "nuisance_seed": nuisance_seed,
                            "pair_id": spec.pair_id,
                            "statistic": test["statistic"],
                            "p_value": test["p_value"],
                            "rejected_at_0_05": bool(test["p_value"] <= 0.05),
                            "permutations": test["permutations"],
                        }
                    )
            completed += 1
            tracker.update(
                completed,
                message=f"seed {nuisance_seed}: acquisition-only negative control",
            )

            completed += 1
            tracker.update(
                completed,
                message=(
                    f"seed {nuisance_seed}: nuisance truth logged separately "
                    "and excluded from estimator inputs"
                ),
            )

        _apply_holm_columns(result_rows, specs)
        _apply_holm_columns(acquisition_null_rows, specs)
        result_frame = pd.DataFrame(result_rows)
        null_frame = pd.DataFrame(acquisition_null_rows)
        equivalence_frame = pd.DataFrame(equivalence_rows)
        truth_frame = pd.DataFrame(nuisance_truth_rows)

        baseline_contaminated, _ = contaminate_arrays(
            clean_arrays,
            records,
            seed=config.nuisance_seeds[0],
            max_shift=config.max_integer_shift,
        )
        stress_rows = approximate_action_stress(
            [baseline_contaminated[record.well_id] for record in records],
            records,
            specs,
            config,
        )
        stress_frame = pd.DataFrame(stress_rows)
        completed += 1
        tracker.update(completed, message="approximate-action robustness audit")

        output_files = {
            "pair_seed_results": output_root / "pair_seed_results.csv",
            "acquisition_null_results": output_root / "acquisition_null_results.csv",
            "clean_contaminated_equivalence": (
                output_root / "clean_contaminated_equivalence.csv"
            ),
            "approximate_action_stress": (
                output_root / "approximate_action_stress.csv"
            ),
            "hidden_nuisance_truth": (
                output_root / "hidden_nuisance_truth_NOT_ANALYSIS.csv"
            ),
            "acquisition_null_false_positive_summary": (
                output_root / "acquisition_null_false_positive_summary.csv"
            ),
        }
        result_frame.to_csv(output_files["pair_seed_results"], index=False)
        null_frame.to_csv(output_files["acquisition_null_results"], index=False)
        equivalence_frame.to_csv(
            output_files["clean_contaminated_equivalence"], index=False
        )
        stress_frame.to_csv(
            output_files["approximate_action_stress"], index=False
        )
        truth_frame.to_csv(
            output_files["hidden_nuisance_truth"], index=False
        )

        false_positive_summary = (
            null_frame.groupby("method")["rejected_at_0_05"]
            .agg(["sum", "count", "mean"])
            .reset_index()
            .rename(
                columns={
                    "sum": "false_positives",
                    "count": "tests",
                    "mean": "false_positive_fraction",
                }
            )
        )
        intervals = [
            clopper_pearson(int(row.false_positives), int(row.tests))
            for row in false_positive_summary.itertuples(index=False)
        ]
        false_positive_summary["clopper_pearson_95_lower"] = [
            interval[0] for interval in intervals
        ]
        false_positive_summary["clopper_pearson_95_upper"] = [
            interval[1] for interval in intervals
        ]
        false_positive_summary.to_csv(
            output_files["acquisition_null_false_positive_summary"], index=False
        )
        figure_paths = _plot_results(result_frame, Path(figure_directory))
        completed += 1
        tracker.update(completed, message="wrote tables, figures, and audit metadata")

        experiment_counts = {
            spec.pair_id: int(
                len(
                    {
                        records[index].experiment_number
                        for index in pair_indices[spec.pair_id]
                    }
                )
            )
            for spec in specs
        }
        summary: dict[str, Any] = {
            "status": "completed",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "scientific_unit": "RxRx1 well",
            "sites_per_well": 2,
            "channels_per_site": 6,
            "exact_group": (
                "product action (Z^2 semidirect C4)^2 on two-site "
                "finite-support arrays"
            ),
            "exact_invariant": (
                "sitewise support crop followed by lexicographic C4 "
                "canonicalization, concatenated at the well level"
            ),
            "nuisance_parameters_supplied_to_estimators": False,
            "pair_specs": [asdict(spec) for spec in specs],
            "experiments_per_pair": experiment_counts,
            "exact_swap_counts": {
                pair_id: int(2**count) for pair_id, count in experiment_counts.items()
            },
            "config": asdict(config),
            "manifest": {
                "path": str(manifest_path.resolve()),
                "sha256": sha256_file(manifest_path),
            },
            "metadata": {
                "path": str(Path(metadata_path).resolve()),
                "sha256": sha256_file(metadata_path),
            },
            "software": {
                "python": sys.version,
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "source_sha256": {
                    "experiment.py": sha256_file(Path(__file__)),
                    "invariants.py": sha256_file(
                        Path(__file__).with_name("invariants.py")
                    ),
                    "statistics.py": sha256_file(
                        Path(__file__).with_name("statistics.py")
                    ),
                },
            },
            "exact_invariance_gate": {
                "all_passed": bool(
                    equivalence_frame["exact_invariance_gate_pass"].all()
                ),
                "tolerance": config.invariance_tolerance,
                "maximum_quotient_feature_error": float(
                    equivalence_frame[
                        "quotient_exact_max_abs_feature_error"
                    ].max()
                ),
                "maximum_euler_feature_error": float(
                    equivalence_frame[
                        "euler_secondary_max_abs_feature_error"
                    ].max()
                ),
                "maximum_quotient_mmd2_difference": float(
                    equivalence_frame[
                        "quotient_exact_max_abs_mmd2_difference"
                    ].max()
                ),
                "maximum_quotient_p_value_difference": float(
                    equivalence_frame[
                        "quotient_exact_max_abs_p_value_difference"
                    ].max()
                ),
                "maximum_euler_mmd2_difference": float(
                    equivalence_frame[
                        "euler_secondary_max_abs_mmd2_difference"
                    ].max()
                ),
                "maximum_euler_p_value_difference": float(
                    equivalence_frame[
                        "euler_secondary_max_abs_p_value_difference"
                    ].max()
                ),
            },
            "outputs": {
                "files": {
                    key: {
                        "path": str(path.resolve()),
                        "sha256": sha256_file(path),
                    }
                    for key, path in output_files.items()
                },
                "figures": figure_paths,
                "figure_sha256": {
                    str(Path(path).resolve()): sha256_file(path)
                    for path in figure_paths
                },
            },
            "failures": failures,
        }
        write_json(output_root / "experiment_summary.json", summary)
        tracker.complete("RxRx1 experiment completed")
        return summary
    except Exception as error:
        tracker.fail(f"{type(error).__name__}: {error}")
        raise
