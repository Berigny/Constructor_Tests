"""
query_builder.py
Deterministic query composer for Constructor_Tests.

- Uses queries_manifest.json for allowed tokens, synonyms, categories, and rules
- Converts selected photo tags into a safe NL query
- NEVER invents demographics or age/gender words
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


class QueryBuilder:
    def __init__(self, manifest_path: str = "queries_manifest.json"):
        self.manifest_path = Path(manifest_path)
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")
        self.manifest: Dict[str, Any] = json.loads(self.manifest_path.read_text())

        # Precompute vocab sets
        self.allowed = {t.lower() for t in self.manifest.get("allowed_tokens", [])}
        self.forbidden = {t.lower() for t in self.manifest.get("forbidden_tokens", [])}
        self.synonyms = {
            k.lower(): [v.lower() for v in vs]
            for k, vs in self.manifest.get("synonyms", {}).items()
        }
        self.tag_to_categories = {
            k.lower(): vs for k, vs in self.manifest.get("tag_to_categories", {}).items()
        }
        self.rules = self.manifest.get("query_rules", {"min_tokens": 2, "max_tokens": 6})

    def _map_token(self, tag: str) -> str | None:
        """Map raw tag to canonical token (allowed or synonym)."""

        t = tag.lower()
        if t in self.allowed:
            return t
        for key, values in self.synonyms.items():
            if t == key or t in values:
                return key
        return None

    def compose(
        self, photo_tags: List[str], budget: Tuple[int, int] | None = None
    ) -> Tuple[str | None, List[str]]:
        """
        Compose a safe NL query and category list.

        Args:
            photo_tags: raw tags from selected photos
            budget: optional (low, high) tuple in AUD

        Returns:
            query (str | None), categories (list[str])
        """

        tokens: List[str] = []
        seen = set()

        for raw in photo_tags:
            mapped = self._map_token(raw)
            if mapped and mapped not in self.forbidden and mapped not in seen:
                tokens.append(mapped)
                seen.add(mapped)

        # Apply rules
        max_tokens = self.rules.get("max_tokens", 6)
        min_tokens = self.rules.get("min_tokens", 2)
        tokens = tokens[:max_tokens]

        categories = sorted(
            {
                category
                for token in tokens
                for category in self.tag_to_categories.get(token, [])
            }
        )

        if len(tokens) < min_tokens:
            if categories:
                return " ".join(categories), categories
            return None, []

        # Build query string
        query = " ".join(tokens) + " gift ideas"

        # Add budget if present
        if budget:
            _lo, hi = budget
            query += f" under {hi} AUD"

        # Map to Constructor categories
        return query, categories
