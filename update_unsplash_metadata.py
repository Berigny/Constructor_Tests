import os
import json
import time
import argparse
from typing import Dict, List

import requests


def load_json(path: str) -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def save_json(path: str, rows: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=4)


def scan_photo_ids(img_dir: str) -> List[str]:
    ids = []
    for name in os.listdir(img_dir):
        if name.lower().endswith(".jpg"):
            ids.append(os.path.splitext(name)[0])
    return sorted(list(dict.fromkeys(ids)))


def main() -> None:
    ap = argparse.ArgumentParser(description="Update local Unsplash metadata (alt_description + tags) for existing JPGs")
    ap.add_argument("--dir", default="unsplash_images", help="Directory containing JPGs and metadata.json")
    ap.add_argument("--limit", type=int, default=None, help="Max photos to update (default: all)")
    ap.add_argument("--sleep", type=float, default=1.0, help="Sleep seconds between API calls (respect rate limits)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing alt_description/tags if present")
    args = ap.parse_args()

    img_dir = args.dir
    meta_path = os.path.join(img_dir, "metadata.json")

    # resolve access key
    access_key = os.environ.get("UNSPLASH_ACCESS_KEY")
    if not access_key:
        # streamlit secrets are not accessible here; rely on env
        print("UNSPLASH_ACCESS_KEY not set in environment.")
        return

    rows = load_json(meta_path)
    by_id: Dict[str, Dict] = {}
    for r in rows:
        pid = str(r.get("photo_id") or r.get("id") or "").strip()
        if pid:
            by_id[pid] = r

    ids = scan_photo_ids(img_dir)
    if args.limit is not None:
        ids = ids[: args.limit]

    updated = 0
    created = 0
    skipped = 0

    for pid in ids:
        # decide whether to fetch
        existing = by_id.get(pid)
        if existing and not args.overwrite:
            # skip if we already have alt/tags
            if existing.get("alt_description") or existing.get("tags"):
                skipped += 1
                continue
        try:
            url = f"https://api.unsplash.com/photos/{pid}"
            resp = requests.get(url, params={"client_id": access_key}, timeout=10)
            if resp.status_code != 200:
                print(f"[WARN] {pid}: {resp.status_code} {resp.text[:120]}")
                time.sleep(args.sleep)
                continue
            j = resp.json()
            alt = j.get("alt_description") or j.get("description") or ""
            tags = [t.get("title") for t in (j.get("tags") or []) if isinstance(t, dict) and t.get("title")]
            width = j.get("width")
            height = j.get("height")
            photographer = (j.get("user") or {}).get("name")
            if existing:
                existing["photo_id"] = pid
                existing["alt_description"] = alt
                existing["tags"] = tags
                if width: existing["width"] = width
                if height: existing["height"] = height
                if photographer: existing["photographer"] = photographer
                existing.setdefault("filename", f"{pid}.jpg")
                updated += 1
            else:
                row = {
                    "photo_id": pid,
                    "alt_description": alt,
                    "tags": tags,
                    "width": width,
                    "height": height,
                    "photographer": photographer,
                    "filename": f"{pid}.jpg",
                }
                rows.append(row)
                by_id[pid] = row
                created += 1
            time.sleep(args.sleep)
        except Exception as e:
            print(f"[ERROR] {pid}: {e}")
            time.sleep(args.sleep)

    save_json(meta_path, rows)
    print(f"Done. Updated: {updated}, Created: {created}, Skipped: {skipped}, Total rows: {len(rows)}")


if __name__ == "__main__":
    main()

