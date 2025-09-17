"""Helpers for surfacing semantic cousin photos while avoiding duplicates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

try:  # Reuse the Photo definition if taste.py is available.
    from .taste import Photo
except Exception:  # pragma: no cover - defensive fallback for standalone use
    @dataclass(frozen=True)
    class Photo:  # type: ignore[redefinition]
        id: str
        vector: np.ndarray
        tags: Sequence[str]


def jaccard_overlap(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    inter = len(sa & sb)
    union = len(sa | sb)
    if union == 0:
        return 0.0
    return inter / union


def _cosine(a: np.ndarray, b: np.ndarray, eps: float = 1e-9) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + eps
    return float(np.dot(a, b) / denom)


def find_variants(
    base: Photo,
    pool: Iterable[Photo],
    min_tag_overlap: float = 0.8,
    max_cosine: float = 0.9,
    max_variants: int = 2,
    exclude_ids: Optional[Iterable[str]] = None,
    emphasise_contrast_axes: Optional[List[str]] = None,
) -> List[Tuple[str, float, float]]:
    """Return semantic cousins for ``base`` with high tag overlap."""

    exclude = set(exclude_ids or [])
    variants: List[Tuple[str, float, float, float]] = []  # (id, overlap, cosine, boost)

    for candidate in pool:
        if candidate.id == base.id or candidate.id in exclude:
            continue
        overlap = jaccard_overlap(base.tags, candidate.tags)
        if overlap < min_tag_overlap:
            continue
        cos = _cosine(base.vector, candidate.vector)
        if cos > max_cosine:
            continue
        boost = _contrast_boost(base, candidate, emphasise_contrast_axes)
        variants.append((candidate.id, overlap, cos, boost))

    variants.sort(key=lambda item: (item[1] + item[3], -item[2]), reverse=True)
    trimmed = [(vid, overlap, cos) for vid, overlap, cos, _ in variants[:max_variants]]
    return trimmed


def _contrast_boost(
    base: Photo,
    candidate: Photo,
    emphasise_contrast_axes: Optional[List[str]] = None,
) -> float:
    """Simple heuristic that rewards differences on specified axes."""

    if not emphasise_contrast_axes:
        return 0.0

    boost = 0.0
    base_tags = set(base.tags)
    cand_tags = set(candidate.tags)
    for axis in emphasise_contrast_axes:
        # axes encoded as "mood:serene|energetic" etc.
        if ":" not in axis or "|" not in axis:
            continue
        prefix, values = axis.split(":", 1)
        left, right = values.split("|", 1)
        left_tag = f"{prefix}:{left}".lower()
        right_tag = f"{prefix}:{right}".lower()
        if (left_tag in base_tags and right_tag in cand_tags) or (
            right_tag in base_tags and left_tag in cand_tags
        ):
            boost += 0.02
    return boost
