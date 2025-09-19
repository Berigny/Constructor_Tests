import os
import json
import uuid
import re
import html
import hashlib
import mimetypes
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from urllib.parse import urljoin, urlencode
from datetime import datetime
import csv
import numpy as np
import base64
import random
import streamlit as st

from src.image_loader import SUPPORTED, discover_images
from src.query_builder import QueryBuilder
from src.query_interpreter import QueryInterpreter
from src.query_composer import (
    sanitize_query,
    top_tags_from_rows,
)
from src.constructor_url import build_constructor_url, DEFAULT_PREFILTER_NOT


# ----------------------- Minimal .env loader -----------------------
def _load_env_from_file(path: str) -> None:
    try:
        if not os.path.exists(path):
            return
        with open(path, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                key = k.strip()
                val = v.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


_load_env_from_file(".env.local")
_load_env_from_file(".env")


# ----------------------- Query builder cache -----------------------
_QUERY_BUILDER: Optional[QueryBuilder] = None
_QUERY_BUILDER_MTIME: Optional[float] = None
_QUERY_INTERPRETER: Optional[QueryInterpreter] = None
_QUERY_INTERPRETER_SIGNATURE: Optional[Tuple[Optional[float], Optional[float]]] = None


def get_query_builder(manifest_path: str = "queries_manifest.json") -> QueryBuilder:
    """Return a cached ``QueryBuilder``, reloading if the manifest changes."""

    global _QUERY_BUILDER, _QUERY_BUILDER_MTIME
    path = Path(manifest_path)
    mtime: Optional[float] = None
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        pass
    if _QUERY_BUILDER is None or _QUERY_BUILDER_MTIME != mtime:
        _QUERY_BUILDER = QueryBuilder(manifest_path)
        _QUERY_BUILDER_MTIME = mtime
    return _QUERY_BUILDER


def get_query_interpreter(
    manifest_path: str = "queries_manifest.json",
    metadata_path: str = "unsplash_images/metadata.json",
) -> QueryInterpreter:
    """Return a cached ``QueryInterpreter`` with simple file-change detection."""

    global _QUERY_INTERPRETER, _QUERY_INTERPRETER_SIGNATURE
    manifest_mtime: Optional[float] = None
    metadata_mtime: Optional[float] = None
    try:
        manifest_mtime = Path(manifest_path).stat().st_mtime
    except FileNotFoundError:
        manifest_mtime = None
    try:
        metadata_mtime = Path(metadata_path).stat().st_mtime
    except FileNotFoundError:
        metadata_mtime = None

    signature = (manifest_mtime, metadata_mtime)
    if _QUERY_INTERPRETER is None or _QUERY_INTERPRETER_SIGNATURE != signature:
        _QUERY_INTERPRETER = QueryInterpreter(
            manifest_path=manifest_path,
            metadata_path=metadata_path,
        )
        _QUERY_INTERPRETER_SIGNATURE = signature
    return _QUERY_INTERPRETER


# ----------------------- Quiz loading -----------------------
@st.cache_data
def load_quiz(path: str = "QuizIA.json") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ----------------------- Helper parsing utils -----------------------
def parse_budget_range(label: str) -> Tuple[Optional[float], Optional[float]]:
    s = label.strip().lower()
    # Handle patterns like: under_$10, $10-$20, $20-$50, over_$50
    if "under" in s:
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if m:
            return (None, float(m.group(1)))
    if "over" in s:
        m = re.search(r"(\d+(?:\.\d+)?)", s)
        if m:
            return (float(m.group(1)), None)
    # Range
    m = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (min(a, b), max(a, b))
    # Single number fallback
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        x = float(m.group(1))
        return (0.8 * x, 1.2 * x)
    return (None, None)


def price_filter_value(lo: Optional[float], hi: Optional[float]) -> Optional[str]:
    if lo is None and hi is None:
        return None
    l = int(lo) if lo is not None else 0
    if hi is None:
        return f"{l}-inf"
    return f"{l}-{int(hi)}"


def price_text(lo: Optional[float], hi: Optional[float]) -> Optional[str]:
    if lo is None and hi is None:
        return None
    if lo is None and hi is not None:
        return f"under ${int(hi)}"
    if lo is not None and hi is None:
        return f"over ${int(lo)}"
    return f"${int(lo)}–${int(hi)}"


def neighbor_price_bands(lo: Optional[float], hi: Optional[float]) -> List[Tuple[Optional[float], Optional[float]]]:
    """Return up to two nearby price bands to try if none in range.
    Uses simple step heuristics to approximate nearest constructor buckets.
    """
    bands: List[Tuple[Optional[float], Optional[float]]] = []
    # Choose step size
    base = 0
    if lo is not None and hi is not None:
        base = int(abs(hi - lo))
    elif hi is not None:
        base = int(hi)
    elif lo is not None:
        base = int(lo)
    step = 5
    if base > 30:
        step = 10
    if base > 100:
        step = 20
    if base > 250:
        step = 50
    # Build neighbors
    if lo is not None and hi is not None:
        bands.append((max(0, lo - step), hi))
        bands.append((lo, hi + step))
    elif hi is not None:
        bands.append((None, max(1, hi - step)))
        bands.append((None, hi + step))
    elif lo is not None:
        bands.append((max(0, lo - step), None))
        bands.append((lo + step, None))
    return bands[:2]


def any_in_budget(items: List[Dict[str, Any]], lo: Optional[float], hi: Optional[float]) -> bool:
    for it in items:
        price = it.get("price")
        if price is None:
            continue
        if (lo is None or price >= lo) and (hi is None or price <= hi):
            return True
    return False


# Common runner to fetch products; stores outputs in session_state
def run_product_search(q_base: str, include_cats: List[str], lo: Optional[float], hi: Optional[float], label: str) -> None:
    pf = price_filter_value(lo, hi)
    urls_used: List[str] = []
    errors: List[str] = []
    chosen: List[Dict[str, Any]] = []
    try:
        if match_type == "Constructor":
            items_raw, urls1 = fetch_aggregate_items(base_url, q_base, api_key, pf, include_cats, per_page=max(per_page, gifts_opt), pages=1)
            urls_used.extend(urls1)
            items = normalise_items(items_raw, source_band="original")
            if not any_in_budget(items, lo, hi) and (lo is not None or hi is not None):
                expanded_items: List[Dict[str, Any]] = []
                msgs = []
                for (nlo, nhi) in neighbor_price_bands(lo, hi):
                    npf = price_filter_value(nlo, nhi)
                    if npf == pf:
                        continue
                    raw2, urls2 = fetch_aggregate_items(base_url, q_base, api_key, npf, include_cats, per_page=max(per_page, gifts_opt), pages=1)
                    urls_used.extend(urls2)
                    expanded_items.extend(normalise_items(raw2, source_band="expanded"))
                    msgs.append(price_text(nlo, nhi) or "")
                if expanded_items:
                    items = expanded_items
                    try:
                        st.toast(f"Expanded price to nearby bands: {', '.join([m for m in msgs if m])}")
                    except Exception:
                        pass
            chosen = items[:gifts_opt]
        else:
            # Powered-up alternating convergent/divergent
            all_items: List[Dict[str, Any]] = []
            q_base_local = q_base
            last_best = None
            for iter_idx in range(1, queries_opt + 1):
                if iter_idx == 1:
                    q_iter = q_base_local
                elif iter_idx % 2 == 0:
                    q_iter = divergent_variant(q_base_local, q_base_local, include_cats, price_text(lo, hi))
                else:
                    q_iter = refine_query(q_base_local, last_best) if last_best else q_base_local
                raw, urls2 = fetch_aggregate_items(base_url, q_iter, api_key, pf, include_cats, per_page=per_page, pages=pages_per_iter)
                urls_used.extend(urls2)
                # dedupe and normalise
                seen_local = set()
                uniq_raw = []
                for it in raw:
                    pid = it.get("id") or (it.get("data") or {}).get("id") or it.get("url")
                    pid = str(pid)
                    if pid and pid not in seen_local:
                        seen_local.add(pid)
                        uniq_raw.append(it)
                items = normalise_items(uniq_raw, source_band="original")
                if not any_in_budget(items, lo, hi) and (lo is not None or hi is not None):
                    for (nlo, nhi) in neighbor_price_bands(lo, hi):
                        npf = price_filter_value(nlo, nhi)
                        raw2, urls3 = fetch_aggregate_items(base_url, q_iter, api_key, npf, include_cats, per_page=per_page, pages=pages_per_iter)
                        urls_used.extend(urls3)
                        items.extend(normalise_items(raw2, source_band="expanded"))
                    try:
                        txts = [price_text(*b) for b in neighbor_price_bands(lo, hi)]
                        st.toast(f"Expanded price to nearby bands: {', '.join([t for t in txts if t])}")
                    except Exception:
                        pass
                all_items.extend(items)
                if items:
                    best = sorted(items, key=lambda it: score_item(it, q_base_local, lo, hi), reverse=True)[0]
                    last_best = best
            ranked = sorted(all_items, key=lambda it: score_item(it, q_base_local, lo, hi), reverse=True)
            seen_ids_global = set()
            for it in ranked:
                pid = it.get("id") or it.get("url")
                if pid and pid not in seen_ids_global and it.get("url"):
                    chosen.append(it)
                    seen_ids_global.add(pid)
                if len(chosen) >= gifts_opt:
                    break
    except Exception as e:
        errors.append(str(e))

    # Store for common rendering
    st.session_state["last_results"] = chosen
    st.session_state["last_errors"] = errors
    st.session_state["last_urls"] = urls_used
    st.session_state["last_label"] = label
    st.session_state["last_budget"] = (lo, hi)


# ----------------------- Images Tab (Greedy Tree) -----------------------
@st.cache_data
def load_meta_df(meta_path: str, folder_sig: str = "") -> Optional[Any]:
    try:
        import pandas as pd  # local import to avoid global dependency if unused
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return None
        df = pd.DataFrame(data)
        # ensure columns
        if "tags" in df.columns:
            df["tags"] = df["tags"].apply(lambda x: x if isinstance(x, list) else [])
        else:
            df["tags"] = [[] for _ in range(len(df))]
        for c in ["alt_description", "description"]:
            if c not in df.columns:
                df[c] = ""
        # normalise photo_id from possible fields
        if "photo_id" not in df.columns:
            if "id" in df.columns:
                df["photo_id"] = df["id"].astype(str)
            elif "filename" in df.columns:
                df["photo_id"] = df["filename"].astype(str).str.replace(".jpg", "", regex=False)
            else:
                df["photo_id"] = ""
        # If no usable photo_id exists in metadata, fall back to local images in the same folder
        if (df.get("photo_id") is not None) and df["photo_id"].astype(str).str.strip().eq("").all():
            base_dir = os.path.dirname(meta_path)
            try:
                discovered, _ = discover_images(base_dir or ".")
            except Exception:
                discovered = []
            if discovered:
                base_path = Path(base_dir or ".").resolve()
                rel_files = []
                pids = []
                for path in discovered:
                    try:
                        rel = str(path.resolve().relative_to(base_path))
                    except Exception:
                        rel = path.name
                    rel_files.append(rel)
                    pids.append(path.stem)
                df = pd.DataFrame({
                    "photo_id": pids,
                    "filename": rel_files,
                    "alt_description": pids,
                    "tags": [[]] * len(pids),
                })
        df["text"] = (
            df["alt_description"].fillna("").astype(str)
            + " "
            + df["tags"].apply(lambda lst: " ".join([str(t) for t in lst]))
        ).str.lower()
        return df
    except Exception:
        return None


@st.cache_data
def embed_texts(texts: List[str]) -> np.ndarray:
    # Try OpenAI embeddings, else TF-IDF
    try:
        from openai import OpenAI  # type: ignore
        api = os.environ.get("OPENAI_API_KEY")
        if api:
            client = OpenAI()
            # chunk to respect token limits as needed
            resp = client.embeddings.create(input=texts, model="text-embedding-3-small")
            vecs = [r.embedding for r in resp.data]
            return np.array(vecs, dtype=float)
    except Exception:
        pass
    # Fallback: TF-IDF vectors
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
        vec = TfidfVectorizer(max_features=2048)
        m = vec.fit_transform(texts)
        return m.toarray().astype(float)
    except Exception:
        # last resort: zeros
        return np.zeros((len(texts), 16), dtype=float)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if b.ndim == 1:
        b = b.reshape(1, -1)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a.dot(b.T) / (na * nb))


def build_greedy_tree(leaf_ids: List[int], embeddings: np.ndarray, seed: Optional[int] = None) -> Any:
    n = len(leaf_ids)
    if n == 0:
        return None
    if n == 1:
        return leaf_ids[0]
    if n == 2:
        a, b = leaf_ids[0], leaf_ids[1]
        return {"left": a, "right": b, "pair_idx": (a, b)}
    order = list(leaf_ids)
    if seed is not None:
        rnd = random.Random(seed)
        rnd.shuffle(order)
    best_pair = None
    best_balance = None
    for i in order:  # consider pivots drawn from current pool (shuffled if seed)
        for j in order:
            if j <= i:
                continue
            left, right = [], []
            for lid in leaf_ids:
                v = embeddings[lid]
                si = cosine(v, embeddings[i])
                sj = cosine(v, embeddings[j])
                (left if si > sj else right).append(lid)
            balance = abs(len(left) - len(right))
            if best_pair is None or balance < best_balance:
                best_pair = (i, j, left, right)
                best_balance = balance
                if balance == 0:
                    break
        if best_pair is not None and best_balance == 0:
            break
    if not best_pair:
        # Fallback even split
        mid_left = leaf_ids[::2]
        mid_right = leaf_ids[1::2]
        return {"left": build_greedy_tree(mid_left, embeddings, seed), "right": build_greedy_tree(mid_right, embeddings, seed), "pair_idx": (mid_left[0], mid_right[0])}
    i, j, left, right = best_pair
    # Guard against degenerate splits
    if len(left) == 0 or len(right) == 0 or (len(left) == n or len(right) == n):
        mid_left = leaf_ids[::2]
        mid_right = leaf_ids[1::2]
        return {"left": build_greedy_tree(mid_left, embeddings, seed), "right": build_greedy_tree(mid_right, embeddings, seed), "pair_idx": (mid_left[0], mid_right[0])}
    return {"left": build_greedy_tree(left, embeddings, seed), "right": build_greedy_tree(right, embeddings, seed), "pair_idx": (i, j)}


def walk_tree(tree: Any, bits: List[int]) -> Any:
    node = tree
    for b in bits:
        node = node["left"] if b == 0 else node["right"]
    return node


def node_size(node: Any) -> int:
    if node is None:
        return 0
    if isinstance(node, dict):
        return node_size(node.get("left")) + node_size(node.get("right"))
    return 1


def collect_selected_indices(tree: Any, bits: List[int]) -> List[int]:
    selected: List[int] = []
    node = tree
    for b in bits:
        if not isinstance(node, dict):
            break
        pair = node.get("pair_idx") or (None, None)
        if pair[0] is None or pair[1] is None:
            break
        chosen = pair[0] if b == 0 else pair[1]
        selected.append(chosen)
        node = node["left"] if b == 0 else node["right"]
    if isinstance(node, int):
        selected.append(node)
    seen: set[int] = set()
    ordered: List[int] = []
    for idx in selected:
        if idx not in seen:
            ordered.append(idx)
            seen.add(idx)
    return ordered


def file_to_data_uri(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            b = f.read()
        mime, _ = mimetypes.guess_type(path)
        if not mime:
            mime = "image/jpeg"
        b64 = base64.b64encode(b).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def openrouter_summarise_phrase(description: str, tags: List[str]) -> Optional[str]:
    if not st.session_state.get("llm_enabled"):
        return None
    key = os.environ.get("OPENROUTER_API_KEY")
    base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    if not key:
        return None
    try:
        import requests as _rq
        prompt = (
            "Based on the image metadata below, produce a very short natural language shopping phrase (max 10 words) "
            "describing product domain and audience, similar to 'tech and gadgets for men' or 'gardening and plant products for women'. "
            "Avoid the word 'gift'.\n\n"
            f"alt_description: {description}\n"
            f"tags: {', '.join(tags) if tags else ''}\n"
        )
        data = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        resp = _rq.post(f"{base}/chat/completions", json=data, headers=headers, timeout=20)
        resp.raise_for_status()
        txt = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return txt or None
    except Exception:
        return None


def openrouter_summarise_dataset(df_meta: Any, max_tags: int = 50, max_examples: int = 20) -> Optional[str]:
    if not st.session_state.get("llm_enabled"):
        return None
    key = os.environ.get("OPENROUTER_API_KEY")
    base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    if not key:
        return None
    try:
        import requests as _rq
        # Aggregate top tags and sample alt descriptions
        tags_all: List[str] = []
        alts: List[str] = []
        if hasattr(df_meta, 'iterrows'):
            for _, r in df_meta.iterrows():
                ts = r.get('tags')
                if isinstance(ts, list):
                    tags_all.extend([str(t) for t in ts if t])
                a = r.get('alt_description')
                if isinstance(a, str) and a.strip():
                    alts.append(a.strip())
        # Top-N tags by frequency
        freq: Dict[str,int] = {}
        for t in tags_all:
            k = str(t).lower()
            freq[k] = freq.get(k, 0) + 1
        top_tags = [t for t,_ in sorted(freq.items(), key=lambda kv: kv[1], reverse=True)][:max_tags]
        alt_samples = alts[:max_examples]

        prompt = (
            "You are crafting a very short natural-language shopping phrase (max 10 words) that describes a product domain and audience, "
            "in the style of 'tech and gadgets for men' or 'gardening and plant products for women'. Do not include the word 'gift'.\n\n"
            f"Top tags: {', '.join(top_tags)}\n"
            f"Alt examples: {' | '.join(alt_samples)}\n\n"
            "Return ONLY the phrase."
        )
        data = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        resp = _rq.post(f"{base}/chat/completions", json=data, headers=headers, timeout=20)
        resp.raise_for_status()
        txt = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return txt or None
    except Exception:
        return None


def _is_id_like(s: str, pid: Optional[str]) -> bool:
    if not s:
        return False
    t = s.strip().lower()
    if pid and t == str(pid).strip().lower():
        return True
    # Unsplash-style id: compact, no spaces, 8-16+ chars
    if " " not in t and 8 <= len(t) <= 24 and re.fullmatch(r"[a-z0-9_-]+", t):
        return True
    return False


def concept_from_meta(alt_text: str, tags: List[str], pid: Optional[str]) -> str:
    # Prefer alt_text if it's meaningful and not id-like
    if alt_text and not _is_id_like(alt_text, pid):
        return alt_text.strip()
    # Fall back to tag-driven phrases
    tag_line = " ".join([str(t) for t in tags]) if tags else ""
    t = tag_line.lower()
    mapping = [
        ("dog", "dog accessories"),
        ("cat", "cat accessories"),
        ("fish", "aquarium products"),
        ("aquarium", "aquarium products"),
        ("plush", "soft toys and plush"),
        ("toy", "toys"),
        ("sneaker", "sneakers and footwear"),
        ("shoe", "footwear"),
        ("garden", "gardening and plant products"),
        ("plant", "gardening and plant products"),
        ("tech", "tech and gadgets"),
        ("gadget", "tech and gadgets"),
    ]
    for k, v in mapping:
        if k in t:
            return v
    return "popular products"


def prettify_token(s: str) -> str:
    s = s.replace("_", " ").replace("&", "and")
    return s


def normalize_public_key(raw: str) -> str:
    """Accept either the bare key value or a snippet like 'key=XYZ&i=...'.
    Returns just the key token (e.g., 'key_ABC123')."""
    raw = (raw or "").strip().strip('"').strip("'")
    m = re.search(r"(?:^|[?&])key=([^&\s]+)", raw)
    if m:
        return m.group(1)
    return raw


# ----------------------- Constructor API helpers -----------------------
POSSIBLE_LIST_KEYS = ["results", "items", "data", "products", "records"]


def extract_items(json_obj: Any) -> List[Dict[str, Any]]:
    if isinstance(json_obj, list):
        return json_obj
    if isinstance(json_obj, dict):
        for k in POSSIBLE_LIST_KEYS:
            if k in json_obj and isinstance(json_obj[k], list):
                return json_obj[k]
        resp = json_obj.get("response") if isinstance(json_obj, dict) else None
        if isinstance(resp, dict):
            res = resp.get("results")
            if isinstance(res, list):
                return res
            if isinstance(res, dict):
                combined: List[Dict[str, Any]] = []
                for v in res.values():
                    if isinstance(v, list):
                        combined.extend(v)
                if combined:
                    return combined
            items = resp.get("items")
            if isinstance(items, list):
                return items
    return []


def get_first(d: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def normalise_price(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        s = re.sub(r"[^\d\.\-]", "", str(x))
        return float(s) if s else None
    except Exception:
        return None


def normalise_item(d: Dict[str, Any]) -> Dict[str, Any]:
    base = d.get("data") if isinstance(d, dict) else None
    base = base if isinstance(base, dict) else d
    pid = get_first(base, ["id", "product_id", "sku", "uid"]) or get_first(d, ["id", "product_id", "sku", "uid"])  # type: ignore
    title = get_first(base, ["title", "name", "product_title", "productName"]) or get_first(d, ["title", "name"])  # type: ignore
    price_raw = (
        get_first(base, ["price", "sale_price", "amount", "price_value", "final_price"]) or
        get_first(d, ["price", "sale_price", "amount"])
    )
    url = get_first(base, ["url", "product_url", "link", "permalink", "canonical_url"]) or get_first(d, ["url", "product_url"])  # type: ignore
    cat = get_first(base, ["category", "categories"], [])
    tags = get_first(base, ["tags", "labels"], [])
    price = normalise_price(price_raw)
    return {
        "id": pid,
        "title": title or "",
        "price": price,
        "url": url or "",
        "categories": cat,
        "tags": tags,
        "_raw": d,
    }


def normalise_items(raw_items: List[Dict[str, Any]], source_band: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in raw_items:
        n = normalise_item(it)
        n["_band"] = source_band  # 'original' or 'expanded'
        out.append(n)
    return out


def build_query_text(relationship: str, gender: Optional[str], age_text: Optional[str], interest: str, price_phrase: Optional[str] = None, generation_label: Optional[str] = None) -> str:
    # Build a very concise query like "tech and gadgets for men under $100"
    def simple_interest_phrase(raw: str) -> str:
        s = prettify_token(raw).lower().replace("&", "and")
        mapping = {
            "tech and gaming": "tech and gadgets",
            "cooking and baking": "kitchen and cooking products",
            "arts and creativity": "arts and crafts supplies",
            "board games and puzzles": "board games and puzzles",
            "relaxation and down time": "relaxation products",
            "reading": "books and reading accessories",
            "diy": "diy tools and craft supplies",
            "gardening": "gardening and plant products",
            "fashion and beauty": "fashion and beauty items",
            "music": "music gear",
            "outdoor play": "outdoor toys",
            "arts and crafts": "arts and crafts supplies",
            "stem and science kits": "stem and science kits",
            "soft toys and plush": "soft toys and plush",
        }
        for k, v in mapping.items():
            if k in s:
                return v
        if not s.endswith("products") and len(s.split()) > 1:
            s = f"{s} products"
        return s

    def simple_audience_phrase(rel: str, gen: Optional[str], gendr: Optional[str]) -> str:
        g = (gen or "").lower()
        sex = (gendr or "").lower()
        if "alpha" in g:
            base = "kids"
        elif "gen z" in g:
            base = "young adults"
        elif "millennial" in g or "gen y" in g:
            base = "adults"
        elif "gen x" in g:
            base = "older adults"
        elif "boomer" in g or "silent" in g:
            base = "older adults"
        else:
            base = rel if rel else "adults"
        if sex in ("male", "man", "men"):
            if base == "kids":
                return "boys"
            if "older" in base:
                return "older men"
            if "young" in base:
                return "young men"
            return "men"
        if sex in ("female", "woman", "women"):
            if base == "kids":
                return "girls"
            if "older" in base:
                return "older women"
            if "young" in base:
                return "young women"
            return "women"
        return base

    def simple_budget_phrase(p: Optional[str]) -> str:
        if not p:
            return ""
        s = p.lower().replace("$", "").replace("aud", "").strip()
        if "under" in s:
            m = re.search(r"(\d+)", s)
            if m:
                return f"under ${int(m.group(1))}"
        if "+" in s or "more" in s or "over" in s:
            m = re.search(r"(\d+)", s)
            if m:
                return f"more than ${int(m.group(1))}"
        m = re.search(r"(\d+)\D+(\d+)", s)
        if m:
            a, b = sorted([int(m.group(1)), int(m.group(2))])
            return f"between ${a} and ${b}"
        m = re.search(r"(\d+)", s)
        if m:
            return f"around ${int(m.group(1))}"
        return ""

    interest_phrase = simple_interest_phrase(interest)
    audience = simple_audience_phrase(relationship, generation_label, gender)
    budget_phrase = simple_budget_phrase(price_phrase)
    parts = [interest_phrase, "for", audience]
    if budget_phrase:
        parts.append(budget_phrase)
    return " ".join(parts).strip()


def divergent_variant(base_query: str, interest: str, include_cats: List[str], price_phrase: Optional[str]) -> str:
    """Produce a more creative/divergent take on the base query, while
    preserving the persona and constraints. Avoid the word 'gift'."""
    intr = prettify_token(interest)
    cats = ", ".join(dict.fromkeys(include_cats)) if include_cats else ""
    mood = (
        "Explore fresh, imaginative options that surprise and delight, "
        "still aligned to everyday Australian needs and smart savings. "
    )
    cat_line = f" Focus on motifs related to: {intr}." if intr else ""
    if cats:
        cat_line += f" Consider catalogue areas like: {cats}."
    price_line = f" Aim {price_phrase}." if price_phrase else ""
    return f"{base_query} {mood}{cat_line}{price_line}"


def build_minimal_query(relationship: str, gender: Optional[str], age_text: Optional[str], interest: str, price_phrase: Optional[str] = None) -> str:
    rel = prettify_token(relationship)
    gen = prettify_token(gender) if gender else None
    intr = prettify_token(interest)
    parts = [rel]
    if gen:
        parts.append(gen)
    if age_text:
        parts.append(age_text)
    who = " ".join(parts)
    tail = f" within {price_phrase}" if price_phrase else ""
    return f"Ideas for a {who} who enjoys {intr}{tail}."


def fetch_aggregate_items(base_url: str, q_text: str, api_key: str, pf: Optional[str], include_cats: List[str], per_page: int, pages: int) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Fetch items over several fallback strategies. Returns (items_raw, urls_used)."""
    urls_used: List[str] = []
    def _do_fetch(qt: str, cats: List[str], pricef: Optional[str]) -> List[Dict[str, Any]]:
        out_raw: List[Dict[str, Any]] = []
        for p in range(1, pages + 1):
            url = make_url(base_url, qt, api_key, pricef, cats, per_page=per_page, page=p)
            urls_used.append(url)
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            data = r.json()
            out_raw.extend(extract_items(data))
        return out_raw

    # 1) Full constraints
    try:
        raw = _do_fetch(q_text, include_cats, pf)
        if raw:
            return raw, urls_used
    except Exception:
        pass
    # 2) Drop categories
    try:
        raw = _do_fetch(q_text, [], pf)
        if raw:
            return raw, urls_used
    except Exception:
        pass
    # 3) Drop price filter
    try:
        raw = _do_fetch(q_text, [], None)
        if raw:
            return raw, urls_used
    except Exception:
        pass
    # 4) Minimal query: strip persona if present, keep core phrase
    def _simplify(qs: str) -> str:
        m = re.search(r"(Thoughtful ideas.*)$", qs)
        if m:
            return m.group(1)
        return qs
    try:
        raw = _do_fetch(_simplify(q_text), [], None)
        if raw:
            return raw, urls_used
    except Exception:
        pass
    return [], urls_used


@st.cache_data
def load_category_whitelist(categories_path: str = "categories.txt", example_path: str = "example.json") -> List[str]:
    # Union categories from categories.txt and example.json facets
    cats: List[str] = []
    try:
        if os.path.exists(categories_path):
            section = None
            with open(categories_path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line:
                        continue
                    low = line.lower()
                    if "categories:" in low:
                        section = "categories"
                        continue
                    if "product types:" in low:
                        section = "product_types"
                        continue
                    if section == "categories":
                        cats.append(line.replace("  ", " ").strip())
    except Exception:
        pass
    try:
        if os.path.exists(example_path):
            with open(example_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            facets = ((data.get("response") or {}).get("facets") or [])
            for facet in facets:
                if str(facet.get("name")).lower() == "category":
                    for opt in facet.get("options", []):
                        name = opt.get("display_name") or opt.get("value")
                        if name:
                            cats.append(str(name))
    except Exception:
        pass
    # unique preserving order
    return list(dict.fromkeys(cats))


def _norm_cat(s: str) -> str:
    s = s.lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@st.cache_data
def build_category_canonical_map() -> Dict[str, str]:
    whitelist = load_category_whitelist()
    mapping: Dict[str, str] = {}
    for cat in whitelist:
        mapping[_norm_cat(cat)] = cat
    return mapping


def interest_to_categories(interest: str, restrict_to_whitelist: bool = True) -> List[str]:
    raw = (interest or "").strip()
    t = raw.lower().replace("_", " ")
    # Explicit mapping for QuizIA interests → catalog categories
    explicit: Dict[str, List[str]] = {
        # Kids / Child
        "soft toys & plush": ["Toys", "Kids and Baby"],
        "sensory play": ["Toys", "Kids and Baby"],
        "teething & comfort": ["Kids and Baby"],
        "first books": ["Back To School", "Kids and Baby"],
        "imaginative play": ["Toys"],
        "stacking & sorting": ["Toys"],
        "building blocks": ["Toys"],
        "storytime & picture books": ["Back To School"],
        "stem & science kits": ["Toys", "Back To School"],
        "arts & crafts": ["Craft Supplies", "Artistry", "Kids Art", "Craft and Stationery"],
        "board games & puzzles": ["Toys"],
        "outdoor play": ["Toys"],
        # Adults
        "cooking & baking": ["Kitchen Appliances", "Utensils & Gadgets", "Food Preparation", "Cookware", "Bakeware", "Serveware"],
        "relaxation & down time": ["Home  Living"],
        "gardening": ["Home  Living"],
        "reading": ["Back To School"],
        "tech & gaming": ["Electronics", "Gadgets", "Tech"],
        "diy": ["Craft Supplies", "Artistry"],
        "arts & creativity": ["Artistry", "Craft Supplies"],
        "music": ["Music"],
        "fashion & beauty": ["Gifting"],
    }
    # Normalise keys for lookup
    def norm_interest(s: str) -> str:
        x = s.lower()
        x = x.replace(" and ", " & ")
        x = x.replace("&", "&")
        x = re.sub(r"\s+", " ", x).strip()
        return x
    candidates: List[str] = []
    ni = norm_interest(t)
    if ni in explicit:
        candidates.extend(explicit[ni])
    # Token-based heuristics as a fallback
    if not candidates:
        token_map = [
            ("cooking", ["Kitchen Appliances", "Utensils & Gadgets", "Food Preparation", "Cookware", "Bakeware", "Serveware"]),
            ("baking", ["Bakeware", "Kitchen Appliances", "Utensils & Gadgets"]),
            ("gardening", ["Home  Living"]),
            ("relaxation", ["Home  Living"]),
            ("reading", ["Back To School"]),
            ("tech", ["Electronics", "Gadgets", "Tech"]),
            ("gaming", ["Electronics", "Gadgets", "Tech"]),
            ("diy", ["Craft Supplies", "Artistry"]),
            ("craft", ["Craft Supplies", "Artistry", "Craft and Stationery", "Kids Art"]),
            ("board", ["Toys"]),
            ("puzzle", ["Toys"]),
            ("toy", ["Toys"]),
            ("kids", ["Kids and Baby", "Toys"]),
            ("home", ["Home  Living"]),
            ("music", ["Music"]),
        ]
        for key, cats in token_map:
            if key in ni:
                candidates.extend(cats)
    # Whitelist canonicalisation
    if restrict_to_whitelist:
        canonical = build_category_canonical_map()
        resolved: List[str] = []
        for c in candidates:
            key = _norm_cat(c)
            if key in canonical:
                resolved.append(canonical[key])
        candidates = resolved
    return list(dict.fromkeys([c for c in candidates if c]))


def ensure_constructor_ids() -> Tuple[str, str]:
    session_token = st.session_state.get("constructor_s")
    if not session_token:
        session_token = "1"
        st.session_state["constructor_s"] = session_token
    user_token = st.session_state.get("constructor_i")
    if not user_token:
        user_token = str(uuid.uuid4())
        st.session_state["constructor_i"] = user_token
    return session_token, user_token


def make_url(
    base: str,
    query: str,
    key: str,
    price_filter: Optional[str],
    include_categories: List[str],
    per_page: int = 10,
    page: int = 1,
) -> str:
    canonical = build_category_canonical_map()
    cat_filters: List[str] = []
    for cat in include_categories:
        c = canonical.get(_norm_cat(cat), cat)
        if c and c not in cat_filters:
            cat_filters.append(c)

    filters: Dict[str, str | List[str]] = {}
    if price_filter:
        filters["Price"] = price_filter
    if cat_filters:
        filters["Category"] = cat_filters if len(cat_filters) > 1 else cat_filters[0]

    session_token, user_token = ensure_constructor_ids()
    endpoint = urljoin(base, "/v1/search/natural_language/")

    return build_constructor_url(
        nl_query=sanitize_query(query),
        api_key=key,
        base_url=endpoint,
        page=page,
        per_page=per_page,
        filters=filters or None,
        prefilter_not=DEFAULT_PREFILTER_NOT,
        session=session_token,
        extra_params=[("i", user_token)],
    )


def normalize_filter_value(val: str) -> str:
    s = (val or "").strip()
    s = s.replace("&", "and")
    return s


def url_for_bucket(
    base_url: str,
    api_key: str,
    nl: str,
    bucket: str,
    recipient: str,
    budget_hi: Optional[int],
    expanded_categories: Optional[List[str]] = None,
    gender_opt: Optional[str] = None,
    per_page: int = 60,
) -> str:
    filters: Dict[str, str | List[str]] = {}
    if budget_hi is not None:
        filters["Price"] = normalize_filter_value(f"0-{int(budget_hi)}")

    bucket_map: Dict[str, List[str]] = {
        "Books": ["Books"],
        "Tech": ["Tech"],
        "Outdoors": ["Outdoors"],
        "Home": ["Home"],
        "Fashion": ["Fashion"],
        "Entertainment": ["Entertainment"],
    }

    cat_filters: List[str] = list(bucket_map.get(bucket, []))
    for cat in expanded_categories or []:
        if not cat:
            continue
        if bucket.lower() in cat.lower() and cat not in cat_filters:
            cat_filters.append(cat)

    if recipient == "couple":
        if bucket == "Home":
            extras = ["Home", "Occasion", "Jewellery"]
        elif bucket in {"Fashion", "Entertainment"}:
            extras = ["Jewellery", "Occasion"]
        else:
            extras = []
        for cat in extras:
            if cat not in cat_filters:
                cat_filters.append(cat)

    if cat_filters:
        normalized_cats = [normalize_filter_value(c) for c in cat_filters]
        if len(normalized_cats) == 1:
            filters["Category"] = normalized_cats[0]
        else:
            filters["Category"] = normalized_cats

    if gender_opt in {"Men", "Women"}:
        filters["Gender"] = gender_opt

    session_token, user_token = ensure_constructor_ids()
    endpoint = urljoin(base_url, "/v1/search/natural_language/")

    return build_constructor_url(
        nl_query=sanitize_query(nl),
        api_key=api_key,
        base_url=endpoint,
        page=1,
        per_page=per_page,
        filters=filters or None,
        prefilter_not=DEFAULT_PREFILTER_NOT,
        session=session_token,
        extra_params=[("i", user_token)],
    )


def make_url_with_pairs(
    base: str,
    query: str,
    key: str,
    per_page: int,
    page: int,
    pairs: List[Tuple[str, str]],
) -> str:
    filters: Dict[str, str | List[str]] = {}
    extra_pairs: List[Tuple[str, str]] = []
    prefilter_override: Optional[str] = None

    for raw_key, raw_val in pairs:
        key_norm = (raw_key or "").strip()
        val_norm = normalize_filter_value(raw_val)
        if not key_norm or not val_norm:
            continue
        if key_norm.startswith("filters[") and key_norm.endswith("]"):
            field = key_norm[8:-1]
            existing = filters.get(field)
            if isinstance(existing, list):
                if val_norm not in existing:
                    existing.append(val_norm)
            elif isinstance(existing, str) and existing:
                if val_norm != existing:
                    filters[field] = [existing, val_norm]
            else:
                filters[field] = val_norm
        elif key_norm == "pre_filter_expression":
            prefilter_override = val_norm
        else:
            extra_pairs.append((key_norm, val_norm))

    session_token, user_token = ensure_constructor_ids()
    endpoint = urljoin(base, "/v1/search/natural_language/")

    prefilter = DEFAULT_PREFILTER_NOT if prefilter_override is None else None
    extra = list(extra_pairs)
    extra.append(("i", user_token))
    if prefilter_override is not None:
        extra.append(("pre_filter_expression", prefilter_override))

    return build_constructor_url(
        nl_query=sanitize_query(query),
        api_key=key,
        base_url=endpoint,
        page=page,
        per_page=per_page,
        filters=filters or None,
        prefilter_not=prefilter,
        session=session_token,
        extra_params=extra,
    )


def fetch_aggregate_items_generic(base_url: str, q_text: str, api_key: str, per_page: int, pages: int, filter_pairs: List[Tuple[str, str]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    urls_used: List[str] = []
    out_raw: List[Dict[str, Any]] = []
    for p in range(1, pages + 1):
        url = make_url_with_pairs(base_url, q_text, api_key, per_page=per_page, page=p, pairs=filter_pairs)
        urls_used.append(url)
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        out_raw.extend(extract_items(data))
    return out_raw, urls_used


def refine_query(prev_query: str, picked: Dict[str, Any]) -> str:
    title = (picked.get("title") or "").strip()
    if not title:
        return prev_query
    # Extract a few meaningful tokens from the product title
    words = [w for w in re.split(r"[^a-zA-Z0-9]+", title) if len(w) > 2]
    focus = " ".join(words[:5])
    # Append guidance to anchor embeddings toward value and practicality
    return f"{prev_query} Focus on: {focus}. Prioritise practical, durable, great-value options suitable for everyday Australian use."


def constructor_search(query: str, price_filter: Optional[str], page: int, per_page: int = 10) -> Dict[str, Any]:
    base = os.environ.get("CONSTRUCTOR_BASE_URL", "https://ac.cnstrc.com")
    key = os.environ.get("CONSTRUCTOR_API_KEY") or os.environ.get("CONSTRUCTOR_KEY") or os.environ.get("CONSTRUCTOR_PUBLIC_KEY")
    if not key:
        raise ValueError("Set CONSTRUCTOR_API_KEY (or CONSTRUCTOR_KEY/CONSTRUCTOR_PUBLIC_KEY) in env or via the sidebar.")
    session_token, user_token = ensure_constructor_ids()
    endpoint = urljoin(base, "/v1/search/natural_language/")

    filters: Dict[str, str] = {}
    if price_filter:
        filters["Price"] = price_filter

    url = build_constructor_url(
        nl_query=sanitize_query(query),
        api_key=key,
        base_url=endpoint,
        page=page,
        per_page=per_page,
        filters=filters or None,
        prefilter_not=DEFAULT_PREFILTER_NOT,
        session=session_token,
        extra_params=[("i", user_token)],
    )

    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def score_item(item: Dict[str, Any], interest: str, lo: Optional[float], hi: Optional[float]) -> float:
    title = (item.get("title") or "").lower()
    tokens = [t for t in re.split(r"[^a-z0-9]+", prettify_token(interest).lower()) if t]
    score = 0.0
    for t in tokens:
        if t and t in title:
            score += 1.0
    price = item.get("price")
    # reward being in budget, penalize if outside
    if price is not None:
        in_budget = True
        if lo is not None and price < lo:
            in_budget = False
        if hi is not None and price > hi:
            in_budget = False
        score += 1.0 if in_budget else -0.5
    return score


# ----------------------- UI -----------------------
st.set_page_config(page_title="Gift Finder", page_icon="🎁", layout="centered")
st.markdown(
    """
    <style>
    div[data-testid="stMarkdownContainer"]:has(> div[data-image-box]) {
        margin: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Gift Finder")
st.caption("Choose match mode and amounts, then select recipient details.")

quiz = load_quiz()

with st.sidebar:
    st.header("Settings")
    # PIN-gated access to Streamlit secrets
    pin_val = st.text_input("Enter PIN", type="password")
    secrets_unlocked = pin_val.strip().upper() == "ALEX" if pin_val else False
    st.session_state["secrets_unlocked"] = secrets_unlocked
    if secrets_unlocked:
        st.caption("Secrets unlocked")

    st.subheader("Match Controls")
    match_type = st.radio("Match type", options=["Constructor", "Powered-up"], horizontal=True, index=1)
    gifts_opt = st.slider("Number of gifts", min_value=1, max_value=5, value=3)
    queries_opt = 1
    if match_type == "Powered-up":
        queries_opt = st.slider("Queries", min_value=1, max_value=5, value=3)

    # Constructor config from secrets; no manual base/key inputs
    base_url = os.environ.get("CONSTRUCTOR_BASE_URL", "https://ac.cnstrc.com")
    os.environ["CONSTRUCTOR_BASE_URL"] = base_url
    api_key = ""
    if secrets_unlocked:
        try:
            api_key = st.secrets.get("CONS_KEY", "")
        except Exception:
            api_key = ""
        if api_key:
            api_key = normalize_public_key(api_key)
            os.environ["CONSTRUCTOR_PUBLIC_KEY"] = api_key
    if not api_key:
        api_key = os.environ.get("CONSTRUCTOR_PUBLIC_KEY", "")
    per_page = st.slider("Results per iteration", min_value=10, max_value=50, value=24, step=2)
    pages_per_iter = 1
    # Defaults ON (no toggles): include budget in query, strict budget, logging, restrict to whitelist
    include_budget_in_query = True
    strict_budget = True
    enable_logging = True
    restrict_cats = True

    st.subheader("LLM")
    model_opt = st.selectbox("LLM model", options=["Please select", "gpt-4o-mini"], index=0)
    if model_opt != "Please select" and secrets_unlocked:
        try:
            secret_key = st.secrets.get("Gifting", "")
        except Exception:
            secret_key = ""
        if secret_key:
            os.environ["OPENROUTER_API_KEY"] = secret_key
            os.environ["OPENROUTER_BASE_URL"] = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            os.environ["OPENROUTER_MODEL"] = "openai/gpt-4o-mini" if model_opt == "gpt-4o-mini" else model_opt
            st.session_state["llm_enabled"] = True
            st.caption("LLM enabled")
        else:
            st.session_state["llm_enabled"] = False
            st.warning("LLM selected but no OpenRouter key in secrets (Gifting)")
    else:
        st.session_state["llm_enabled"] = False

tabs = st.tabs(["Images", "Quiz", "URLs"])

with tabs[1]:
    st.subheader("Who is the gift for?")
    recipient_kind = st.radio("Recipient kind", options=["Human","Pet"], horizontal=True, index=0)

    who_keys_all = list((quiz.get("who") or {}).keys())

    # Generation selection first for Human
    GENERATIONS = [
        ("Gen Alpha (1–14)", 1, 14),
        ("Gen Z (13–28)", 13, 28),
        ("Millennials (29–44)", 29, 44),
        ("Gen X (45–60)", 45, 60),
        ("Boomers (61–79)", 61, 79),
        ("Silent Generation (80–97)", 80, 97),
    ]
    gen_labels = [g[0] for g in GENERATIONS]
    gen_idx_default = 0
    gen_label = None

    def allowed_who_for_gen(gl: str) -> List[str]:
        gl = gl.lower()
        base = {
            "alpha": ["child"],
            "gen z": ["partner","friend","coworker"],
            "millennials": ["parent","partner","friend","coworker"],
            "gen x": ["parent","partner","friend","coworker"],
            "boomers": ["grandparent","partner","friend","coworker"],
            "silent": ["grandparent","partner","friend"],
        }
        for k,v in base.items():
            if k in gl:
                return v
        return ["partner","friend","coworker"]

    gender = None
    age = None
    interest = None
    budget_label = None
    relationship = None
    age_range = (None, None)

    if recipient_kind == "Pet":
        # Pet flow
        who = "pet"
        node = quiz["who"][who]
        pet_types = list((node.get("pet_type") or {}).keys())
        pet = st.selectbox("Pet type", options=pet_types)
        pet_node = node["pet_type"][pet]
        interests = pet_node.get("interests", [])
        interest = st.selectbox("Interest", options=interests)
        budgets = pet_node.get("budget", [])
        budget_label = st.selectbox("Budget", options=budgets)
        relationship = f"{pet}"
    else:
        # Human flow: generation first
        gen_label = st.selectbox("Generation", options=gen_labels, index=gen_idx_default)
        allowed = allowed_who_for_gen(gen_label)
        # Intersect with available who keys in quiz
        who_candidates = [w for w in allowed if w in who_keys_all]
        if not who_candidates:
            who_candidates = [w for w in who_keys_all if w != "pet"]
        who = st.selectbox("Recipient type", options=who_candidates)
        node = quiz["who"][who]
        genders = list((node.get("gender") or {}).keys())
        gender = st.selectbox("Gender", options=genders)
        if who == "child":
            # Child: show age slider and map to child buckets
            gmin, gmax = next((a, b) for (lbl, a, b) in GENERATIONS if lbl == gen_label)
            age_range = st.slider("Age range", min_value=1, max_value=97, value=(gmin, gmax))
            available_buckets = list(((node["gender"][gender]).get("age") or {}).keys())
            def _bucket_range(bk: str) -> Tuple[int, int]:
                if bk == "0_2": return (0,2)
                if bk == "3_5": return (3,5)
                if bk == "6_8": return (6,8)
                if bk == "9_12": return (9,12)
                if bk == "13_17": return (13,17)
                if bk == "18_plus": return (18, 120)
                return (0, 120)
            rep_age = int((age_range[0] + age_range[1]) // 2)
            best_bk = None
            best_dist = 10**9
            for bk in available_buckets:
                lo_b, hi_b = _bucket_range(bk)
                mid = (lo_b + hi_b) / 2
                dist = 0 if (lo_b <= rep_age <= hi_b) else abs(rep_age - mid)
                if dist < best_dist:
                    best_dist = dist
                    best_bk = bk
            age_bucket = best_bk or (available_buckets[0] if available_buckets else "13_17")
            age_node = node["gender"][gender]["age"][age_bucket]
        else:
            # Adult recipients: force 18_plus
            age_range = (18, 97)
            age_bucket = "18_plus"
            age_dict = (node.get("gender", {}).get(gender, {}).get("age", {}))
            if isinstance(age_dict, dict) and age_bucket in age_dict:
                age_node = age_dict[age_bucket]
            else:
                # fallback: take first available
                if isinstance(age_dict, dict) and age_dict:
                    first_key = next(iter(age_dict.keys()))
                    age_node = age_dict.get(first_key, {})
                else:
                    age_node = {}
        interests = age_node.get("interests", []) if isinstance(age_node, dict) else []
        interest = st.selectbox("Interest", options=interests)
        budgets = age_node.get("budget", []) if isinstance(age_node, dict) else []
        budget_label = st.selectbox("Budget", options=budgets)
        relationship = who

    st.divider()
    if st.button("Find products", key="quiz_go", type="primary"):
        lo, hi = parse_budget_range(budget_label or "")
        age_text_display = None
        if who != "pet" and age_range[0] is not None:
            age_text_display = f"ages {age_range[0]}–{age_range[1]}"
        p_phrase = price_text(*parse_budget_range(budget_label or "")) if include_budget_in_query else None
        current_generation = gen_label if who != "pet" else None
        q_base = build_query_text(relationship, None if who == "pet" else gender, age_text_display, interest or "", p_phrase, current_generation)
        include_cats = interest_to_categories(interest or "", restrict_to_whitelist=restrict_cats)
        run_product_search(q_base, include_cats, lo, hi, label="Quiz")

with tabs[2]:
    st.subheader("URLs")
    st.caption("Build a Constructor URL from natural language and filters (no LLM). Spaces → %20, '&' → 'and' automatically.")
    url_nl = st.text_area("Natural language", value=st.session_state.get("url_nl", ""))
    st.session_state["url_nl"] = url_nl
    @st.cache_data
    def fetch_filter_types(base: str, key: str) -> List[str]:
        try:
            # minimal seed query to fetch facets; tolerate failure
            seed_url = f"{base}/v1/search/natural_language/ideas"
            params = {"key": key, "s": 1, "num_results_per_page": 1}
            r = requests.get(seed_url, params=params, timeout=8)
            r.raise_for_status()
            data = r.json()
            facets = ((data.get("response") or {}).get("facets") or [])
            names = []
            for f in facets:
                nm = f.get("name") or f.get("display_name")
                if nm:
                    names.append(str(nm))
            # Dedup, keep common ones first
            base_order = [
                "Category","Product Type","Subcategory","Price","Audience","Colour","Material","Features","Book Genre","Brand","Size","Suitable for ages","Capacity","Power Rating"
            ]
            out = []
            for b in base_order:
                if b in names and b not in out:
                    out.append(b)
            for n in names:
                if n not in out:
                    out.append(n)
            return out or base_order
        except Exception:
            return [
                "Category","Product Type","Subcategory","Price","Audience","Colour","Material","Features","Book Genre","Brand","Size","Suitable for ages","Capacity","Power Rating"
            ]

    FILTER_TYPES = fetch_filter_types(base_url, api_key)
    if "url_filters" not in st.session_state:
        st.session_state["url_filters"] = []
    filters_list = st.session_state["url_filters"]
    st.write("Filters")
    rm = []
    for idx, row in enumerate(filters_list):
        c1, c2, c3 = st.columns([2,4,1])
        with c1:
            row["type"] = st.selectbox("Type", options=FILTER_TYPES, index=(FILTER_TYPES.index(row.get("type")) if row.get("type") in FILTER_TYPES else 0), key=f"url_ft_{idx}")
        with c2:
            row["value"] = st.text_input("Value", value=row.get("value",""), key=f"url_fv_{idx}")
        with c3:
            if st.button("Remove", key=f"url_fr_{idx}"):
                rm.append(idx)
    if rm:
        st.session_state["url_filters"] = [r for i, r in enumerate(filters_list) if i not in rm]
        st.rerun()
    if st.button("Add filter", key="url_f_add"):
        st.session_state["url_filters"].append({"type": FILTER_TYPES[0], "value": ""})
        st.rerun()

    st.divider()
    if st.button("Find products", key="url_go", type="primary"):
        pairs: List[Tuple[str,str]] = []
        for row in st.session_state["url_filters"]:
            t = (row.get("type") or "").strip()
            v = (row.get("value") or "").strip()
            if not t or not v:
                continue
            pairs.append((f"filters[{t}]", v))
        urls_used: List[str] = []
        errors: List[str] = []
        chosen: List[Dict[str, Any]] = []
        try:
            if match_type == "Constructor":
                raw, urls1 = fetch_aggregate_items_generic(base_url, url_nl, api_key, per_page=max(per_page, gifts_opt), pages=1, filter_pairs=pairs)
                urls_used.extend(urls1)
                items = [normalise_item(it) for it in raw]
                chosen = items[:gifts_opt]
            else:
                all_items: List[Dict[str, Any]] = []
                last_best = None
                for iter_idx in range(1, queries_opt + 1):
                    if iter_idx == 1:
                        q_iter = url_nl
                    elif iter_idx % 2 == 0:
                        q_iter = divergent_variant(url_nl, url_nl, [], None)
                    else:
                        q_iter = refine_query(url_nl, last_best) if last_best else url_nl
                    raw, urls2 = fetch_aggregate_items_generic(base_url, q_iter, api_key, per_page=per_page, pages=pages_per_iter, filter_pairs=pairs)
                    urls_used.extend(urls2)
                    seen_local = set()
                    uniq_raw = []
                    for it in raw:
                        pid = it.get("id") or (it.get("data") or {}).get("id") or it.get("url")
                        pid = str(pid)
                        if pid and pid not in seen_local:
                            seen_local.add(pid)
                            uniq_raw.append(it)
                    items = [normalise_item(it) for it in uniq_raw]
                    all_items.extend(items)
                    if items:
                        best = sorted(items, key=lambda it: score_item(it, url_nl, None, None), reverse=True)[0]
                        last_best = best
                ranked = sorted(all_items, key=lambda it: score_item(it, url_nl, None, None), reverse=True)
                seen = set()
                for it in ranked:
                    pid = it.get("id") or it.get("url")
                    if pid and pid not in seen and it.get("url"):
                        chosen.append(it)
                        seen.add(pid)
                    if len(chosen) >= gifts_opt:
                        break
        except Exception as e:
            errors.append(str(e))
        st.session_state["last_results"] = chosen
        st.session_state["last_errors"] = errors
        st.session_state["last_urls"] = urls_used
        st.session_state["last_label"] = "URLs"

with tabs[0]:
    # Images vibe picker (simplified UI)
    files, deck_sig = discover_images("unsplash_images")
    total_files = len(files)
    use_all = st.sidebar.toggle("Use all images", value=True, key="use_all_images")
    slider_min = 50 if total_files >= 50 else max(1, total_files)
    slider_max = 400 if total_files >= 400 else max(slider_min, total_files if total_files else 50)
    if slider_max < slider_min:
        slider_max = slider_min
    default_value = min(100, total_files) if total_files else slider_min
    step = 10 if slider_max > slider_min else 1
    deck_size = st.sidebar.slider(
        "Deck size",
        min_value=slider_min,
        max_value=slider_max,
        value=min(max(slider_min, default_value), slider_max),
        step=step,
        key="deck_size",
    )
    rng = random.Random(deck_sig)
    files_sorted = sorted(files)
    rng.shuffle(files_sorted)
    deck = files_sorted if use_all or deck_size >= len(files_sorted) else files_sorted[:deck_size]
    st.sidebar.write(f"Found: **{total_files}** | Using: **{len(deck)}**")
    names = [p.name for p in files]
    dupes = [n for n, c in Counter(names).items() if c > 1]
    exts = Counter(p.suffix.lower() for p in files)
    with st.sidebar.expander("Diagnostics", expanded=False):
        st.write("Extensions:", dict(exts))
        if dupes:
            st.warning(f"Duplicate filenames: {len(dupes)} (e.g., {dupes[:3]})")
    if len(deck) == 0:
        st.info("Add images to the 'unsplash_images' folder to get started.")
        st.stop()

    meta_path = os.path.join("unsplash_images", "metadata.json")
    df_meta = load_meta_df(meta_path, deck_sig)
    if (df_meta is None or (hasattr(df_meta, "empty") and df_meta.empty)) and deck:
        try:
            import pandas as pd  # type: ignore

            base_path = Path("unsplash_images").resolve()
            records = []
            for path in deck:
                try:
                    rel = str(path.resolve().relative_to(base_path))
                except Exception:
                    rel = path.name
                records.append(
                    {
                        "photo_id": path.stem,
                        "filename": rel,
                        "alt_description": path.stem,
                        "tags": [],
                    }
                )
            if records:
                df_meta = pd.DataFrame(records)
                df_meta["text"] = (
                    df_meta["alt_description"].fillna("").astype(str)
                    + " "
                    + df_meta["tags"].apply(lambda lst: " ".join([str(t) for t in lst]))
                ).str.lower()
        except Exception:
            df_meta = None
    if df_meta is None or (hasattr(df_meta, "empty") and df_meta.empty):
        st.info("Provide a valid metadata.json from Unsplash downloads.")
    else:
        base_dir = os.path.dirname(meta_path) or "."
        base_path = Path(base_dir).resolve()
        file_by_name: Dict[str, Path] = {}
        file_by_rel: Dict[str, Path] = {}
        file_by_stem: Dict[str, Path] = {}
        for p in files:
            try:
                resolved = p.resolve()
            except Exception:
                resolved = Path(p)
            file_by_name.setdefault(p.name, resolved)
            try:
                rel = str(resolved.relative_to(base_path))
                file_by_rel.setdefault(rel, resolved)
            except Exception:
                pass
            file_by_stem.setdefault(resolved.stem, resolved)

        def _normalise_param_values(values: Any) -> List[str]:
            normalised: List[str] = []
            if values is None:
                return normalised
            if isinstance(values, (list, tuple)):
                iterable = values
            else:
                iterable = [values]
            for item in iterable:
                if item is None:
                    continue
                text = str(item)
                if text:
                    normalised.append(text)
            return normalised

        def _get_query_params_lists() -> Dict[str, List[str]]:
            try:
                qp = st.query_params
            except Exception:
                qp = None
            if qp is not None:
                data: Dict[str, List[str]] = {}
                try:
                    keys = list(qp.keys())  # type: ignore[attr-defined]
                except Exception:
                    keys = list(qp)
                for key in keys:
                    values: List[str]
                    try:
                        values = [str(v) for v in qp.get_all(key)]  # type: ignore[attr-defined]
                    except AttributeError:
                        values = _normalise_param_values(qp.get(key))
                    except Exception:
                        values = []
                    filtered = [v for v in values if v]
                    if filtered:
                        data[str(key)] = filtered
                return data
            raw = st.experimental_get_query_params()
            data: Dict[str, List[str]] = {}
            for k, v in raw.items():
                normalised = _normalise_param_values(v)
                if normalised:
                    data[str(k)] = normalised
            return data

        def _set_query_params_lists(params: Dict[str, List[str]]) -> None:
            cleaned: Dict[str, List[str]] = {}
            for key, values in params.items():
                normalised = _normalise_param_values(values)
                if normalised:
                    cleaned[str(key)] = normalised
            serialised = {
                k: v if len(v) > 1 else v[0]
                for k, v in cleaned.items()
            }
            updated = False
            try:
                qp = st.query_params
                if cleaned:
                    try:
                        qp.clear()
                    except Exception:
                        pass
                    qp.from_dict(serialised)
                else:
                    qp.clear()
                updated = True
            except Exception:
                updated = False
            if updated:
                return
            try:
                if cleaned:
                    st.experimental_set_query_params(**serialised)
                else:
                    st.experimental_set_query_params()
            except Exception:
                pass

        def _build_image_action_url(action: str) -> str:
            params = dict(_get_query_params_lists())
            params["img_select"] = [action]
            query = urlencode(params, doseq=True)
            return f"?{query}" if query else "?"

        def _row_pid(r):
            return r.get("photo_id") or r.get("id") or ""

        def _row_local_path(r):
            fn = r.get("filename")
            if isinstance(fn, str) and fn:
                raw = fn.strip()
                candidate = file_by_rel.get(raw) or file_by_name.get(Path(raw).name)
                if candidate and candidate.exists():
                    return str(candidate)
                candidate_path = base_path / raw
                if candidate_path.exists():
                    return str(candidate_path)
            pid = str(_row_pid(r)).strip()
            if pid:
                candidate = file_by_stem.get(pid)
                if candidate and candidate.exists():
                    return str(candidate)
                for ext in SUPPORTED:
                    candidate_path = base_path / f"{pid}{ext}"
                    if candidate_path.exists():
                        return str(candidate_path)
            return None

        def _show_image_box(src: str, alt_text: str = "", height: int = 240) -> None:
            safe_alt = html.escape(alt_text or "")
            st.markdown(
                f"""
                <div data-image-box style="width: 100%; height: {height}px; overflow: hidden; border-radius: 12px; border: 1px solid #ddd;">
                    <img src="{src}" alt="{safe_alt}" style="width: 100%; height: 100%; object-fit: cover; display: block;" />
                </div>
                """,
                unsafe_allow_html=True,
            )

        def _render_image(r, height: int = 240):
            alt_text = str(r.get("alt_description") or "")
            lp = _row_local_path(r)
            if lp:
                uri = file_to_data_uri(lp)
                if uri:
                    _show_image_box(uri, alt_text, height=height)
                    return True
            pid = _row_pid(r)
            if pid:
                _show_image_box(f"https://source.unsplash.com/{pid}/600x400", alt_text, height=height)
                return True
            return False

        overrides = st.session_state.get("img_meta_override", {})
        if overrides:
            df_meta = df_meta.copy()
            for idx, r in df_meta.iterrows():
                pid = r.get("photo_id") or r.get("id")
                if pid and pid in overrides:
                    ov = overrides[pid]
                    if ov.get("alt_description"):
                        df_meta.at[idx, "alt_description"] = ov["alt_description"]
                    if ov.get("tags") is not None:
                        df_meta.at[idx, "tags"] = ov["tags"]

        try:
            import pandas as pd  # type: ignore

            existing_paths: Set[Path] = set()
            for _, row in df_meta.iterrows():
                lp = _row_local_path(row)
                if not lp:
                    continue
                try:
                    existing_paths.add(Path(lp).resolve())
                except Exception:
                    existing_paths.add(Path(lp))
            additions = []
            for path in deck:
                try:
                    resolved = path.resolve()
                except Exception:
                    resolved = path
                if resolved in existing_paths:
                    continue
                try:
                    rel = str(resolved.relative_to(base_path))
                except Exception:
                    rel = path.name
                additions.append(
                    {
                        "photo_id": path.stem,
                        "filename": rel,
                        "alt_description": path.stem.replace("_", " ").replace("-", " "),
                        "tags": [],
                    }
                )
                existing_paths.add(resolved)
            if additions:
                df_meta = pd.concat([df_meta, pd.DataFrame(additions)], ignore_index=True)
        except Exception:
            pass

        if "tags" in df_meta.columns:
            df_meta["tags"] = df_meta["tags"].apply(lambda x: x if isinstance(x, list) else [])
        else:
            df_meta["tags"] = [[] for _ in range(len(df_meta))]
        if "alt_description" not in df_meta.columns:
            df_meta["alt_description"] = ""
        df_meta["alt_description"] = df_meta["alt_description"].fillna("")
        df_meta["text"] = (
            df_meta["alt_description"].astype(str)
            + " "
            + df_meta["tags"].apply(lambda lst: " ".join([str(t) for t in lst]))
        ).str.lower()
        df_meta = df_meta.reset_index(drop=True)

        path_to_idx: Dict[Path, int] = {}
        for idx, row in df_meta.iterrows():
            lp = _row_local_path(row)
            if not lp:
                continue
            try:
                path_to_idx[Path(lp).resolve()] = idx
            except Exception:
                path_to_idx[Path(lp)] = idx
        deck_indices: List[int] = []
        for path in deck:
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path
            idx = path_to_idx.get(resolved)
            if idx is None:
                for cand_path, cand_idx in path_to_idx.items():
                    if cand_path.name == path.name:
                        idx = cand_idx
                        break
            if idx is not None:
                deck_indices.append(idx)
        if deck_indices:
            seen_idx: Set[int] = set()
            leaf_ids: List[int] = []
            for idx in deck_indices:
                if idx not in seen_idx:
                    leaf_ids.append(idx)
                    seen_idx.add(idx)
        else:
            leaf_ids = list(range(len(df_meta)))

        if not leaf_ids:
            st.info("No images available after filtering.")
            st.stop()

        key_path = "img_meta_path"
        key_tree = "img_tree"
        key_bits = "img_path_bits"
        key_emb = "img_embeddings"
        key_sig = "img_deck_sig"
        key_leaf = "img_leaf_ids"
        key_meta_len = "img_meta_len"
        key_text_sig = "img_text_sig"
        text_sig = (
            hashlib.md5("||".join(df_meta["text"].astype(str).tolist()).encode("utf-8")).hexdigest()
            if len(df_meta) else ""
        )
        stored_leaf_ids = tuple(st.session_state.get(key_leaf, ()))
        needs_refresh = (
            st.session_state.get(key_path) != meta_path
            or st.session_state.get(key_sig) != deck_sig
            or st.session_state.get(key_meta_len) != len(df_meta)
            or st.session_state.get(key_text_sig) != text_sig
            or stored_leaf_ids != tuple(leaf_ids)
        )
        if needs_refresh:
            st.session_state[key_path] = meta_path
            st.session_state[key_sig] = deck_sig
            st.session_state[key_meta_len] = len(df_meta)
            st.session_state[key_text_sig] = text_sig
            st.session_state[key_bits] = []
            emb = embed_texts(df_meta["text"].tolist())
            st.session_state[key_emb] = emb
            st.session_state.setdefault("img_seed", 0)
            st.session_state[key_tree] = build_greedy_tree(leaf_ids, emb, seed=st.session_state["img_seed"])
            st.session_state[key_leaf] = tuple(leaf_ids)
        else:
            st.session_state[key_leaf] = tuple(leaf_ids)

        if key_bits not in st.session_state:
            st.session_state[key_bits] = []

        params_current = _get_query_params_lists()
        selection_vals = params_current.pop("img_select", None)
        if selection_vals:
            _set_query_params_lists(params_current)
            choice = selection_vals[-1]
            if choice == "left":
                st.session_state[key_bits].append(0)
                st.rerun()
            elif choice == "right":
                st.session_state[key_bits].append(1)
                st.rerun()
            elif choice == "neither":
                st.session_state["img_seed"] = int(st.session_state.get("img_seed", 0)) + 1
                emb = st.session_state.get(key_emb)
                current_leaf_ids = list(st.session_state.get(key_leaf, tuple(leaf_ids)))
                st.session_state[key_tree] = build_greedy_tree(current_leaf_ids, emb, seed=st.session_state["img_seed"])
                st.rerun()

        bits = st.session_state.get(key_bits, [])
        tree = st.session_state.get(key_tree)
        emb = st.session_state.get(key_emb)
        if tree is None:
            st.info("No image tree available.")
            st.stop()
        try:
            node_img = walk_tree(tree, bits)
        except Exception:
            st.session_state[key_bits] = []
            node_img = walk_tree(tree, [])
        if isinstance(node_img, dict):
            i, j = node_img["pair_idx"]
            left_row = df_meta.iloc[i]
            right_row = df_meta.iloc[j]
            # Clickable images
            st.markdown("### Which vibe matches?")
            img_srcs: List[str] = []
            img_alts: List[str] = []
            for r in (left_row, right_row):
                alt_text = str(r.get("alt_description") or "")
                img_alts.append(alt_text)
                lp = _row_local_path(r)
                if lp:
                    uri = file_to_data_uri(lp)
                    if uri:
                        img_srcs.append(uri)
                        continue
                pid = r.get("photo_id") or r.get("id") or ""
                img_srcs.append(f"https://source.unsplash.com/{pid}/600x400")
            try:
                from clickable_images import clickable_images  # type: ignore

                clicked = clickable_images(
                    img_srcs,
                    titles=["", ""],
                    div_style={
                        "display": "flex",
                        "justify-content": "space-between",
                        "gap": "1rem",
                        "align-items": "stretch",
                    },
                    img_style={
                        "width": "100%",
                        "height": "240px",
                        "object-fit": "cover",
                        "border-radius": "12px",
                        "border": "1px solid #ddd",
                        "box-shadow": "0 2px 8px rgba(0,0,0,0.05)",
                    },
                )
                if clicked == 0:
                    st.session_state[key_bits].append(0)
                    st.rerun()
                elif clicked == 1:
                    st.session_state[key_bits].append(1)
                    st.rerun()
                # Neither match CTA
                ncol = st.columns([1, 1, 1])
                with ncol[1]:
                    if st.button("Neither match", key="img_neither"):
                        st.session_state["img_seed"] = int(st.session_state.get("img_seed", 0)) + 1
                        emb = st.session_state.get(key_emb)
                        current_leaf_ids = list(st.session_state.get(key_leaf, tuple(leaf_ids)))
                        st.session_state[key_tree] = build_greedy_tree(current_leaf_ids, emb, seed=st.session_state["img_seed"])
                        st.rerun()
            except Exception:
                if len(img_srcs) == 2 and all(img_srcs):
                    st.markdown(
                        """
                        <style>
                        .img-choice-grid {
                            display: flex;
                            justify-content: space-between;
                            gap: 1rem;
                            align-items: stretch;
                        }
                        .img-choice-grid .img-choice {
                            flex: 1;
                            display: block;
                            border-radius: 12px;
                            overflow: hidden;
                            border: 1px solid #ddd;
                            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
                            transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
                        }
                        .img-choice-grid .img-choice:hover,
                        .img-choice-grid .img-choice:focus {
                            transform: translateY(-2px);
                            box-shadow: 0 6px 16px rgba(0,0,0,0.12);
                            border-color: #bbb;
                        }
                        .img-choice-grid .img-choice img {
                            width: 100%;
                            height: 240px;
                            object-fit: cover;
                            display: block;
                        }
                        .img-choice-actions {
                            margin-top: 1rem;
                            text-align: center;
                        }
                        .img-choice-actions a {
                            display: inline-block;
                            padding: 0.5rem 1.25rem;
                            border-radius: 999px;
                            border: 1px solid #444;
                            color: #444;
                            text-decoration: none;
                            font-weight: 500;
                            transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
                        }
                        .img-choice-actions a:hover,
                        .img-choice-actions a:focus {
                            background-color: #444;
                            border-color: #444;
                            color: #fff;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )
                    choice_container_id = f"img-choice-{uuid.uuid4().hex}"
                    left_url = _build_image_action_url("left")
                    right_url = _build_image_action_url("right")
                    neither_url = _build_image_action_url("neither")
                    st.markdown(
                        f"""
                        <div id="{choice_container_id}" class="img-choice-root" data-img-choice-root="true">
                            <div class="img-choice-grid">
                                <a class="img-choice" data-img-choice-link href="{left_url}" target="_self">
                                    <img src="{html.escape(img_srcs[0], quote=True)}" alt="{html.escape(img_alts[0] or '', quote=True)}" />
                                </a>
                                <a class="img-choice" data-img-choice-link href="{right_url}" target="_self">
                                    <img src="{html.escape(img_srcs[1], quote=True)}" alt="{html.escape(img_alts[1] or '', quote=True)}" />
                                </a>
                            </div>
                            <div class="img-choice-actions">
                                <a data-img-choice-link href="{neither_url}" target="_self">Neither match</a>
                            </div>
                        </div>
                        <script>
                        (function() {{
                            const root = document.getElementById("{choice_container_id}");
                            if (!root || root.dataset.bound === "true") {{
                                return;
                            }}
                            root.dataset.bound = "true";
                            const sendParams = (href) => {{
                                if (!href) {{
                                    return false;
                                }}
                                try {{
                                    const url = new URL(href, window.location.href);
                                    const params = {{}};
                                    url.searchParams.forEach((value, key) => {{
                                        if (!params[key]) {{
                                            params[key] = [];
                                        }}
                                        params[key].push(value);
                                    }});
                                    const callStreamlit = (fnName, args) => {{
                                        const stObj = window.Streamlit || (window.parent && window.parent.Streamlit);
                                        if (stObj && typeof stObj[fnName] === "function") {{
                                            stObj[fnName](...args);
                                            return true;
                                        }}
                                        return false;
                                    }};
                                    if (!callStreamlit("setQueryParams", [params])) {{
                                        const target = window.parent || window;
                                        target.postMessage({{ type: "streamlit:setQueryParams", queryParams: params }}, "*");
                                    }}
                                    if (!callStreamlit("rerun", [])) {{
                                        const target = window.parent || window;
                                        target.postMessage({{ type: "streamlit:rerunScript" }}, "*");
                                    }}
                                    return true;
                                }} catch (err) {{
                                    console.error("Image choice handler error", err);
                                    return false;
                                }}
                            }};
                            const handleClick = (event) => {{
                                const href = event.currentTarget.getAttribute("href");
                                if (sendParams(href)) {{
                                    event.preventDefault();
                                    event.stopPropagation();
                                }}
                            }};
                            root.querySelectorAll("a[data-img-choice-link]").forEach((el) => {{
                                el.addEventListener("click", handleClick, {{ passive: false }});
                            }});
                        }})();
                        </script>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    # Fallback to buttons if component or image sources are unavailable
                    col1, col2 = st.columns(2)
                    with col1:
                        if not _render_image(left_row):
                            st.write("No image available")
                        if st.button("This matches", key="img_left_btn"):
                            st.session_state[key_bits].append(0)
                            st.rerun()
                    with col2:
                        if not _render_image(right_row):
                            st.write("No image available")
                        if st.button("This matches", key="img_right_btn"):
                            st.session_state[key_bits].append(1)
                            st.rerun()
                    ccent = st.columns([1, 1, 1])
                    with ccent[1]:
                        if st.button("Neither match", key="img_neither_btn"):
                            st.session_state["img_seed"] = int(st.session_state.get("img_seed", 0)) + 1
                            emb = st.session_state.get(key_emb)
                            current_leaf_ids = list(st.session_state.get(key_leaf, tuple(leaf_ids)))
                            st.session_state[key_tree] = build_greedy_tree(current_leaf_ids, emb, seed=st.session_state["img_seed"])
                            st.rerun()
        else:
            leaf_idx = node_img
            try:
                leaf = df_meta.iloc[leaf_idx]
            except Exception:
                st.info("No leaf selected; reset and try again.")
                if st.button("Reset images path"):
                    st.session_state[key_bits] = []
                    st.rerun()
            else:
                selected_indices = collect_selected_indices(tree, bits)
                if not selected_indices:
                    selected_indices = [leaf_idx]
                cols_per_row = 3
                for start in range(0, len(selected_indices), cols_per_row):
                    row_cols = st.columns(min(cols_per_row, len(selected_indices) - start))
                    for offset, col in enumerate(row_cols):
                        with col:
                            img_idx = selected_indices[start + offset]
                            try:
                                img_row = df_meta.iloc[img_idx]
                            except Exception:
                                st.write("No image available")
                                continue
                            if not _render_image(img_row):
                                st.write("No image available")
                tags = leaf.get("tags", [])
                if not isinstance(tags, list):
                    tags = []
                alt_text = str(leaf.get("alt_description") or "")
                selected_rows = []
                for idx_sel in selected_indices:
                    try:
                        selected_rows.append(df_meta.iloc[idx_sel])
                    except Exception:
                        continue
                if not selected_rows:
                    selected_rows = [leaf]

                taste_top = top_tags_from_rows(selected_rows, top_k=6)
                if not taste_top and isinstance(tags, list):
                    taste_top = [str(t) for t in tags if str(t).strip()]

                st.markdown("#### Budget")
                budget_value: int = st.slider(
                    "Max budget ($)",
                    min_value=20,
                    max_value=300,
                    value=100,
                    step=5,
                    key="img_budget_slider",
                )

                qb = get_query_builder()
                q_preview, include_cats_prev, debug = qb.compose_with_debug(taste_top)
                raw_tags_dbg = debug.get("raw_tags", taste_top)
                filtered_tokens = debug.get("filtered_tokens", [])
                dropped_forbidden = debug.get("dropped_forbidden", [])
                dropped_not_allowed = debug.get("dropped_not_allowed", [])

                budget_tuple: Optional[Tuple[int, int]] = None
                budget_hi: Optional[int] = None
                budget_hi = int(budget_value)
                budget_tuple = (0, budget_hi)

                interpreter = get_query_interpreter()
                photo_ids: List[str] = []
                for row in selected_rows:
                    pid = row.get("photo_id") or row.get("id")
                    if not pid:
                        continue
                    text_pid = str(pid).strip()
                    if text_pid and text_pid not in photo_ids:
                        photo_ids.append(text_pid)

                interpreter_result = interpreter.interpret(
                    tokens=filtered_tokens,
                    categories=list(include_cats_prev),
                    photo_ids=photo_ids,
                    budget_aud=budget_tuple,
                    use_llm=False,
                )

                expanded_categories = interpreter_result.get("categories", include_cats_prev) or []
                queries_multi = interpreter_result.get("queries_multi", [])
                legacy_query = interpreter_result.get("query_no_llm", q_preview)
                recipient_guess = interpreter_result.get("recipient", "me")

                with st.expander("Query & URL preview", expanded=True):
                    st.write(f"Raw tags: {', '.join(raw_tags_dbg) or '-'}")
                    st.write(f"Filtered tokens: {', '.join(filtered_tokens) or '-'}")
                    st.write(f"Dropped (forbidden): {', '.join(dropped_forbidden) or '-'}")
                    st.write(f"Dropped (not allowed): {', '.join(dropped_not_allowed) or '-'}")
                    st.write(f"Categories: {', '.join(expanded_categories) or '-'}")
                    if legacy_query:
                        st.write(f"Legacy NL query: {legacy_query}")
                    else:
                        st.write("Legacy NL query: —")
                    if queries_multi:
                        st.markdown("**Query plan**")
                        for idx_q, (bucket, query_text) in enumerate(queries_multi, start=1):
                            st.write(f"{bucket}: {query_text}")
                            bucket_cats = [
                                c for c in expanded_categories if bucket.lower() in c.lower()
                            ]
                            if not bucket_cats:
                                bucket_cats = list(expanded_categories)
                            if bucket not in bucket_cats and bucket:
                                bucket_cats.append(bucket)
                            bucket_cats = [c for c in dict.fromkeys(bucket_cats) if c]
                            if recipient_guess == "couple":
                                if bucket == "Home":
                                    extras = ["Home", "Occasion", "Jewellery"]
                                elif bucket in {"Fashion", "Entertainment"}:
                                    extras = ["Jewellery", "Occasion"]
                                else:
                                    extras = []
                                for extra in extras:
                                    if extra not in bucket_cats:
                                        bucket_cats.append(extra)
                            url_categories = list(bucket_cats)
                            if api_key:
                                try:
                                    url_prev = url_for_bucket(
                                        base_url=base_url,
                                        api_key=api_key,
                                        nl=query_text,
                                        bucket=bucket,
                                        recipient=recipient_guess,
                                        budget_hi=budget_hi,
                                        expanded_categories=url_categories,
                                    )
                                    st.code(url_prev)
                                except Exception:
                                    pass
                            button_key = f"img_go_{leaf_idx}_{bucket}_{idx_q}"
                            if st.button(f"Find products ({bucket})", key=button_key):
                                run_product_search(
                                    query_text,
                                    bucket_cats,
                                    None,
                                    budget_hi,
                                    label=f"Images · {bucket}",
                                )
                    else:
                        st.info("No multi-bucket queries generated yet. Adjust your selections to continue.")

                    if st.button("Start over", key="img_start_over"):
                        st.session_state[key_bits] = []
                        st.rerun()

if False:
    pass  # placeholder removed old inline search block

    # Optional logging
    if enable_logging and chosen:
        try:
            os.makedirs("out_streamlit", exist_ok=True)
            log_path = os.path.join("out_streamlit", "log.csv")
            new_file = not os.path.exists(log_path)
            with open(log_path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow([
                        "timestamp","match_type","queries","gifts","relationship","gender","age_min","age_max","interest","budget_label",
                        "iter","query","categories_used","product_id","product_title","product_price","in_budget","product_url"
                    ])
                # Recompute to capture URL and cats used per iter
                include_cats = interest_to_categories(interest or "", restrict_to_whitelist=restrict_cats)
                lo, hi = parse_budget_range(budget_label or "")
                pf = price_filter_value(lo, hi)
                if match_type == "Constructor":
                    queries_used = [q]
                else:
                    queries_used = []
                    q_base = q
                    last_best = chosen[0] if chosen else None
                    for iter_idx in range(1, queries_opt + 1):
                        if iter_idx == 1:
                            q_iter_l = q_base
                        elif iter_idx % 2 == 0:
                            q_iter_l = divergent_variant(q_base, interest or "", include_cats, price_text(lo, hi))
                        else:
                            q_iter_l = refine_query(q_base, last_best) if last_best else q_base
                        queries_used.append(q_iter_l)
                for idx_iter, pick in enumerate(chosen, start=1):
                    cats_used = ",".join(include_cats)
                    price = pick.get("price")
                    in_budget = (price is not None) and ((lo is None or price >= lo) and (hi is None or price <= hi))
                    w.writerow([
                        datetime.utcnow().isoformat(), match_type, queries_opt, gifts_opt, relationship, gender if who != "pet" else "pet", 
                        age_range[0] if who != "pet" else "", age_range[1] if who != "pet" else "",
                        interest, budget_label, idx_iter, queries_used[min(idx_iter-1, len(queries_used)-1)], cats_used,
                        pick.get("id") or pick.get("url"), pick.get("title"), price, in_budget,
                        pick.get("url")
                    ])
                    # Expand categories a bit based on each pick for future context
                    cat_field = pick.get("categories")
                    if isinstance(cat_field, str) and cat_field:
                        for c in re.split(r"[|,/]", cat_field):
                            c = c.strip()
                            if c and c not in include_cats:
                                include_cats.append(c)
                    elif isinstance(cat_field, list):
                        for c in cat_field:
                            c = str(c).strip()
                            if c and c not in include_cats:
                                include_cats.append(c)
        except Exception as e:
            st.warning(f"Logging failed: {e}")

# (old Images/URLs tabs removed; new tabs defined above)

# -------- Shared Results Section --------
st.divider()
last_results = st.session_state.get("last_results", [])
last_errors = st.session_state.get("last_errors", [])
last_urls = st.session_state.get("last_urls", [])
if last_errors:
    st.warning("\n".join(last_errors))
if last_results:
    st.subheader("Top picks")
    lohi = st.session_state.get("last_budget", (None, None))
    lo_b, hi_b = lohi
    for idx, it in enumerate(last_results, start=1):
        title = it.get("title") or "View product"
        def _full_product_url(u: str) -> str:
            if not u:
                return ""
            su = str(u).strip()
            if su.startswith("http://") or su.startswith("https://"):
                return su
            return urljoin("https://www.kmart.com.au/", su.lstrip("/"))
        url = _full_product_url(it.get("url") or "")
        price = it.get("price")
        meta = f"${price:.2f}" if isinstance(price, (int, float)) and price is not None else ""
        # badges
        band = it.get("_band")
        price = it.get("price")
        in_budget = None
        if price is not None and (lo_b is not None or hi_b is not None):
            in_budget = (lo_b is None or price >= lo_b) and (hi_b is None or price <= hi_b)
        badge = ""
        if band == "expanded":
            badge += " [expanded]"
        if in_budget is True:
            badge += " [in budget]"
        elif in_budget is False:
            badge += " [out of budget]"
        st.markdown(f"{idx}. [{title}]({url}) {meta}{badge}")
    with st.expander("Search URLs used"):
        for i,u in enumerate(last_urls):
            st.code(u)
            if i == 0:
                st.text_input("Copy first URL", value=u, key="copy_first_url")
    # Logging
    if enable_logging:
        try:
            os.makedirs("out_streamlit", exist_ok=True)
            log_path = os.path.join("out_streamlit", "log.csv")
            new_file = not os.path.exists(log_path)
            with open(log_path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new_file:
                    w.writerow(["timestamp","label","match_type","queries","gifts","product_id","product_title","product_price","product_url"])
                for it in last_results:
                    w.writerow([
                        datetime.utcnow().isoformat(), st.session_state.get("last_label",""), match_type, queries_opt, gifts_opt,
                        it.get("id") or it.get("url"), it.get("title"), it.get("price"), it.get("url")
                    ])
        except Exception as e:
            st.warning(f"Logging failed: {e}")
else:
    st.info("No products yet. Use one of the tabs above and click 'Find products'.")
