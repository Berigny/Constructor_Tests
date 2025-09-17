from __future__ import annotations

from pathlib import Path
import hashlib
from typing import List, Tuple

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def _folder_hash(paths: List[Path]) -> str:
    """Hash filenames and modification times to invalidate caches when needed."""
    h = hashlib.md5()
    for p in sorted(paths):
        h.update(p.name.encode("utf-8"))
        try:
            h.update(str(p.stat().st_mtime_ns).encode("utf-8"))
        except Exception:
            # If we can't stat the file, skip the timestamp but keep the name
            continue
    return h.hexdigest()


def discover_images(root: str = "unsplash_images") -> Tuple[List[Path], str]:
    """Return all supported image paths beneath ``root`` and a cache signature."""
    folder = Path(root)
    if not folder.exists():
        return [], ""
    files = [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED]
    return files, _folder_hash(files)
