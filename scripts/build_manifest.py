#!/usr/bin/env python3
"""
Builds/refreshes queries_manifest.json from your photo metadata.

- Reads photos from JSONL/JSON files (e.g., Unsplash exports, your own manifest)
- Extracts/normalises tags (plus optional alt_description tokens)
- Removes demographics/colours/common junk
- Optionally calls OpenAI to map tags → broad product categories if OPENAI_API_KEY is set
- Merges with an existing manifest (preserves custom synonyms/rules unless --fresh)

Usage:
  python scripts/build_manifest.py \
      --photos data/photos.jsonl data/extra.json \
      --out queries_manifest.json \
      --categories Outdoors Home Tech Entertainment Books Fashion Food Crafts Sports Travel \
      --min-count 2 \
      --llm-map  # (optional, requires OPENAI_API_KEY)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

# -------------------------- Config: defaults -------------------------------

DEFAULT_FORBIDDEN_DEMOGRAPHICS = {
    "woman",
    "women",
    "man",
    "men",
    "girl",
    "girls",
    "boy",
    "boys",
    "human",
    "people",
    "kid",
    "kids",
    "child",
    "children",
    "adult",
    "adults",
    "male",
    "female",
    "grandma",
    "grandpa",
    "mum",
    "mom",
    "dad",
    "mother",
    "father",
    "lady",
    "gentleman",
}
DEFAULT_FORBIDDEN_COLOURS = {
    "black",
    "white",
    "grey",
    "gray",
    "blue",
    "red",
    "green",
    "yellow",
    "purple",
    "pink",
    "orange",
    "brown",
    "beige",
    "turquoise",
    "teal",
    "maroon",
    "navy",
    "gold",
    "silver",
}
DEFAULT_JUNK = {
    "portrait",
    "closeup",
    "close-up",
    "studio",
    "model",
    "person",
    "face",
    "headshot",
    "no-person",
    "nobody",
    "copyspace",
    "copy-space",
    "vertical",
    "horizontal",
    "background",
    "wallpaper",
    "hd",
    "4k",
    "macro",
    "bokeh",
}
DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "of",
    "in",
    "on",
    "to",
    "with",
    "for",
    "by",
    "at",
    "from",
    "into",
    "over",
    "under",
    "is",
    "are",
    "this",
    "that",
}

# British/American normalisations & tiny built-ins
CANON_SYNONYMS: Dict[str, List[str]] = {
    "cozy": ["cosy"],
    "vintage": ["retro"],
    "photo": ["photography", "photograph"],
}
DEFAULT_CATEGORIES = [
    "Outdoors",
    "Home",
    "Tech",
    "Entertainment",
    "Books",
    "Fashion",
    "Food",
    "Crafts",
    "Sports",
    "Travel",
]

TOKEN_RE = re.compile(r"[a-z][a-z0-9\-]+", re.I)


# -------------------------- Helpers ----------------------------------------


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def iter_photo_objs(paths: List[Path]):
    for p in paths:
        if not p.exists():
            continue
        if p.suffix.lower() == ".jsonl":
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
        elif p.suffix.lower() == ".json":
            obj = load_json(p)
            if isinstance(obj, list):
                for o in obj:
                    if isinstance(o, dict):
                        yield o
            elif isinstance(obj, dict):
                seq = obj.get("photos") if "photos" in obj else [obj]
                for o in seq:
                    if isinstance(o, dict):
                        yield o


def tokenise(text: str) -> List[str]:
    toks = [t.lower() for t in TOKEN_RE.findall(text or "")]
    return [t for t in toks if t not in DEFAULT_STOPWORDS and not t.isdigit()]


def normalise_tag(tag: str) -> str:
    t = tag.strip().lower()
    t = t.replace("_", "-")
    for canon, values in CANON_SYNONYMS.items():
        if t == canon or t in values:
            return canon
    return t


def collect_tags(photo_paths: List[Path], use_alt_description: bool, min_len: int) -> Counter:
    counts: Counter[str] = Counter()
    for obj in iter_photo_objs(photo_paths):
        tags: List[str] = []
        if "tags" in obj and isinstance(obj["tags"], list):
            for item in obj["tags"]:
                if isinstance(item, dict) and "title" in item:
                    tags.append(str(item["title"]))
                elif isinstance(item, str):
                    tags.append(item)
        for key in ("photo_tags", "labels", "keywords"):
            if key in obj and isinstance(obj[key], list):
                tags.extend([str(x) for x in obj[key]])
        if use_alt_description:
            for key in ("alt_description", "alt", "description", "prompt"):
                if key in obj and isinstance(obj[key], str):
                    tags.extend(tokenise(obj[key]))
        for raw in tags:
            token = normalise_tag(str(raw))
            if len(token) >= min_len:
                counts[token] += 1
    return counts


def build_vocab(counts: Counter, min_count: int) -> List[str]:
    forbid = (
        DEFAULT_FORBIDDEN_DEMOGRAPHICS
        | DEFAULT_FORBIDDEN_COLOURS
        | DEFAULT_JUNK
    )
    vocab = [t for t, c in counts.items() if c >= min_count and t not in forbid]
    camera_terms = {"dslr", "mirrorless", "nikon", "canon", "fujifilm", "leica", "lens"}
    vocab = [t for t in vocab if t not in camera_terms]
    return sorted(set(vocab))


def merge_existing(
    manifest_path: Path,
    new_allowed: List[str],
    new_tag2cat: Dict[str, List[str]],
    fresh: bool,
):
    if not manifest_path.exists() or fresh:
        return {
            "allowed_tokens": new_allowed,
            "forbidden_tokens": sorted(
                DEFAULT_FORBIDDEN_DEMOGRAPHICS | DEFAULT_FORBIDDEN_COLOURS
            ),
            "synonyms": CANON_SYNONYMS,
            "tag_to_categories": new_tag2cat,
            "query_rules": {
                "min_tokens": 2,
                "max_tokens": 6,
                "lowercase": True,
                "dedupe": True,
            },
            "rerank_rules": {
                "penalise_out_of_budget": 0.15,
                "penalise_contradictory_style": 0.20,
                "explanation_max_words": 18,
                "never_add_demographics": True,
            },
        }

    existing = json.loads(manifest_path.read_text())
    allowed = set(existing.get("allowed_tokens", [])) | set(new_allowed)
    tag_map = dict(existing.get("tag_to_categories", {}))
    for tag, cats in new_tag2cat.items():
        tag_map.setdefault(tag, cats)
    synonyms = dict(existing.get("synonyms", {}))
    for key, values in CANON_SYNONYMS.items():
        synonyms.setdefault(key, values)
    forbidden = set(existing.get("forbidden_tokens", [])) | (
        DEFAULT_FORBIDDEN_DEMOGRAPHICS | DEFAULT_FORBIDDEN_COLOURS
    )
    existing["allowed_tokens"] = sorted(allowed)
    existing["forbidden_tokens"] = sorted(forbidden)
    existing["synonyms"] = synonyms
    existing["tag_to_categories"] = tag_map
    existing.setdefault(
        "query_rules",
        {"min_tokens": 2, "max_tokens": 6, "lowercase": True, "dedupe": True},
    )
    existing.setdefault(
        "rerank_rules",
        {
            "penalise_out_of_budget": 0.15,
            "penalise_contradictory_style": 0.20,
            "explanation_max_words": 18,
            "never_add_demographics": True,
        },
    )
    return existing


# -------------------------- Optional LLM mapping ----------------------------

def llm_map_tags_to_categories(tags: List[str], categories: List[str]) -> Dict[str, List[str]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return heuristic_tag_to_categories(tags, categories)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
    except Exception:
        return heuristic_tag_to_categories(tags, categories)

    tag2cat: Dict[str, List[str]] = {}
    chunk_size = 30
    for i in range(0, len(tags), chunk_size):
        chunk = tags[i : i + chunk_size]
        prompt = (
            "Classify each tag into zero or more of these product categories.\n"
            f"Categories: {', '.join(categories)}\n"
            "Return JSON object mapping tag -> [categories]. Only use the provided category names. If unclear, return [].\n\n"
            f"Tags: {', '.join(chunk)}"
        )
        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a careful classifier."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
        except Exception:
            tag2cat.update(heuristic_tag_to_categories(chunk, categories))
            continue
        text = resp.choices[0].message.content.strip()
        try:
            obj = json.loads(text)
        except Exception:
            tag2cat.update(heuristic_tag_to_categories(chunk, categories))
            continue
        for tag, cats in obj.items():
            if isinstance(cats, list):
                tag2cat[tag] = [c for c in cats if c in categories]
    return tag2cat


def heuristic_tag_to_categories(tags: List[str], categories: List[str]) -> Dict[str, List[str]]:
    cats = set(categories)
    out: Dict[str, List[str]] = {}
    for tag in tags:
        lowered = tag.lower()
        mapped: List[str] = []
        if any(word in lowered for word in ("hike", "camp", "trail", "forest", "mountain", "outdoor", "nature", "surf", "beach")):
            mapped.append("Outdoors")
        if any(word in lowered for word in ("home", "kitchen", "mug", "candle", "decor", "plant", "garden", "cozy", "cozy", "ceramic", "pottery")):
            mapped.append("Home")
        if any(word in lowered for word in ("tech", "gadget", "smart", "wireless", "headphone", "charger")):
            mapped.append("Tech")
        if any(word in lowered for word in ("music", "vinyl", "record", "film", "movie", "game", "gaming", "console", "boardgame")):
            mapped.append("Entertainment")
        if any(word in lowered for word in ("book", "novel", "journal", "notebook", "reading")):
            mapped.append("Books")
        if any(word in lowered for word in ("watch", "scarf", "bag", "handbag", "wallet", "fashion", "jewelry", "jewellery")):
            mapped.append("Fashion")
        if any(word in lowered for word in ("coffee", "tea", "brew", "cook", "chef", "kitchen", "snack", "chocolate")):
            mapped.append("Food")
        if any(word in lowered for word in ("craft", "handmade", "diy", "knit", "yarn", "needle", "sew", "embroidery", "woodwork", "leather")):
            mapped.append("Crafts")
        if any(word in lowered for word in ("sport", "cycling", "bike", "run", "yoga", "fitness", "gym", "ball", "tennis", "golf")):
            mapped.append("Sports")
        if any(word in lowered for word in ("travel", "luggage", "passport", "weekender", "trip")):
            mapped.append("Travel")
        out[tag] = [c for c in mapped if c in cats]
    return out


# -------------------------- Main -------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--photos", nargs="+", required=True, help="Paths to photos JSON/JSONL files")
    parser.add_argument("--out", default="queries_manifest.json", help="Output manifest path")
    parser.add_argument(
        "--categories",
        nargs="*",
        default=DEFAULT_CATEGORIES,
        help="Category names",
    )
    parser.add_argument("--min-count", type=int, default=2, help="Min tag frequency to include in allowed_tokens")
    parser.add_argument("--min-len", type=int, default=3, help="Min token length to keep")
    parser.add_argument(
        "--use-alt-description",
        action="store_true",
        help="Also mine alt_description/description text",
    )
    parser.add_argument(
        "--llm-map",
        action="store_true",
        help="Use OpenAI to map tags->categories if OPENAI_API_KEY is set",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Ignore existing queries_manifest.json and rebuild from scratch",
    )
    args = parser.parse_args()

    photo_paths = [Path(p) for p in args.photos]
    counts = collect_tags(
        photo_paths,
        use_alt_description=args.use_alt_description,
        min_len=args.min_len,
    )

    allowed_tokens = build_vocab(counts, min_count=args.min_count)

    if args.llm_map:
        tag_to_categories = llm_map_tags_to_categories(allowed_tokens, args.categories)
    else:
        tag_to_categories = heuristic_tag_to_categories(allowed_tokens, args.categories)

    out_path = Path(args.out)
    merged = merge_existing(out_path, allowed_tokens, tag_to_categories, fresh=args.fresh)

    total_tags = sum(counts.values())
    print(
        f"[build_manifest] raw_unique_tags={len(counts)} "
        f"kept_allowed={len(allowed_tokens)} total_seen={total_tags}"
    )
    print(f"[build_manifest] categories={args.categories}")

    out_path.write_text(json.dumps(merged, indent=2))
    print(f"[build_manifest] wrote {out_path.resolve()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
