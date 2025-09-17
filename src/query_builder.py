"""Deterministic, whitelist-based query composer used by the Streamlit app."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class QueryBuilder:
    """Compose safe Constructor natural-language queries from photo tags."""

    def __init__(self, manifest_path: str = "queries_manifest.json"):
        self.manifest_path = Path(manifest_path)
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        self.manifest: Dict[str, Any] = json.loads(self.manifest_path.read_text())

        # Pre-compute vocabulary helpers
        self.allowed = {t.lower() for t in self.manifest.get("allowed_tokens", [])}
        self.forbidden = {t.lower() for t in self.manifest.get("forbidden_tokens", [])}

        # synonyms are stored in the manifest as {canonical: [aliases]}
        syn = self.manifest.get("synonyms", {})
        self.syn_to_canon: Dict[str, str] = {}
        for canonical, aliases in syn.items():
            canon = canonical.lower()
            self.syn_to_canon[canon] = canon
            for alias in aliases:
                self.syn_to_canon[alias.lower()] = canon

        self.tag_to_categories = {
            key.lower(): list(values)
            for key, values in self.manifest.get("tag_to_categories", {}).items()
        }
        self.rules = self.manifest.get("query_rules", {"min_tokens": 2, "max_tokens": 6})

    # ------------------------------------------------------------------
    # Normalisation helpers

    def _canonicalise(self, tag: str) -> Optional[str]:
        """Return the canonical allowed token for ``tag`` or ``None``."""

        token = (tag or "").strip().lower()
        if not token or token in self.forbidden:
            return None

        if token in self.allowed:
            return token

        if token in self.syn_to_canon:
            canonical = self.syn_to_canon[token]
            if canonical in self.allowed and canonical not in self.forbidden:
                return canonical
        return None

    @staticmethod
    def _dedupe_preserve(seq: List[str]) -> List[str]:
        seen: set[str] = set()
        output: List[str] = []
        for item in seq:
            if item not in seen:
                seen.add(item)
                output.append(item)
        return output

    # ------------------------------------------------------------------
    # Public API

    def compose(
        self, photo_tags: List[str], budget: Tuple[int, int] | None = None
    ) -> Tuple[Optional[str], List[str]]:
        query, categories, _ = self.compose_with_debug(photo_tags, budget)
        return query, categories

    def compose_with_debug(
        self, photo_tags: List[str], budget: Tuple[int, int] | None = None
    ) -> Tuple[Optional[str], List[str], Dict[str, Any]]:
        """
        Compose a query and return debug information about dropped tags.

        Returns ``(query_or_none, categories, debug_dict)``.
        The ``debug_dict`` exposes raw tags, filtered tokens and reasons for drops
        so the UI can visualise what happened.
        """

        raw_tags = [tag for tag in (photo_tags or []) if isinstance(tag, str)]
        filtered: List[str] = []
        dropped_forbidden: List[str] = []
        dropped_not_allowed: List[str] = []

        for raw in raw_tags:
            token = (raw or "").strip().lower()
            if not token:
                continue
            if token in self.forbidden:
                dropped_forbidden.append(token)
                continue
            canonical = self._canonicalise(token)
            if canonical is None:
                dropped_not_allowed.append(token)
                continue
            filtered.append(canonical)

        filtered = self._dedupe_preserve(filtered)

        max_tokens = self.rules.get("max_tokens", 6)
        if max_tokens:
            filtered = filtered[:max_tokens]

        categories = sorted(
            {
                category
                for token in filtered
                for category in self.tag_to_categories.get(token, [])
            }
        )

        min_tokens = self.rules.get("min_tokens", 2)
        if len(filtered) >= max(min_tokens, 0):
            query: Optional[str] = " ".join(filtered)
            if budget:
                _low, high = budget
                query = f"{query} under {high} AUD"
        elif categories:
            query = " ".join(categories)
        else:
            query = None

        debug = {
            "raw_tags": raw_tags,
            "filtered_tokens": filtered,
            "dropped_forbidden": self._dedupe_preserve(dropped_forbidden),
            "dropped_not_allowed": self._dedupe_preserve(dropped_not_allowed),
            "categories": categories,
            "min_tokens": min_tokens,
            "max_tokens": max_tokens,
        }

        return query, categories, debug
