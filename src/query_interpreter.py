"""Hybrid enrichment layer that expands filtered tokens into gift-friendly terms."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Literal

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


# --- New: multi-query composer with user hints -------------------------------

Bucket = Literal["Fashion", "Books", "Tech", "Outdoors", "Home", "Entertainment"]


class Hints(TypedDict, total=False):
    recipient: str  # "me","man","woman","teen","kid","couple","family"
    colours: List[str]
    styles: List[str]  # ["casual","minimalist","retro","90s","practical","premium"]
    budget_aud: Tuple[int | None, int | None]
    cohort: str  # e.g., "Gen X"


BUCKET_TEMPLATES: Dict[Bucket, str] = {
    "Fashion": "{styles} {palette} clothes {recipient_phrase} {cohort_twist} under {hi}",
    "Books": "books and ideas on {themes} {recipient_phrase} under {hi}",
    "Tech": "tech and gadgets {style_practical} {recipient_phrase} under {hi}",
    "Outdoors": "{palette} outdoor gear and apparel {recipient_phrase} under {hi}",
    "Home": "{palette} home items {style_practical} {recipient_phrase} under {hi}",
}

STYLE_PHRASES = {
    "casual": "casual",
    "minimalist": "plain",
    "practical": "practical",
    "retro": "retro",
    "90s": "90s twist",
    "premium": "premium",
}

COHORT_PHRASE = {
    "Gen Z": "with a Gen Z vibe",
    "Millennial": "with Millennial nostalgia",
    "Gen X": "with Gen X sensibility",
    "Boomer": "classic",
}

PALETTE_CANON = {
    "black": "black",
    "blue": "blue",
    "neutral": "neutral",
    "natural": "earthy",
    "earthy": "earthy",
    "warm": "warm",
    "neon": "neon",
}


def _recipient_phrase(h: Hints) -> str:
    rec = (h.get("recipient") or "me").lower()
    return {
        "me": "for me",
        "man": "for men",
        "woman": "for women",
        "teen": "for teens",
        "kid": "for kids",
        "couple": "for couples",
        "family": "for families",
    }.get(rec, "for me")


def _palette_phrase(colours: Optional[List[str]]) -> str:
    if not colours:
        return ""
    mapped = []
    for colour in colours:
        if not colour:
            continue
        canon = PALETTE_CANON.get(colour.lower())
        if canon:
            mapped.append(canon)
    seen: set[str] = set()
    keep = [c for c in mapped if not (c in seen or seen.add(c))]
    if not keep:
        return ""
    return "in " + " and ".join(keep)


def _styles_phrase(styles: Optional[List[str]]) -> Tuple[str, str]:
    if not styles:
        return "", ""
    mapped = [STYLE_PHRASES.get(s.lower(), s.lower()) for s in styles]
    style_str = " ".join(sorted(set(mapped)))
    practical = ""
    if "practical" in mapped:
        practical = "that are practical"
    elif "plain" in mapped:
        practical = "that are plain and practical"
    return style_str, practical


def _themes_from_tokens(tokens: List[str]) -> str:
    keep = [t for t in tokens if t in {"philosophy", "art", "tech", "nature", "design"}]
    return " and ".join(keep) if keep else "philosophy and tech"


def compose_queries_multi(
    tokens: List[str],
    categories: List[str],
    hints: Hints,
    cohort_hint: Optional[str] = None,
) -> List[Tuple[Bucket, str]]:
    _lo, hi = hints.get("budget_aud") or (None, None)
    recipient = _recipient_phrase(hints)
    palette = _palette_phrase(hints.get("colours"))
    styles, style_practical = _styles_phrase(hints.get("styles"))
    cohort = cohort_hint or hints.get("cohort")
    cohort_twist = COHORT_PHRASE.get(cohort or "", "").strip()

    buckets: List[Bucket] = []
    if "Fashion" in categories or any(t in tokens for t in ("casual", "retro", "90s", "minimalist")):
        buckets.append("Fashion")
    if "Books" in categories or any(t in tokens for t in ("book", "philosophy", "art", "tech", "design")):
        buckets.append("Books")
    if "Tech" in categories or "tech" in tokens:
        buckets.append("Tech")
    if "Outdoors" in categories or any(
        t in tokens for t in ("outdoor", "nature", "hiking", "camping", "summer", "sun", "beach")
    ):
        buckets.append("Outdoors")
    if "Home" in categories or "window" in tokens:
        buckets.append("Home")
    seen: set[str] = set()
    buckets = [b for b in buckets if not (b in seen or seen.add(b))][:5]
    if not buckets:
        buckets = ["Tech", "Books"]

    themes = _themes_from_tokens(tokens)
    if isinstance(hi, (int, float)) and hi:
        budget_phrase = f"${int(hi)}"
    else:
        budget_phrase = "$100"

    out: List[Tuple[Bucket, str]] = []
    for bucket in buckets:
        template = BUCKET_TEMPLATES[bucket]
        query = template.format(
            styles=styles or "casual",
            palette=palette,
            recipient_phrase=recipient,
            cohort_twist=f"{cohort_twist}" if cohort_twist else "",
            style_practical=style_practical or "that are plain and practical",
            themes=themes,
            hi=budget_phrase,
        )
        query = " ".join(query.split())
        out.append((bucket, query))
    return out


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
        ui_recipient: Optional[str] = None,
        ui_colours: Optional[List[str]] = None,
        ui_styles: Optional[List[str]] = None,
        ui_cohort: Optional[str] = None,
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

        hints: Hints = {}
        if ui_recipient:
            hints["recipient"] = ui_recipient
        if ui_colours:
            colour_list = [c for c in ui_colours if c]
            if colour_list:
                colour_list = list(dict.fromkeys(colour_list))
            if colour_list:
                hints["colours"] = colour_list
        if ui_styles:
            style_list = [s for s in ui_styles if s]
            if style_list:
                style_list = list(dict.fromkeys(style_list))
            if style_list:
                hints["styles"] = style_list
        if budget_aud:
            lo, hi = budget_aud
            hints["budget_aud"] = (lo, hi)
        if ui_cohort:
            hints["cohort"] = ui_cohort

        multi_queries = compose_queries_multi(
            filtered_tokens,
            expanded_categories,
            hints,
            cohort_hint=cohort,
        )

        queries_multi: List[Tuple[Bucket, str]] = []
        for bucket, query_text in multi_queries:
            allow_terms = query_text.split()
            rewritten = _llm_rewrite(allow_terms, cohort, budget_aud) if use_llm else None
            queries_multi.append((bucket, rewritten or query_text))

        final_query = (
            queries_multi[0][1]
            if queries_multi
            else (query_llm or query_no_llm)
        )

        return {
            "tokens": filtered_tokens,
            "categories": expanded_categories,
            "cohort": cohort,
            "product_terms": product_terms,
            "query_no_llm": query_no_llm,
            "query_llm": query_llm,
            "queries_multi": queries_multi,
            "final_query": final_query,
        }
