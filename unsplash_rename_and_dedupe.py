import os
import json
import argparse
from typing import List, Dict


def expected_filename(entry: Dict) -> str:
    try:
        idx = int(entry.get("image_number", 0))
    except Exception:
        idx = 0
    q = str(entry.get("query", "")).replace(" ", "_")
    return f"{idx:02d}_{q}.jpg"


def main() -> None:
    ap = argparse.ArgumentParser(description="Rename Unsplash images to <photo_id>.jpg and remove duplicates")
    ap.add_argument("--dir", default="unsplash_images", help="Directory containing images and metadata.json")
    ap.add_argument("--dry-run", action="store_true", help="Show actions without modifying files")
    args = ap.parse_args()

    base = args.dir
    meta_path = os.path.join(base, "metadata.json")
    if not os.path.exists(meta_path):
        print(f"metadata.json not found in {base}")
        return

    try:
        data: List[Dict] = json.loads(open(meta_path, "r", encoding="utf-8").read())
        if not isinstance(data, list):
            raise ValueError("metadata.json root is not a list")
    except Exception as e:
        print(f"Failed to read metadata: {e}")
        return

    seen_ids = set()
    kept: List[Dict] = []
    for entry in data:
        pid = str(entry.get("photo_id", "")).strip()
        if not pid or pid == "N/A":
            # skip entries without a valid id
            continue
        cur_name = expected_filename(entry)
        cur_path = os.path.join(base, cur_name)
        new_name = f"{pid}.jpg"
        new_path = os.path.join(base, new_name)

        # If we've already kept this id, drop this duplicate and remove its file (if it exists)
        if pid in seen_ids or (os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(cur_path)):
            if os.path.exists(cur_path) and not args.dry_run:
                try:
                    os.remove(cur_path)
                    print(f"Removed duplicate image: {cur_name}")
                except Exception as e:
                    print(f"Failed to remove {cur_name}: {e}")
            # do not add to kept
            continue

        # Ensure current file exists; if not, try to locate a file with same id already
        if not os.path.exists(cur_path):
            if os.path.exists(new_path):
                # File already correctly named from a prior run
                seen_ids.add(pid)
                entry["filename"] = new_name
                kept.append(entry)
                continue
            else:
                print(f"Missing file for entry: expected {cur_name}; skipping")
                continue

        # Rename to id-based filename if needed
        if os.path.abspath(cur_path) != os.path.abspath(new_path):
            if not args.dry_run:
                try:
                    os.rename(cur_path, new_path)
                    print(f"Renamed {cur_name} -> {new_name}")
                except Exception as e:
                    print(f"Failed to rename {cur_name} -> {new_name}: {e}")
                    continue
            else:
                print(f"Would rename {cur_name} -> {new_name}")

        seen_ids.add(pid)
        entry["filename"] = new_name
        kept.append(entry)

    # Write updated metadata without duplicates
    if not args.dry_run:
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(kept, f, indent=4)
            print(f"Updated metadata.json with {len(kept)} unique entries")
        except Exception as e:
            print(f"Failed to write metadata: {e}")
    else:
        print(f"Would update metadata.json with {len(kept)} unique entries")


if __name__ == "__main__":
    main()

