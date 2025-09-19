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
                rel = resolved.relative_to(base_path)
                file_by_rel.setdefault(str(rel), resolved)
            except Exception:
                pass
            file_by_stem.setdefault(p.stem, resolved)

        def find_file(entry: str) -> Optional[Path]:
            if not entry:
                return None
            entry = entry.strip()
            # Try direct relative path
            if entry in file_by_rel:
                return file_by_rel[entry]
            # Try by name
            name = os.path.basename(entry)
            if name in file_by_name:
                return file_by_name[name]
            # Try by stem
            stem = Path(entry).stem
            if stem in file_by_stem:
                return file_by_stem[stem]
            return None

        @st.cache_data
        def build_text_matrix(df_sig: str, df_json: str) -> Tuple[np.ndarray, List[str]]:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
            except Exception:
                return np.empty((0, 0)), []
            df = json.loads(df_json)
            texts = [row.get("text") or "" for row in df]
            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform(texts)
            return matrix, texts

        df_meta_records = df_meta.to_dict(orient="records")
        matrix, texts = build_text_matrix(
            df_sig=hashlib.sha256(df_meta.to_json().encode("utf-8")).hexdigest(),
            df_json=df_meta.to_json(),
        )
        df_meta = df_meta.assign(text_lower=df_meta["text"].str.lower())

        if matrix.size > 0 and df_meta_records:
            st.write("### Explore deck by prompt or tags")
            prompt = st.text_input("Describe the vibe you're after", key="deck_prompt")
            if prompt:
                prompt_lower = prompt.lower()
                matches = df_meta[df_meta["text_lower"].str.contains(prompt_lower)]
                if matches.empty:
                    try:
                        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
                    except Exception:
                        cosine_similarity = None  # type: ignore
                    if cosine_similarity is not None:
                        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore

                        vectorizer = TfidfVectorizer(stop_words="english")
                        prompt_vec = vectorizer.fit_transform([prompt])
                        similarity = cosine_similarity(prompt_vec, matrix)
                        top_idx = np.argsort(similarity[0])[::-1][:12]
                        matches = df_meta.iloc[top_idx]
                st.write(f"Showing {len(matches)} matches for prompt.")
                cols = st.columns(4)
                for idx, row in matches.head(12).iterrows():
                    file_path = find_file(row.get("filename") or "")
                    if not file_path or not file_path.exists():
                        continue
                    img_data = load_image_safe(str(file_path))
                    if not img_data:
                        continue
                    with cols[idx % 4]:
                        st.image(img_data, caption=row.get("alt_description") or row.get("photo_id"))

    st.divider()
    st.write("### Quick construct URLs")
    st.caption("Use pre-built combos or craft new ones with the controls below.")

    match_type = st.selectbox("Mode", options=["Constructor", "Feedback"], key="match_type", index=0)
    queries_opt = st.number_input("Queries to try", min_value=1, max_value=10, value=3)
    pages_per_iter = st.number_input("Pages per iteration", min_value=1, max_value=5, value=1)
    per_page = st.number_input("Results per page (Constructor)", min_value=1, max_value=40, value=12)
    gifts_opt = st.number_input("Gift picks", min_value=1, max_value=20, value=6)

    st.write("### Relationship & interests")
    relationship = st.selectbox(
        "Relationship",
        options=["friend", "partner", "parent", "child", "coworker", "boss", "sibling", "relative", "pet"],
        key="quiz_relationship",
    )
    gender = st.selectbox("Recipient gender", options=["", "male", "female", "non-binary"], key="quiz_gender")
    age_range = st.slider("Age range", min_value=0, max_value=100, value=(18, 35))
    interest = st.text_input("Interest", key="quiz_interest")
    budget_label = st.selectbox(
        "Budget",
        options=["Under $25", "$25-$50", "$50-$100", "$100-$200", "Over $200"],
        key="quiz_budget",
    )
    restrict_cats = st.checkbox("Restrict to category whitelist", value=True, key="quiz_restrict_cats")

    vibe_choices = [v.get("label") for v in load_vibes_data() if v.get("label")]
    vibe_label = st.selectbox("Vibe (optional)", options=[""] + vibe_choices, key="quiz_vibe")

    st.divider()
    st.write("### Query preview")
    include_budget = st.checkbox("Include budget in query text", value=True, key="quiz_include_budget")
    q = build_query_text(
        relationship,
        gender,
        f"ages {age_range[0]}–{age_range[1]}",
        interest,
        price_text(*parse_budget_range(budget_label or "")) if include_budget else None,
        vibe_label,
    )
    st.code(q, language="text")

    st.divider()
    st.write("### Run search")
    price_range = parse_budget_range(budget_label or "")

    st.write("Include categories:", ", ".join(interest_to_categories(interest or "", restrict_to_whitelist=restrict_cats)))
    st.write("Price filter:", price_filter_value(*price_range))

    st.divider()
    st.write("### Plan overview")
    st.write(
        f"""
        Mode: **{match_type}**  
        Queries: **{queries_opt}** · Pages per iter: **{pages_per_iter}**  
        Gifts to show: **{gifts_opt}** · Budget: **{budget_label}**
        """
    )

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
                "Category", "Product Type", "Subcategory", "Price", "Audience", "Colour", "Material", "Features",
                "Book Genre", "Brand", "Size", "Suitable for ages", "Capacity", "Power Rating"
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
                "Category", "Product Type", "Subcategory", "Price", "Audience", "Colour", "Material", "Features",
                "Book Genre", "Brand", "Size", "Suitable for ages", "Capacity", "Power Rating"
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
                rel = resolved.relative_to(base_path)
                file_by_rel.setdefault(str(rel), resolved)
            except Exception:
                pass
            file_by_stem.setdefault(p.stem, resolved)

        # Remaining logic for file mapping and display continues here...

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
        for i, u in enumerate(last_urls):
            st.code(u)
            if i == 0:
                st.text_input("Copy first URL", value=u, key="copy_first_url")
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
