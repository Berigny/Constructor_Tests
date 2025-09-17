"""Hybrid enrichment layer that expands filtered tokens into gift-friendly terms."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_METADATA_PATH = "unsplash_images/metadata.json"
DEFAULT_MANIFEST_PATH = "queries_manifest.json"

FORBIDDEN = {
    "girl",
    "girls",
    "boy",
    "boys",
    "woman",
    "women",
    "man",
    "men",
    "female",
    "male",
    "lady",
    "gentleman",
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
    "mum",
    "mom",
    "dad",
    "grandma",
    "grandpa",
}

TOKEN_TO_COHORT = {
    "vintage": "Gen X / Millennial nostalgia",
    "retro": "Millennial nostalgia",
    "90s": "Millennial nostalgia",
    "aesthetic": "Gen Z vibe",
    "festival": "Gen Z / Millennial",
    "classic": "Gen X / Boomer",
    "film": "Gen X / Millennial",
    "polaroid": "Gen X / Millennial",
    "tiktok": "Gen Z vibe",
    "neon": "Gen Z vibe",
    "y2k": "Gen Z vibe",
    "streetwear": "Gen Z vibe",
    "cottagecore": "Millennial / Gen Z",
}

TOKEN_TO_PRODUCT_TERMS: Dict[str, List[str]] = {
    "summer": ["sunglasses", "sun hat", "beach towel", "cooler bag"],
    "sun": ["sunglasses", "sunscreen set", "cap"],
    "beach": ["beach towel", "dry bag", "sand-proof blanket"],
    "outdoor": ["insulated bottle", "daypack", "picnic set", "camping mug"],
    "outdoors": ["insulated bottle", "daypack", "picnic set", "camping mug"],
    "hiking": ["trekking socks", "trail snacks", "hydration flask", "compact first-aid kit"],
    "camping": ["enamel mug", "compact lantern", "firestarter kit"],
    "window": ["indoor plant kit", "aromatherapy diffuser", "scented candle", "ceramic vase"],
    "home": ["throw blanket", "candle", "planter", "coaster set"],
    "retro": ["vinyl record", "retro poster", "polaroid film"],
    "vintage": ["vinyl record", "analogue photo album"],
    "vinyl": ["record", "anti-static brush", "slipmat"],
    "coffee": ["pour-over kit", "hand grinder", "ceramic mug", "cold brew bottle"],
    "tea": ["loose leaf sampler", "teapot infuser"],
    "gaming": ["controller stand", "desk mat", "headset holder"],
    "book": ["gift book", "journal", "reading light"],
    "books": ["gift book", "journal", "reading light"],
    "craft": ["ceramic kit", "embroidery kit", "leather key kit"],
    "crafts": ["ceramic kit", "embroidery kit", "leather key kit"],
    "travel": ["packing cubes", "weekender bag", "passport wallet"],
    "minimalist": ["clean desk organiser", "wireless charger", "matte water bottle"],
    "minimal": ["clean desk organiser", "wireless charger", "matte water bottle"],
    "art": ["art print", "museum membership", "colouring book for adults"],
    "forest": ["hiking socks", "outdoor blanket"],
    "mountain": ["daypack", "insulated bottle"],
    "mountains": ["daypack", "insulated bottle"],
}

CATEGORY_TO_DEFAULT_TERMS: Dict[str, List[str]] = {
    "Outdoors": ["sunglasses", "insulated bottle", "daypack", "picnic set", "camping mug"],
    "Home": ["aromatherapy diffuser", "scented candle", "indoor plant kit", "ceramic vase"],
    "Tech": ["power bank", "wireless charger", "bluetooth tracker"],
    "Entertainment": ["board game", "vinyl record", "bluetooth speaker"],
    "Books": ["gift book", "journal", "reading light"],
    "Fashion": ["cap", "scarf", "sunglasses"],
    "Food": ["gourmet chocolate", "coffee beans", "tea sampler"],
    "Crafts": ["ceramic kit", "embroidery kit", "woodcraft kit"],
    "Sports": ["yoga mat", "microfibre towel", "sports bottle"],
    "Travel": ["packing cubes", "weekender bag", "passport wallet"],
}


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _normalise_tokens(tokens: List[str] | None) -> List[str]:
    cleaned: List[str] = []
    for token in tokens or []:
        norm = (token or "").strip().lower()
        if not norm or norm in FORBIDDEN:
            continue
        norm = norm.replace("_", "-")
        if norm == "cosy":
            norm = "cozy"
        cleaned.append(norm)
    deduped: List[str] = []
    seen: set[str] = set()
    for token in cleaned:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def _map_marker(label: str) -> Optional[str]:
    text = (label or "").lower()
    if "gen z" in text or "genz" in text:
        return "Gen Z"
    if "millennial" in text or "gen y" in text:
        return "Millennial"
    if "gen x" in text:
        return "Gen X"
    if "boomer" in text:
        return "Boomer"
    return None


def _infer_from_node(node: Dict[str, Any], counts: Dict[str, int]) -> None:
    for key in ("gen_marker", "cohort", "generation"):
        value = node.get(key)
        if isinstance(value, str):
            value = [value]
        if isinstance(value, list):
            for item in value:
                cohort = _map_marker(str(item))
                if cohort:
                    counts[cohort] = counts.get(cohort, 0) + 1
    facets = node.get("facets")
    if isinstance(facets, dict):
        facet_vals = facets.get("gen_marker")
        if isinstance(facet_vals, str):
            facet_vals = [facet_vals]
        if isinstance(facet_vals, list):
            for item in facet_vals:
                cohort = _map_marker(str(item))
                if cohort:
                    counts[cohort] = counts.get(cohort, 0) + 1


def _infer_cohort_from_metadata(photo_ids: List[str], metadata: Any) -> Optional[str]:
    if not metadata:
        return None
    counts: Dict[str, int] = {}

    def record(candidate_ids: List[str], node: Dict[str, Any]) -> None:
        if not isinstance(node, dict):
            return
        _infer_from_node(node, counts)

    if isinstance(metadata, dict):
        if "photos" in metadata:
            return _infer_cohort_from_metadata(photo_ids, metadata.get("photos"))
        for pid in photo_ids:
            key = str(pid)
            node = metadata.get(key)
            if not isinstance(node, dict):
                continue
            record([key], node)
    elif isinstance(metadata, list):
        for node in metadata:
            if not isinstance(node, dict):
                continue
            node_ids = []
            if "id" in node:
                node_ids.append(str(node["id"]))
            if "photo_id" in node:
                node_ids.append(str(node["photo_id"]))
            if not node_ids:
                continue
            for pid in photo_ids:
                if str(pid) in node_ids:
                    record(node_ids, node)
                    break
    if not counts:
        return None
    items = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    best_label, best_count = items[0]
    if len(items) == 1:
        return best_label
    second_count = items[1][1]
    if best_count >= max(2, 2 * second_count):
        return best_label
    return best_label


def _infer_cohort(tokens: List[str], photo_ids: List[str], metadata_path: Path) -> Optional[str]:
    metadata = _read_json(metadata_path)
    cohort = _infer_cohort_from_metadata(photo_ids, metadata)
    if cohort:
        return cohort
    for token in tokens:
        if token in TOKEN_TO_COHORT:
            return TOKEN_TO_COHORT[token]
    return None


def _load_manifest(manifest_path: Path) -> Dict[str, Any]:
    manifest = _read_json(manifest_path) or {}
    tag_map = manifest.get("tag_to_categories", {})
    manifest["tag_to_categories"] = {
        (key or "").lower(): value for key, value in tag_map.items()
    }
    manifest["allowed_tokens"] = [
        (token or "").lower() for token in manifest.get("allowed_tokens", [])
    ]
    manifest["forbidden_tokens"] = [
        (token or "").lower() for token in manifest.get("forbidden_tokens", [])
    ]
    return manifest


def _expand_categories(tokens: List[str], base_categories: List[str], manifest: Dict[str, Any]) -> List[str]:
    categories = set(base_categories or [])
    mapping = manifest.get("tag_to_categories", {})
    for token in tokens:
        for category in mapping.get(token, []) or []:
            categories.add(category)
    return sorted(categories)


def _product_seeds(tokens: List[str], categories: List[str], max_terms: int) -> List[str]:
    seeds: List[str] = []
    for token in tokens:
        seeds.extend(TOKEN_TO_PRODUCT_TERMS.get(token, []))
    for category in categories:
        seeds.extend(CATEGORY_TO_DEFAULT_TERMS.get(category, []))
    normalised = _normalise_tokens(seeds)
    output: List[str] = []
    for term in normalised:
        if term not in output and len(output) < max_terms:
            output.append(term)
    return output


def _llm_rewrite(
    allowed_terms: List[str],
    cohort: Optional[str],
    budget: Optional[Tuple[int, int]],
) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        use_v1 = True
    except Exception:
        try:
            import openai

            openai.api_key = api_key
            use_v1 = False
        except Exception:
            return None

    forbidden = ", ".join(sorted(FORBIDDEN))
    prompt = (
        "You will compose a concise gift search string.\n"
        "You MAY ONLY use the provided ALLOWED_TERMS (reorder or omit as needed).\n"
        "Do NOT add new nouns, age, gender, or relationship words.\n"
        "Forbidden words: "
        + forbidden
        + "\n"
        + "Output ONE line with no quotes, no punctuation lists.\n"
        + f"ALLOWED_TERMS: {', '.join(allowed_terms)}\n"
    )
    if cohort:
        prompt += f"Cohort vibe: {cohort}. Use it as flavour only, not demographics.\n"
    if budget:
        _low, high = budget
        prompt += f"If natural, append 'under {high} AUD'.\n"

    try:
        if use_v1:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Be precise, safe, and minimal."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            text = (response.choices[0].message.content or "").strip()
        else:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Be precise, safe, and minimal."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            text = (response["choices"][0]["message"]["content"] or "").strip()
    except Exception:
        return None

    output = re.sub(r"\s+", " ", text).strip().lower()
    for bad in FORBIDDEN:
        output = output.replace(bad, "")
    output = " ".join(output.split())
    return output or None


class QueryInterpreter:
    def __init__(
        self,
        manifest_path: str = DEFAULT_MANIFEST_PATH,
        metadata_path: str = DEFAULT_METADATA_PATH,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.metadata_path = Path(metadata_path)
        self.manifest = _load_manifest(self.manifest_path)

    def interpret(
        self,
        tokens: List[str],
        categories: Optional[List[str]],
        photo_ids: Optional[List[str]],
        budget_aud: Optional[Tuple[int, int]] = None,
        use_llm: bool = True,
        max_terms: int = 12,
    ) -> Dict[str, Any]:
        filtered_tokens = _normalise_tokens(tokens)
        expanded_categories = _expand_categories(
            filtered_tokens, categories or [], self.manifest
        )
        cohort = _infer_cohort(filtered_tokens, photo_ids or [], self.metadata_path)
        product_terms = _product_seeds(filtered_tokens, expanded_categories, max_terms)

        ordered: List[str] = []
        seen: set[str] = set()
        for part in filtered_tokens + expanded_categories + product_terms:
            if part not in seen:
                seen.add(part)
                ordered.append(part)
        ordered = ordered[: max(8, max_terms)]
        query_no_llm = " ".join(ordered)
        if budget_aud:
            _low, high = budget_aud
            query_no_llm = f"{query_no_llm} under {high} aud"

        allowed_terms = list(ordered)
        if cohort:
            allowed_terms.append(cohort)
        query_llm = _llm_rewrite(allowed_terms, cohort, budget_aud) if use_llm else None
        final_query = query_llm or query_no_llm

        return {
            "tokens": filtered_tokens,
            "categories": expanded_categories,
            "cohort": cohort,
            "product_terms": product_terms,
            "query_no_llm": query_no_llm,
            "query_llm": query_llm,
            "final_query": final_query,
        }
