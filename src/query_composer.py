"""Deterministic helpers for composing Constructor search queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import re

# Terms that must never appear in the final natural-language query unless they
# are explicitly provided as structured metadata signals.
FORBIDDEN_TERMS: Tuple[str, ...] = (
    "girl",
    "girls",
    "boy",
    "boys",
    "woman",
    "women",
    "man",
    "men",
    "lady",
    "ladies",
    "gent",
    "gents",
    "adult",
    "adults",
    "teen",
    "teens",
    "kid",
    "kids",
    "child",
    "children",
    "for him",
    "for her",
    "for boys",
    "for girls",
    "mum",
    "mom",
    "dad",
    "grandma",
    "grandpa",
)

# Whitelisted tokens that can be emitted from taste tags. All tokens are stored
# in their normalised (lowercase) form to simplify matching.
DEFAULT_ALLOWLIST: Tuple[str, ...] = (
    "outdoor",
    "outdoors",
    "nature",
    "earthy",
    "calm",
    "cozy",
    "cosy",
    "handmade",
    "retro",
    "vintage",
    "minimalist",
    "home",
    "travel",
    "camping",
    "hiking",
    "craft",
    "crafts",
    "handcrafted",
    "eco",
    "sustainable",
    "botanical",
    "garden",
    "gardening",
    "rustic",
    "wooden",
    "natural",
)

# Synonyms/bridging map so descriptive photo tags (e.g. "handcrafted") can be
# converted into the concise whitelist tokens used in the final query.
DEFAULT_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "nature": ("outdoor", "nature"),
    "outdoors": ("outdoor", "nature"),
    "calm": ("calm", "cozy"),
    "relaxed": ("calm", "cozy"),
    "relax": ("calm", "cozy"),
    "earth": ("earthy",),
    "earthy": ("earthy",),
    "handcrafted": ("handmade",),
    "handcraft": ("handmade",),
    "hand-crafted": ("handmade",),
    "craft": ("craft", "handmade"),
    "crafts": ("craft", "handmade"),
    "maker": ("craft", "handmade"),
    "makers": ("craft", "handmade"),
    "retro": ("retro", "vintage"),
    "vintage": ("vintage",),
    "heritage": ("vintage",),
    "minimal": ("minimalist",),
    "minimalist": ("minimalist",),
    "botanical": ("botanical", "garden"),
    "garden": ("garden", "outdoor"),
    "gardening": ("gardening", "outdoor"),
    "rustic": ("rustic", "natural"),
    "wooden": ("wooden", "natural"),
    "natural": ("natural", "earthy"),
    "eco": ("eco", "sustainable"),
    "sustainable": ("sustainable", "eco"),
    "travel": ("travel",),
    "camping": ("camping", "outdoor"),
    "hiking": ("hiking", "outdoor"),
    "adventure": ("outdoor", "travel"),
    "calming": ("calm", "cozy"),
    "soothing": ("calm", "cozy"),
    "serene": ("calm", "cozy"),
}

DEFAULT_CATEGORY_MAP: Dict[str, Tuple[str, ...]] = {
    "outdoor": ("Outdoors",),
    "outdoors": ("Outdoors",),
    "nature": ("Outdoors",),
    "earthy": ("Home", "Outdoors"),
    "calm": ("Home",),
    "cozy": ("Home",),
    "cosy": ("Home",),
    "handmade": ("Craft Supplies", "Home"),
    "craft": ("Craft Supplies",),
    "crafts": ("Craft Supplies",),
    "retro": ("Home",),
    "vintage": ("Home",),
    "minimalist": ("Home",),
    "home": ("Home",),
    "travel": ("Travel",),
    "camping": ("Outdoors", "Travel"),
    "hiking": ("Outdoors",),
    "eco": ("Home",),
    "sustainable": ("Home",),
    "botanical": ("Home", "Outdoors"),
    "garden": ("Outdoors",),
    "gardening": ("Outdoors",),
    "rustic": ("Home",),
    "wooden": ("Home",),
    "natural": ("Home", "Outdoors"),
}

_WORD_RE = re.compile(r"[^a-z0-9]+")


def _normalise(text: str) -> str:
    """Normalise arbitrary text for token comparisons."""
    return _WORD_RE.sub(" ", text.lower()).strip()


def _dedupe_preserve(seq: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in seq:
        key = item.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def select_allowed_terms(
    taste_top: Sequence[str],
    allow: Sequence[str] | None = None,
    synonyms: Mapping[str, Sequence[str]] | None = None,
    max_terms: int = 4,
    min_terms: int = 2,
) -> List[str]:
    """Return allowed tokens derived from ``taste_top`` in a deterministic way."""

    allow_set = {_normalise(term) for term in (allow or DEFAULT_ALLOWLIST)}
    allow_set.discard("")

    syn_map: Dict[str, Tuple[str, ...]] = {}
    source = synonyms or DEFAULT_SYNONYMS
    for key, values in source.items():
        norm_key = _normalise(key)
        norm_vals = tuple(_normalise(val) for val in values if _normalise(val))
        if norm_vals:
            syn_map[norm_key] = norm_vals

    tokens: List[str] = []
    for raw in taste_top:
        norm_tag = _normalise(str(raw))
        if not norm_tag:
            continue
        expansions = list(syn_map.get(norm_tag, ()))
        parts = [p for p in norm_tag.split() if p]
        expansions.extend(parts)
        if norm_tag not in expansions:
            expansions.append(norm_tag)
        for candidate in expansions:
            cand_norm = _normalise(candidate)
            if cand_norm in allow_set and cand_norm not in tokens:
                tokens.append(cand_norm)
                if len(tokens) >= max_terms:
                    return tokens

    if len(tokens) >= min_terms:
        return tokens

    # Second pass – attempt to pull additional synonym hits to satisfy
    # ``min_terms``.
    for raw in taste_top:
        norm_tag = _normalise(str(raw))
        if not norm_tag:
            continue
        for candidate in syn_map.get(norm_tag, ()):  # already normalised
            if candidate in allow_set and candidate not in tokens:
                tokens.append(candidate)
                if len(tokens) >= min_terms:
                    return tokens

    return tokens


@dataclass(frozen=True)
class QueryPlan:
    """Bundle describing the composed query and derived metadata."""

    query: str
    tokens: Tuple[str, ...]
    categories: Tuple[str, ...]


def compose_query_from_tags(
    taste_top: Sequence[str],
    allow: Sequence[str] | None = None,
    synonyms: Mapping[str, Sequence[str]] | None = None,
    category_map: Mapping[str, Sequence[str]] | None = None,
    suffix: Sequence[str] = ("gift", "ideas"),
    max_terms: int = 4,
    min_terms: int = 2,
) -> QueryPlan:
    """Compose a Constructor-ready natural-language query from taste tags."""

    tokens = select_allowed_terms(
        taste_top,
        allow=allow,
        synonyms=synonyms,
        max_terms=max_terms,
        min_terms=min_terms,
    )

    sequence = list(tokens)
    sequence.extend(suffix)
    sequence = _dedupe_preserve(sequence)
    query = sanitize_query(" ".join(sequence))

    cat_map: Dict[str, Tuple[str, ...]] = {}
    source = category_map or DEFAULT_CATEGORY_MAP
    for key, values in source.items():
        norm_key = _normalise(key)
        norm_vals = tuple(str(v) for v in values if str(v).strip())
        if norm_vals:
            cat_map[norm_key] = norm_vals

    categories: List[str] = []
    for token in tokens:
        norm_token = _normalise(token)
        for cat in cat_map.get(norm_token, ()):  # already a tuple
            if cat not in categories:
                categories.append(cat)

    return QueryPlan(query=query, tokens=tuple(tokens), categories=tuple(categories))


def sanitize_query(q: str) -> str:
    """Remove forbidden demographic terms and tidy whitespace."""

    if not q:
        return ""

    cleaned = str(q)

    # Remove phrases from the forbidden set.
    for term in sorted(FORBIDDEN_TERMS, key=len, reverse=True):
        pattern = re.compile(r"\b" + r"\s+".join(re.escape(part) for part in term.split()) + r"\b", re.IGNORECASE)
        cleaned = pattern.sub(" ", cleaned)

    # Preserve "gift ideas" but strip gift-card drift.
    cleaned = re.sub(r"\bgift\s*-?cards?\b", "", cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    return cleaned


def top_tags_from_rows(rows: Iterable[Mapping[str, object]], top_k: int = 6) -> List[str]:
    """Aggregate tags from metadata rows and return the top ``top_k`` entries."""

    counts: Dict[str, int] = {}
    first_seen: Dict[str, int] = {}
    canonical: Dict[str, str] = {}
    order = 0

    for row in rows:
        tags: Optional[Iterable[object]] = None
        getter = getattr(row, "get", None)
        if callable(getter):  # pandas Series exposes .get
            tags = getter("tags")
        if tags is None:
            try:
                tags = row["tags"]  # type: ignore[index]
            except Exception:  # pragma: no cover - defensive guard
                tags = None
        if not isinstance(tags, Iterable):
            continue
        for tag in tags:
            if tag is None:
                continue
            text = str(tag).strip()
            if not text:
                continue
            norm = _normalise(text)
            if not norm:
                continue
            counts[norm] = counts.get(norm, 0) + 1
            if norm not in first_seen:
                first_seen[norm] = order
                canonical[norm] = text
                order += 1

    if not counts:
        return []

    sorted_norms = sorted(
        counts.keys(),
        key=lambda key: (-counts[key], first_seen[key]),
    )
    return [canonical[key] for key in sorted_norms[:top_k]]


__all__ = [
    "compose_query_from_tags",
    "FORBIDDEN_TERMS",
    "QueryPlan",
    "sanitize_query",
    "select_allowed_terms",
    "top_tags_from_rows",
]
