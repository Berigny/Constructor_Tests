"""Utilities for deriving a taste vector from non-verbal photo choices.

The module keeps the maths lightweight so it can run inside a Streamlit
session without extra dependencies.  NumPy is used purely for vector
operations.  Functions here do not assume any specific embedding model –
you simply pass in the photo vectors you already store on disk.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


@dataclass(frozen=True)
class Photo:
    """Container for a photo shown to the user."""

    id: str
    vector: np.ndarray
    tags: Sequence[str]


@dataclass
class ChoiceEvent:
    """User interaction captured during the swipe flow."""

    photo_id: str
    kind: str
    recency_index: int


CHOICE_WEIGHTS: Dict[str, float] = {
    "super_like": 1.5,
    "like": 1.0,
    "dislike": -0.5,
}


def _safe_norm(x: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    n = float(np.linalg.norm(x))
    return x if n < eps else x / n


def _cosine(a: np.ndarray, b: np.ndarray, eps: float = 1e-9) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + eps
    return float(np.dot(a, b) / denom)


def _prepare_events(events: Iterable[ChoiceEvent]) -> List[ChoiceEvent]:
    """Return events sorted by the provided ``recency_index``.

    When events come in chronological order the ``recency_index`` may be
    missing.  This helper assigns a monotonic index before sorting.
    """

    materialised = list(events)
    prepared: List[ChoiceEvent] = []
    for idx, ev in enumerate(materialised):
        rec_i = getattr(ev, "recency_index", None)
        if rec_i is None:
            rec_i = idx
        prepared.append(ChoiceEvent(ev.photo_id, ev.kind, int(rec_i)))
    prepared.sort(key=lambda e: e.recency_index)
    return prepared


def build_taste_vector(
    photos_by_id: Dict[str, Photo],
    events: Iterable[ChoiceEvent],
    dim: Optional[int] = None,
    recency_tau: float = 8.0,
) -> np.ndarray:
    """Aggregate user choices into a single unit taste vector.

    ``recency_tau`` controls an exponential decay that favours recent
    interactions.  The returned vector is normalised (or zeros if there is
    no usable signal).
    """

    prepared = _prepare_events(events)
    if not prepared:
        if dim is None:
            raise ValueError("No events supplied and embedding dimension unknown.")
        return np.zeros(dim, dtype=np.float32)

    if dim is None:
        for ev in prepared:
            ph = photos_by_id.get(ev.photo_id)
            if ph is not None:
                dim = int(ph.vector.shape[0])
                break
        if dim is None:
            raise ValueError("Could not infer embedding dimension from events.")
    assert dim is not None

    latest = prepared[-1].recency_index
    acc = np.zeros(dim, dtype=np.float32)

    for ev in prepared:
        photo = photos_by_id.get(ev.photo_id)
        if photo is None:
            continue
        weight = CHOICE_WEIGHTS.get(ev.kind, 0.0)
        if weight == 0.0:
            continue
        decay = np.exp(-(latest - ev.recency_index) / max(1e-6, recency_tau))
        acc += (weight * decay) * photo.vector.astype(np.float32)

    return _safe_norm(acc.astype(np.float32))


def aggregate_tag_preferences(
    photos_by_id: Dict[str, Photo],
    events: Iterable[ChoiceEvent],
    recency_tau: float = 8.0,
) -> Dict[str, float]:
    """Return weighted tag counts derived from the same events.

    The output is a dictionary mapping tag -> accumulated score.  It can be
    used to produce human-readable explanations or to build TF–IDF fallbacks
    when embedding vectors are missing.
    """

    prepared = _prepare_events(events)
    if not prepared:
        return {}

    latest = prepared[-1].recency_index
    tag_weights: Dict[str, float] = {}

    for ev in prepared:
        photo = photos_by_id.get(ev.photo_id)
        if photo is None:
            continue
        base_w = CHOICE_WEIGHTS.get(ev.kind, 0.0)
        if base_w == 0.0:
            continue
        decay = np.exp(-(latest - ev.recency_index) / max(1e-6, recency_tau))
        weight = base_w * decay
        for tag in photo.tags:
            tag_weights[tag] = tag_weights.get(tag, 0.0) + weight

    return tag_weights


def top_tags_from_events(
    photos_by_id: Dict[str, Photo],
    events: Iterable[ChoiceEvent],
    top_k: int = 6,
    recency_tau: float = 8.0,
) -> List[str]:
    """Return the ``top_k`` tags ranked by their accumulated weights."""

    weights = aggregate_tag_preferences(photos_by_id, events, recency_tau=recency_tau)
    if not weights:
        return []
    sorted_tags = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    return [tag for tag, _ in sorted_tags[:top_k]]


def select_next_photo_greedy_mmr(
    candidate_ids: Sequence[str],
    photos_by_id: Dict[str, Photo],
    taste_vec: np.ndarray,
    shown_ids: Sequence[str],
    lambda_diversity: float = 0.25,
    recent_window: int = 5,
    sample_k: Optional[int] = None,
) -> Optional[str]:
    """Select the next photo balancing exploration and diversity.

    ``sample_k`` can be used when the candidate pool is large; a random
    subset of that size is scored instead of the full list.
    """

    if not candidate_ids:
        return None

    candidate_ids = list(candidate_ids)
    if sample_k is not None and len(candidate_ids) > sample_k:
        rng = np.random.default_rng()
        candidate_ids = list(rng.choice(candidate_ids, size=sample_k, replace=False))

    shown_ids = list(shown_ids)
    recent_ids = shown_ids[-recent_window:] if recent_window > 0 else []
    recent_vecs = [photos_by_id[sid].vector for sid in recent_ids if sid in photos_by_id]

    best_id: Optional[str] = None
    best_score = -1e9

    for pid in candidate_ids:
        photo = photos_by_id.get(pid)
        if photo is None:
            continue

        info = 1.0 - abs(_cosine(taste_vec, photo.vector))
        if recent_vecs:
            sims = [_cosine(photo.vector, vec) for vec in recent_vecs]
            diversity_penalty = lambda_diversity * max(sims)
        else:
            diversity_penalty = 0.0

        score = info - diversity_penalty
        if score > best_score:
            best_score = score
            best_id = pid

    return best_id


def rank_by_cosine_to_taste(
    candidate_ids: Sequence[str],
    photos_by_id: Dict[str, Photo],
    taste_vec: np.ndarray,
    top_k: int = 12,
) -> List[Tuple[str, float]]:
    """Return ``top_k`` photos sorted by cosine similarity to the taste vector."""

    scored: List[Tuple[str, float]] = []
    for pid in candidate_ids:
        photo = photos_by_id.get(pid)
        if photo is None:
            continue
        scored.append((pid, _cosine(taste_vec, photo.vector)))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]


def load_photos_jsonl(path: str) -> Dict[str, Photo]:
    """Utility loader for the provided ``photos.jsonl`` dataset."""

    photos: Dict[str, Photo] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            vector = np.array(record.get("vector", []), dtype=np.float32)
            tags = record.get("tags") or []
            photos[record["id"]] = Photo(id=record["id"], vector=vector, tags=tuple(tags))
    return photos


# Local import placed at end to avoid an optional dependency at module import.
import json  # noqa: E402  (import after definitions for optional dependency)
