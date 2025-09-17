"""Ranking helpers that combine stored vectors with light-weight fallbacks."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


def _safe_norm(x: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    n = float(np.linalg.norm(x))
    return x if n < eps else x / n


def _cosine(a: np.ndarray, b: np.ndarray, eps: float = 1e-9) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + eps
    return float(np.dot(a, b) / denom)


@dataclass
class Gift:
    sku: str
    title: str
    price: float
    tags: Sequence[str]
    meta: Dict[str, Any] = field(default_factory=dict)
    short_desc: str = ""
    vector: Optional[np.ndarray] = None

    def combined_text(self) -> str:
        parts: List[str] = [self.title]
        if self.tags:
            parts.append(" ".join(self.tags))
        if self.short_desc:
            parts.append(self.short_desc)
        age = self.meta.get("age_fit")
        if isinstance(age, (list, tuple)):
            parts.append(" ".join(age))
        category = self.meta.get("category")
        if isinstance(category, (list, tuple)):
            parts.append(" ".join(category))
        return " ".join(str(p) for p in parts if p)


def load_gifts_jsonl(path: str) -> List[Gift]:
    gifts: List[Gift] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            vector = record.get("vector")
            arr = None
            if vector is not None:
                arr = np.array(vector, dtype=np.float32)
            gifts.append(
                Gift(
                    sku=record["sku"],
                    title=record.get("title", ""),
                    price=float(record.get("price", 0.0)),
                    tags=tuple(record.get("tags", [])),
                    meta=record.get("meta", {}),
                    short_desc=record.get("short_desc", ""),
                    vector=arr,
                )
            )
    return gifts


def rank_gifts_by_taste(
    gifts: Sequence[Gift],
    taste_vec: Optional[np.ndarray],
    top_k: int = 12,
    taste_top_tags: Optional[Sequence[str]] = None,
) -> List[Tuple[Gift, float]]:
    """Rank gifts by cosine similarity or TF–IDF fallback."""

    if not gifts:
        return []

    usable_vectors = [g.vector for g in gifts if g.vector is not None]
    same_dimension = False
    if usable_vectors and taste_vec is not None:
        dims = {vec.shape[0] for vec in usable_vectors}
        same_dimension = len(dims) == 1 and taste_vec.shape[0] in dims

    if taste_vec is not None and same_dimension and len(usable_vectors) == len(gifts):
        taste_norm = _safe_norm(taste_vec.astype(np.float32))
        results: List[Tuple[Gift, float]] = []
        for gift in gifts:
            assert gift.vector is not None
            score = _cosine(taste_norm, gift.vector.astype(np.float32))
            results.append((gift, score))
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

    # Fall back to TF–IDF using taste tags as a pseudo-document.
    taste_doc = " ".join(taste_top_tags or [])
    docs = [gift.combined_text() for gift in gifts]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(docs + [taste_doc])
    dense = matrix.toarray()
    gift_matrix = dense[:-1]
    taste_repr = dense[-1]
    taste_repr = _safe_norm(taste_repr)
    gift_matrix = np.array([_safe_norm(row) for row in gift_matrix])

    scores = gift_matrix.dot(taste_repr)
    ranked = list(zip(gifts, scores.tolist()))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


def filter_budget_and_age(
    gifts_with_scores: Sequence[Tuple[Gift, float]],
    budget: Optional[Tuple[float, float]] = None,
    age_prior: Optional[Sequence[str]] = None,
) -> List[Tuple[Gift, float]]:
    """Guard to drop gifts violating budget/age constraints."""

    age_set = {a.lower() for a in age_prior or []}
    min_budget, max_budget = (budget or (None, None))

    filtered: List[Tuple[Gift, float]] = []
    for gift, score in gifts_with_scores:
        if min_budget is not None and gift.price < min_budget:
            continue
        if max_budget is not None and gift.price > max_budget:
            continue
        if age_set:
            gift_ages = {str(a).lower() for a in gift.meta.get("age_fit", [])}
            if gift_ages and gift_ages.isdisjoint(age_set):
                continue
        filtered.append((gift, score))
    return filtered
