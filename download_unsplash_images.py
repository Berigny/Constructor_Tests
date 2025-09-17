import os
import json
import time
import random
import argparse
from typing import List, Dict, Tuple, Iterable, Optional, Union

import requests

# Access key must be provided by env or CLI; no insecure default
DEFAULT_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()

# Curated queries by category (based on user brief)
CURATED_CATEGORIES: Dict[str, List[str]] = {
    "Core Personality Dimensions": [
        "minimalist desk",
        "maximalist interior",
        "colorful street art",
        "black and white portrait",
        "luxury fashion",
        "thrift vintage clothing",
        "nature hiking trail",
        "city nightlife neon",
        "cozy home living room",
        "modern architecture glass",
    ],
    "Values & Orientation": [
        "family gathering dinner",
        "friends party candid",
        "solo traveler mountain",
        "volunteer helping hands",
        "yoga meditation serene",
        "sports team huddle",
        "political protest crowd",
        "business startup team",
    ],
    "Generational Markers": [
        "retro 70s living room",
        "90s cassette player",
        "early 2000s flip phone",
        "modern gaming setup RGB",
        "vinyl record collection",
        "classic car vintage",
        "TikTok selfie style",
        "Instagram cafe aesthetic",
    ],
    "Emotional / Mood Axes": [
        "serene forest fog",
        "dramatic thunderstorm lightning",
        "sunset beach calm",
        "crowded festival happy",
        "abstract chaotic art",
        "clean geometric shapes",
        "soft pastel flat lay",
        "high contrast street photography",
    ],
    "Interests & Hobbies": [
        "gourmet cooking kitchen",
        "gardening hands soil",
        "surfing ocean wave",
        "cycling outdoors urban",
        "vinyl dj turntable",
        "book reading cozy corner",
        "film camera retro",
        "gaming console setup",
        "crafts handmade pottery",
        "luxury watch closeup",
    ],
    # Contrasts become individual queries on both sides
    "Contrasts": [
        "minimalist white room",
        "maximalist colorful room",
        "mountain solitude",
        "city nightlife club",
        "calm yoga pose",
        "intense gym workout",
        "handmade pottery",
        "luxury branded handbag",
        "vintage record player",
        "modern wireless headphones",
    ],
}

# Optional collection IDs (kept for advanced usage; not used by default)
COLLECTION_IDS = {
    "Featured": "317099",
    "Wallpapers": "1065976",
    "Nature": "3330448",
    "3D Renders": "7683081",
    "Textures": "3330446",
    "Travel": "2597413",
    "Film": "2429828",
    "People": "3349876",
    "Architecture": "3348849",
    "Interiors": "3336091",
    "Street Photography": "3336097",
    "Experimental": "296",
}

# CLI options
ap = argparse.ArgumentParser(description="Download images from Unsplash for curated queries")
ap.add_argument("--access-key", default=DEFAULT_ACCESS_KEY, help="Unsplash access key (or set UNSPLASH_ACCESS_KEY)")
ap.add_argument("--out-dir", default="unsplash_images", help="Output directory for images and metadata.json")
ap.add_argument("--sleep", type=float, default=0.7, help="Sleep seconds between API calls to avoid rate limits")
ap.add_argument("--per-query", type=int, default=2, help="Number of images to fetch per query (1-30)")
ap.add_argument("--limit-queries", type=int, default=None, help="Limit number of queries processed (debug)")
ap.add_argument("--only-queries", nargs="+", default=None, help="Only download for these query strings (case-insensitive; '/' treated as space)")
ap.add_argument("--category", nargs="+", default=None, help="Restrict to one or more category names")
ap.add_argument("--australian-bias", action="store_true", help="Append 'Australia' to queries with fallback if no results")
ap.add_argument("--use-collections", action="store_true", help="Also filter by Unsplash collections (may reduce results)")
ap.add_argument("--dry-run", action="store_true", help="List planned downloads without saving images")
ap.add_argument("--shuffle", action="store_true", help="Shuffle queries to diversify results")
args = ap.parse_args()

def _norm(s: str) -> str:
    return " ".join(str(s).replace("/", " ").split()).lower().strip()


def iter_curated_queries(category_filter: Optional[List[str]] = None) -> Iterable[Tuple[str, str]]:
    cats = CURATED_CATEGORIES
    if category_filter:
        keep = set([c.lower() for c in category_filter])
        cats = {k: v for k, v in cats.items() if k.lower() in keep}
    for cat, items in cats.items():
        for q in items:
            yield cat, q


def build_effective_query(q: str, australian_bias: bool) -> Tuple[str, Optional[str]]:
    if not australian_bias:
        return q, None
    biased = f"{q} Australia"
    return biased, q  # primary, fallback


def unsplash_random(
    access_key: str,
    query: str,
    count: int = 1,
    collections: Optional[str] = None,
    timeout: int = 30,
    retries: int = 2,
) -> Union[List[dict], dict, None]:
    url = "https://api.unsplash.com/photos/random"
    params = {"client_id": access_key, "query": query, "count": max(1, min(30, int(count)))}
    if collections:
        params["collections"] = collections
    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            last_err = (resp.status_code, resp.text)
        except Exception as e:
            last_err = ("exception", str(e))
        time.sleep(0.5 + attempt * 0.7)
    print(f"Unsplash random failed for '{query}' ({count}): {last_err}")
    return None


def ensure_out_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_image(url: str, dest_path: str, timeout: int = 60) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            if os.path.exists(dest_path):
                return True
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
        print(f"Download HTTP {r.status_code} for {url}")
        return False
    except Exception as e:
        print(f"Download error for {url}: {e}")
        return False


def load_existing_metadata(metadata_file: str) -> List[dict]:
    if os.path.exists(metadata_file):
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def merge_metadata(existing: List[dict], new_items: List[dict]) -> List[dict]:
    by_id: Dict[str, dict] = {}
    for r in existing:
        pid = str(r.get("photo_id") or r.get("id") or "").strip()
        if pid:
            by_id[pid] = r
        else:
            fn = str(r.get("filename") or "").strip()
            if fn:
                by_id[os.path.splitext(fn)[0]] = r
    for r in new_items:
        pid = str(r.get("photo_id") or r.get("id") or "").strip()
        if not pid:
            fn = str(r.get("filename") or "").strip()
            pid = os.path.splitext(fn)[0] if fn else ""
        if pid and pid in by_id:
            dest = by_id[pid]
            for k, v in r.items():
                if k not in dest or (dest.get(k) in (None, "", []) and v not in (None, "", [])):
                    dest[k] = v
        else:
            existing.append(r)
            if pid:
                by_id[pid] = r
    return existing


def main() -> None:
    access_key = args.access_key.strip()
    if not access_key:
        raise SystemExit("Missing Unsplash access key. Set --access-key or UNSPLASH_ACCESS_KEY.")

    out_dir = args.out_dir
    ensure_out_dir(out_dir)
    metadata_file = os.path.join(out_dir, "metadata.json")

    # Prepare query list
    items: List[Tuple[str, str]] = list(iter_curated_queries(args.category))
    if args.only_queries:
        wanted = set(_norm(q) for q in args.only_queries)
        items = [(cat, q) for (cat, q) in items if _norm(q) in wanted]
    if args.shuffle:
        random.shuffle(items)
    if args.limit_queries is not None:
        items = items[: max(0, int(args.limit_queries))]

    seen_ids: set = set()
    all_metadata: List[dict] = []

    if not items:
        print("No queries to process after filters.")
        return

    # Save a manifest of queries and categories for traceability
    manifest = {
        "categories": {k: v for k, v in CURATED_CATEGORIES.items() if (not args.category or k in args.category)},
        "australian_bias": args.australian_bias,
        "per_query": args.per_query,
        "timestamp": int(time.time()),
    }
    with open(os.path.join(out_dir, "queries_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Iterate queries and fetch images
    for idx, (category, query) in enumerate(items, start=1):
        primary_q, fallback_q = build_effective_query(query, args.australian_bias)
        collections = None
        if args.use_collections:
            # Try to map coarse category to a collection (best-effort)
            if category in ("Core Personality Dimensions", "Values & Orientation", "Interests & Hobbies"):
                collections = COLLECTION_IDS.get("People")
            elif category in ("Emotional / Mood Axes", "Contrasts"):
                collections = None  # too broad; skip
            elif category == "Generational Markers":
                collections = COLLECTION_IDS.get("Film")

        # First try: biased query
        data = unsplash_random(access_key, primary_q, count=args.per_query, collections=collections)
        # Fallback to non-biased if needed
        if not data and fallback_q:
            data = unsplash_random(access_key, fallback_q, count=args.per_query, collections=collections)

        if not data:
            print(f"No data for query '{query}' (category: {category})")
            time.sleep(args.sleep)
            continue

        photos = data if isinstance(data, list) else [data]
        saved_any = False
        for ph in photos:
            photo_id = ph.get("id")
            if not photo_id or photo_id in seen_ids:
                continue
            seen_ids.add(photo_id)

            img_url = ph.get("urls", {}).get("regular") or ph.get("urls", {}).get("full")
            if not img_url:
                continue

            meta = {
                "sequence": idx,
                "category": category,
                "query": query,
                "biased_query": primary_q if args.australian_bias else None,
                "photo_id": photo_id,
                "description": ph.get("description") or "",
                "alt_description": ph.get("alt_description") or "",
                "photographer": (ph.get("user") or {}).get("name") or "",
                "tags": [t.get("title") for t in (ph.get("tags") or []) if isinstance(t, dict) and t.get("title")],
                "width": ph.get("width"),
                "height": ph.get("height"),
                "filename": f"{photo_id}.jpg",
                "links": ph.get("links"),
            }

            if args.dry_run:
                print(f"[DRY-RUN] {category} | {query} -> {photo_id}")
                all_metadata.append(meta)
                saved_any = True
                continue

            dest = os.path.join(out_dir, meta["filename"])
            if save_image(img_url, dest):
                print(f"Saved {dest}  ({category} / {query})")
                all_metadata.append(meta)
                saved_any = True
            else:
                print(f"Failed to save {meta['filename']} for query '{query}'")

            # Be nice to API
            time.sleep(0.2)

        if not saved_any:
            print(f"No photos saved for '{query}'")

        # Rate limiting buffer between query batches
        time.sleep(args.sleep)

    # Merge with existing metadata.json (non-destructive)
    existing = load_existing_metadata(metadata_file)
    merged = merge_metadata(existing, all_metadata)
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4)
    print(f"Saved metadata to {metadata_file} (merged {len(all_metadata)} new, total {len(merged)})")


if __name__ == "__main__":
    main()

"""
Legacy note: previous CLI supported --limit and query/collection pairs.
The new version focuses on curated queries and per-query counts.
"""
