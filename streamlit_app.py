import os
import json
import uuid
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
from urllib.parse import urljoin
from datetime import datetime
import csv
import numpy as np
import streamlit as st


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


# ----------------------- Images Tab (Greedy Tree) -----------------------
@st.cache_data
def load_meta_df(meta_path: str) -> Optional["pd.DataFrame"]:
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


def build_greedy_tree(leaf_ids: List[int], embeddings: np.ndarray) -> Any:
    n = len(leaf_ids)
    if n == 0:
        return None
    if n == 1:
        return leaf_ids[0]
    if n == 2:
        a, b = leaf_ids[0], leaf_ids[1]
        return {"left": a, "right": b, "pair_idx": (a, b)}
    best_pair = None
    best_balance = None
    for i in leaf_ids:  # consider pivots drawn from current pool
        for j in leaf_ids:
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
        return {"left": build_greedy_tree(mid_left, embeddings), "right": build_greedy_tree(mid_right, embeddings), "pair_idx": (mid_left[0], mid_right[0])}
    i, j, left, right = best_pair
    # Guard against degenerate splits
    if len(left) == 0 or len(right) == 0 or (len(left) == n or len(right) == n):
        mid_left = leaf_ids[::2]
        mid_right = leaf_ids[1::2]
        return {"left": build_greedy_tree(mid_left, embeddings), "right": build_greedy_tree(mid_right, embeddings), "pair_idx": (mid_left[0], mid_right[0])}
    return {"left": build_greedy_tree(left, embeddings), "right": build_greedy_tree(right, embeddings), "pair_idx": (i, j)}


def walk_tree(tree: Any, bits: List[int]) -> Any:
    node = tree
    for b in bits:
        node = node["left"] if b == 0 else node["right"]
    return node


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


def build_query_text(relationship: str, gender: Optional[str], age_text: Optional[str], interest: str, price_phrase: Optional[str] = None, generation_label: Optional[str] = None) -> str:
    rel = prettify_token(relationship)
    gen = prettify_token(gender) if gender else None
    intr = prettify_token(interest)
    parts = [rel]
    if gen:
        parts.append(gen)
    if age_text:
        parts.append(age_text)
    who = " ".join(parts)
    # Persona and tone: Australian, value-conscious Kmart shopper with trade-down mindset.
    tail = f" within {price_phrase}" if price_phrase else ""
    # Demographic-tailored persona
    gen_tone = ""
    if generation_label:
        gl = generation_label.lower()
        if "alpha" in gl:
            gen_tone = "For Gen Alpha recipients, lean into playful, hands-on imagination and discovery, guided by practical value for parents. "
        elif "gen z" in gl or "z (" in gl:
            gen_tone = "For Gen Z, highlight expressive, trend-aware choices that feel fun and personal without stretching the budget. "
        elif "millennial" in gl or "gen y" in gl or "y (" in gl:
            gen_tone = "For Millennials, emphasise functional quality, smart savings, and pieces that fit everyday routines. "
        elif "gen x" in gl or "x (" in gl:
            gen_tone = "For Gen X, focus on dependable practicality and durable basics that offer excellent value. "
        elif "boomer" in gl:
            gen_tone = "For Boomers, foreground comfort, ease-of-use, and reliable value. "
        elif "silent" in gl:
            gen_tone = "For the Silent Generation, prefer classic, comfortable, easy-to-use items with clear value. "
    persona = (
        "Australian Kmart shopper profile: value-conscious and trade-down oriented; "
        "prioritise affordable, great value, budget-friendly items that are practical, reliable, and durable. "
        "Prefer good alternatives to premium brands, focusing on smart savings and everyday usefulness. "
        + gen_tone
    )
    # Final natural language query (avoid the word 'gift' to reduce gift-card bias)
    return (
        f"{persona}"
        f"Thoughtful ideas for a {who} who enjoys {intr}{tail}. "
        f"Use Australian English and context; match relatable use-cases and everyday needs."
    )


def sanitize_query(q: str) -> str:
    """Remove 'gift'/'gifts' tokens from query to avoid gift card bias."""
    s = re.sub(r"\b(giftcards?|gifts?)\b", "", q, flags=re.IGNORECASE)
    # Cleanup extra spaces
    s = re.sub(r"\s+", " ", s).strip()
    # Remove stray spaces before punctuation
    s = re.sub(r"\s+([.,;:!?])", r"\1", s)
    return s


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
    # Prefer categories.txt if present (authoritative list)
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
                        # ignore product types for Category filtering
                        section = "product_types"
                        continue
                    if section == "categories":
                        cats.append(line.replace("  ", " ").strip())
            if cats:
                return list(dict.fromkeys(cats))
    except Exception:
        pass
    # Fallback to reading categories from example.json facets
    try:
        with open(example_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        facets = ((data.get("response") or {}).get("facets") or [])
        for facet in facets:
            if str(facet.get("name")).lower() == "category":
                for opt in facet.get("options", []):
                    name = opt.get("display_name") or opt.get("value")
                    if name:
                        cats.append(str(name))
        if cats:
            return list(dict.fromkeys(cats))
    except Exception:
        pass
    return []


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
    t = interest.lower()
    cat_map = [
        ("cooking", ["Food & Drink", "Kitchen Appliances", "Utensils and Gadgets", "Food Preparation", "Cookware", "Bakeware", "Serveware"]),
        ("baking", ["Food & Drink", "Bakeware", "Kitchen Appliances", "Utensils and Gadgets"]),
        ("gardening", ["Home & Pets", "Home and Living", "Garden"]),
        ("relaxation", ["Health & Wellbeing", "Body & Spirit", "Home & Living", "Decor Accessories"]),
        ("reading", ["Books", "Notebooks and Journals", "Stationery"]),
        ("tech", ["Electronics", "Gadgets", "Tech"]),
        ("gaming", ["Gaming", "Electronics", "Tech"]),
        ("diy", ["Craft Supplies", "Artistry", "Tools"]),
        ("arts", ["Artistry", "Craft Supplies", "Drawing and Colouring", "Jewellery Making", "Yarn and Haberdashery"]),
        ("creativity", ["Artistry", "Craft Supplies"]),
        ("board_games", ["Board Games and Puzzles", "Toys"]),
        ("music", ["Music", "Musical Instruments", "Electronics"]),
        ("fashion", ["Fashion", "Accessories", "Jewellery", "Hair Accessories"]),
        ("home", ["Home & Living", "Home Decor", "Home and Living"]),
        ("travel", ["Travel", "Sport and Outdoor"]),
        ("sustainable", ["Sustainable"]),
        ("pet", ["Home & Pets"]) ,
    ]
    out: List[str] = []
    for key, cats in cat_map:
        if key in t:
            out.extend(cats)
    # generic fallback from tokens in interest
    if not out:
        intr = prettify_token(interest)
        if "craft" in intr.lower():
            out.extend(["Craft Supplies", "Artistry"]) 
    # If example.json provides a whitelist of valid categories, intersect
    if restrict_to_whitelist:
        canonical = build_category_canonical_map()
        resolved: List[str] = []
        for c in out:
            key = _norm_cat(c)
            if key in canonical:
                resolved.append(canonical[key])
        # If nothing matched the whitelist, send no category filters rather than invalid ones
        out = resolved
    return list(dict.fromkeys(out))


def make_url(base: str, query: str, key: str, price_filter: Optional[str], include_categories: List[str], per_page: int = 10, page: int = 1) -> str:
    from urllib.parse import urlencode, quote
    params = {
        "key": key,
        "i": st.session_state.get("constructor_i") or str(uuid.uuid4()),
        # Force s=1 per user observation for JSON responses
        "s": 1,
        "num_results_per_page": per_page,
        "page": page,
        "sort_by": "relevance",
    }
    st.session_state["constructor_i"] = params["i"]
    if price_filter:
        params["filters[Price]"] = price_filter
    for cat in include_categories:
        # multiple category filters allowed by repeating the param
        pass
    # Build query string with possible repeated category params
    kv = list(params.items())
    # Canonicalize categories against whitelist when possible
    canonical = build_category_canonical_map()
    added = set()
    for cat in include_categories:
        c = canonical.get(_norm_cat(cat), cat)
        if c not in added:
            kv.append(("filters[Category]", c))
            added.add(c)
    # Ensure query does not contain 'gift'/'gifts'
    clean_q = sanitize_query(query)
    # Encode query parameters using %20 for spaces (not '+') to match Constructor expectations
    qs = urlencode(kv, doseq=True, quote_via=quote)
    return f"{base}/v1/search/natural_language/{quote(clean_q)}?{qs}"


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
    i = st.session_state.get("constructor_i")
    s_id = st.session_state.get("constructor_s")
    if not i:
        i = str(uuid.uuid4())
        st.session_state["constructor_i"] = i
    if not s_id:
        s_id = str(uuid.uuid4())
        st.session_state["constructor_s"] = s_id

    url = f"{base}/v1/search/natural_language/{requests.utils.quote(query)}"
    params = {
        "key": key,
        "i": i,
        "s": s_id,
        "num_results_per_page": per_page,
        "page": page,
        "sort_by": "relevance",
    }
    if price_filter:
        params["filters[Price]"] = price_filter

    r = requests.get(url, params=params, timeout=20)
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
st.set_page_config(page_title="Constructor Gift Finder", page_icon="🎁", layout="centered")
st.title("Gift Finder (Constructor)")
st.caption("Choose match mode and amounts, then select recipient details.")

quiz = load_quiz()

with st.sidebar:
    st.header("Settings")
    default_key = os.environ.get("CONSTRUCTOR_PUBLIC_KEY") or os.environ.get("CONSTRUCTOR_API_KEY") or os.environ.get("CONSTRUCTOR_KEY") or ""
    raw_key = st.text_input("Public search key (value or 'key=…')", value=default_key)
    api_key = normalize_public_key(raw_key)
    if api_key:
        os.environ["CONSTRUCTOR_PUBLIC_KEY"] = api_key
    base_url = st.text_input("Constructor base", value=os.environ.get("CONSTRUCTOR_BASE_URL", "https://ac.cnstrc.com"))
    os.environ["CONSTRUCTOR_BASE_URL"] = base_url
    st.markdown("Uses the front-end natural language search URL that returns JSON.")
    per_page = st.slider("Results per iteration", min_value=10, max_value=50, value=24, step=2)
    pages_per_iter = st.slider("Pages per iteration", min_value=1, max_value=3, value=1)
    # Defaults ON (no toggles): include budget in query, strict budget, logging, restrict to whitelist
    include_budget_in_query = True
    strict_budget = True
    enable_logging = True
    restrict_cats = True

# Global controls above recipient selection
st.subheader("Match Controls")
match_type = st.radio("Match type", options=["Constructor", "Powered-up"], horizontal=True, index=1)
if match_type == "Powered-up":
    queries_opt = st.selectbox("Amount of queries", options=[1,2,3,4,5], index=2)
else:
    queries_opt = 1
gifts_opt = st.selectbox("Number of gifts", options=[1,2,3,4,5], index=2)

st.subheader("Who is the gift for?")

who_options = list((quiz.get("who") or {}).keys())
who = st.selectbox("Recipient type", options=who_options, index=who_options.index("parent") if "parent" in who_options else 0)

node = quiz["who"][who]

gender = None
age = None
interest = None
budget_label = None

if who == "pet":
    pet_types = list((node.get("pet_type") or {}).keys())
    pet = st.selectbox("Pet type", options=pet_types)
    pet_node = node["pet_type"][pet]
    interests = pet_node.get("interests", [])
    interest = st.selectbox("Interest", options=interests)
    budgets = pet_node.get("budget", [])
    budget_label = st.selectbox("Budget", options=budgets)
    relationship = f"{pet}"
else:
    genders = list((node.get("gender") or {}).keys())
    gender = st.selectbox("Gender", options=genders)
    # Generation selection + range slider for precision
    GENERATIONS = [
        ("Gen Alpha (1–14)", 1, 14),
        ("Gen Z (13–28)", 13, 28),
        ("Millennials (29–44)", 29, 44),
        ("Gen X (45–60)", 45, 60),
        ("Boomers (61–79)", 61, 79),
        ("Silent Generation (80–97)", 80, 97),
    ]
    gen_labels = [g[0] for g in GENERATIONS]
    gen_idx_default = 1 if "Gen Z (13–28)" in gen_labels else 0
    gen_label = st.selectbox("Generation", options=gen_labels, index=gen_idx_default)
    gmin, gmax = next((a, b) for (lbl, a, b) in GENERATIONS if lbl == gen_label)
    age_range = st.slider("Age range", min_value=1, max_value=97, value=(gmin, gmax))

    # Map selected age range to the closest available QuizIA age bucket
    available_buckets = list(((node["gender"][gender]).get("age") or {}).keys())
    def _bucket_range(bk: str) -> Tuple[int, int]:
        if bk == "0_2":
            return (0,2)
        if bk == "3_5":
            return (3,5)
        if bk == "6_8":
            return (6,8)
        if bk == "9_12":
            return (9,12)
        if bk == "13_17":
            return (13,17)
        if bk == "18_plus":
            return (18, 120)
        return (0, 120)
    rep_age = int((age_range[0] + age_range[1]) // 2)
    # choose bucket that contains rep_age or is closest by mid-point
    best_bk = None
    best_dist = 10**9
    for bk in available_buckets:
        lo, hi = _bucket_range(bk)
        mid = (lo + hi) / 2
        dist = 0 if (lo <= rep_age <= hi) else abs(rep_age - mid)
        if dist < best_dist:
            best_dist = dist
            best_bk = bk
    # Fallback
    age_bucket = best_bk or (available_buckets[0] if available_buckets else "18_plus")
    age = age_bucket
    age_node = node["gender"][gender]["age"][age_bucket]
    interests = age_node.get("interests", [])
    interest = st.selectbox("Interest", options=interests)
    budgets = age_node.get("budget", [])
    budget_label = st.selectbox("Budget", options=budgets)
    relationship = who


st.divider()

col1, col2 = st.columns([1, 2])
with col1:
    go = st.button("Find best 3 products", type="primary")
with col2:
    st.write("")

if go:
    # Build query and price filter
    lo, hi = parse_budget_range(budget_label or "")
    pf = price_filter_value(lo, hi)
    age_text_display = None
    if who != "pet":
        age_text_display = f"ages {age_range[0]}–{age_range[1]}"
    p_phrase = price_text(*parse_budget_range(budget_label or "")) if include_budget_in_query else None
    current_generation = gen_label if who != "pet" else None
    q = build_query_text(relationship, None if who == "pet" else gender, age_text_display, interest or "", p_phrase, current_generation)

    chosen: List[Dict[str, Any]] = []
    seen_ids: set = set()
    errors: List[str] = []
    with st.spinner("Fetching and refining selections..."):
        include_cats = interest_to_categories(interest or "", restrict_to_whitelist=restrict_cats)
        if match_type == "Constructor":
            try:
                # Single query with fallbacks; take N gifts in the order returned
                items_raw, _urls_used = fetch_aggregate_items(
                    base_url, q, api_key, pf, include_cats, per_page=max(per_page, gifts_opt), pages=1
                )
                items = [normalise_item(it) for it in items_raw]
                # If no in-budget items and we have a target band, expand to nearest two bands
                if not any_in_budget(items, lo, hi) and (lo is not None or hi is not None):
                    expanded_items: List[Dict[str, Any]] = []
                    msgs = []
                    for (nlo, nhi) in neighbor_price_bands(lo, hi):
                        npf = price_filter_value(nlo, nhi)
                        if npf == pf:
                            continue
                        raw2, _ = fetch_aggregate_items(
                            base_url, q, api_key, npf, include_cats, per_page=max(per_page, gifts_opt), pages=1
                        )
                        expanded_items.extend([normalise_item(it) for it in raw2])
                        msgs.append(price_text(nlo, nhi) or "")
                    if expanded_items:
                        items = expanded_items
                        try:
                            st.toast(f"Expanded price to nearby bands: {', '.join([m for m in msgs if m])}")
                        except Exception:
                            pass
                chosen = items[:gifts_opt]
            except Exception as e:
                errors.append(str(e))
        else:
            # Powered-up: run queries_opt iterations, alternating convergent (focused) and divergent (creative) queries.
            all_items: List[Dict[str, Any]] = []
            q_base = q
            q_iter = q_base
            last_best: Optional[Dict[str, Any]] = None
            for iter_idx in range(1, queries_opt + 1):
                try:
                    # Determine take: odd -> convergent, even -> divergent
                    if iter_idx == 1:
                        q_iter = q_base  # first is convergent base
                    elif iter_idx % 2 == 0:
                        q_iter = divergent_variant(q_base, interest or "", include_cats, price_text(lo, hi))
                    else:
                        # convergent: refine toward last best if available, else use base
                        q_iter = refine_query(q_base, last_best) if last_best else q_base

                    # fetch across configured pages with fallbacks
                    items_raw, _urls_used = fetch_aggregate_items(
                        base_url, q_iter, api_key, pf, include_cats, per_page=per_page, pages=pages_per_iter
                    )
                    # dedupe per-iteration
                    seen_local = set()
                    uniq_raw = []
                    for it in items_raw:
                        pid = it.get("id") or (it.get("data") or {}).get("id") or it.get("url")
                        pid = str(pid)
                        if pid and pid not in seen_local:
                            seen_local.add(pid)
                            uniq_raw.append(it)
                    items = [normalise_item(it) for it in uniq_raw]
                    # If no in-budget items, expand by two nearby bands
                    if not any_in_budget(items, lo, hi) and (lo is not None or hi is not None):
                        for (nlo, nhi) in neighbor_price_bands(lo, hi):
                            npf = price_filter_value(nlo, nhi)
                            raw2, _ = fetch_aggregate_items(
                                base_url, q_iter, api_key, npf, include_cats, per_page=per_page, pages=pages_per_iter
                            )
                            items.extend([normalise_item(it) for it in raw2])
                        try:
                            txts = [price_text(*b) for b in neighbor_price_bands(lo, hi)]
                            st.toast(f"Expanded price to nearby bands: {', '.join([t for t in txts if t])}")
                        except Exception:
                            pass
                    all_items.extend(items)
                    # track best for next convergent refinement and expand categories
                    if items:
                        def _score(it: Dict[str, Any]) -> float:
                            base_s = score_item(it, interest or "", lo, hi)
                            if strict_budget:
                                price = it.get("price")
                                in_b = True
                                if price is not None:
                                    if lo is not None and price < lo:
                                        in_b = False
                                    if hi is not None and price > hi:
                                        in_b = False
                                base_s += 2.0 if in_b else -1.0
                            return base_s
                        best = sorted(items, key=_score, reverse=True)[0]
                        last_best = best
                        cat_field = best.get("categories")
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
                    errors.append(str(e))
            # After all queries, score globally and pick top unique
            def _score_global(it: Dict[str, Any]) -> float:
                base_s = score_item(it, interest or "", lo, hi)
                if strict_budget:
                    price = it.get("price")
                    in_b = True
                    if price is not None:
                        if lo is not None and price < lo:
                            in_b = False
                        if hi is not None and price > hi:
                            in_b = False
                    base_s += 2.0 if in_b else -1.0
                return base_s
            ranked = sorted(all_items, key=_score_global, reverse=True)
            seen_ids_global = set()
            chosen = []
            for it in ranked:
                pid = it.get("id") or it.get("url")
                if pid and pid not in seen_ids_global and it.get("url"):
                    chosen.append(it)
                    seen_ids_global.add(pid)
                if len(chosen) >= gifts_opt:
                    break

    if errors:
        st.warning("\n".join(errors))

    if chosen:
        st.subheader("Top picks")
        for idx, it in enumerate(chosen, start=1):
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
            st.markdown(f"{idx}. [{title}]({url}) {meta}")
        with st.expander("Search URLs used"):
            # Reconstruct displayed search URLs for transparency
            include_cats = interest_to_categories(interest or "", restrict_to_whitelist=restrict_cats)
            lo, hi = parse_budget_range(budget_label or "")
            pf = price_filter_value(lo, hi)
            if match_type == "Constructor":
                for p in range(1, pages_per_iter + 1):
                    url = make_url(base_url, q, api_key, pf, include_cats, per_page=per_page, page=p)
                    st.code(url)
            else:
                q_base = q
                last_best = chosen[0] if chosen else None
                for iter_idx in range(1, queries_opt + 1):
                    if iter_idx == 1:
                        q_iter = q_base
                    elif iter_idx % 2 == 0:
                        q_iter = divergent_variant(q_base, interest or "", include_cats, price_text(lo, hi))
                    else:
                        q_iter = refine_query(q_base, last_best) if last_best else q_base
                    for p in range(1, pages_per_iter + 1):
                        url = make_url(base_url, q_iter, api_key, pf, include_cats, per_page=per_page, page=p)
                        st.code(url)
    else:
        st.info("No products found. Try a different selection or budget.")

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

# ----------------------- Tabs: Images and URLs -----------------------
st.divider()
tabs = st.tabs(["Images", "URLs"])

with tabs[0]:
    st.subheader("Pick by images (greedy tree)")
    meta_path = st.text_input("Metadata path", value=os.path.join("unsplash_images", "metadata.json"))
    df_meta = load_meta_df(meta_path)
    if df_meta is None or df_meta.empty:
        st.info("Provide a valid metadata.json from Unsplash downloads.")
    else:
        # Cache/rebuild embeddings if path changed
        key_path = f"img_meta_path"
        key_tree = f"img_tree"
        key_bits = f"img_path_bits"
        key_emb = f"img_embeddings"
        if st.session_state.get(key_path) != meta_path:
            st.session_state[key_path] = meta_path
            st.session_state[key_bits] = []
            emb = embed_texts(df_meta["text"].tolist())
            st.session_state[key_emb] = emb
            st.session_state[key_tree] = build_greedy_tree(list(range(len(df_meta))), emb)
        # current node
        bits = st.session_state.get(key_bits, [])
        tree = st.session_state.get(key_tree)
        emb = st.session_state.get(key_emb)
        node = walk_tree(tree, bits)
        if isinstance(node, dict):
            i, j = node["pair_idx"]
            left_row = df_meta.iloc[i]
            right_row = df_meta.iloc[j]
            col1, col2 = st.columns(2)
            with col1:
                st.image(f"https://source.unsplash.com/{left_row['photo_id']}/600x400", use_column_width=True, caption=left_row.get("alt_description") or "")
                if st.button("Left", key="img_left"):
                    st.session_state[key_bits].append(0)
                    st.rerun()
            with col2:
                st.image(f"https://source.unsplash.com/{right_row['photo_id']}/600x400", use_column_width=True, caption=right_row.get("alt_description") or "")
                if st.button("Right", key="img_right"):
                    st.session_state[key_bits].append(1)
                    st.rerun()
        else:
            leaf_idx = node
            leaf = df_meta.iloc[leaf_idx]
            st.success("Image vibe selected")
            st.image(f"https://source.unsplash.com/{leaf['photo_id']}/600x400", use_column_width=True, caption=leaf.get("alt_description") or "")
            # Build concept from tags + alt
            tags = leaf.get("tags", [])
            if not isinstance(tags, list):
                tags = []
            tag_text = ", ".join([str(t) for t in tags][:6])
            alt_text = str(leaf.get("alt_description") or "")
            concept = (alt_text + "; " + tag_text).strip("; ")
            st.write(f"Concept: {concept}")
            if st.button("Find products from image vibe", key="img_go"):
                # Use Powered-up flow to fetch products with this concept
                include_cats = interest_to_categories(concept or "", restrict_to_whitelist=True)
                q_base = build_query_text("someone", None, None, concept or "", None, None)
                chosen_img: List[Dict[str, Any]] = []
                errors_img: List[str] = []
                all_items: List[Dict[str, Any]] = []
                last_best = None
                for iter_idx in range(1, (queries_opt if match_type == "Powered-up" else 1) + 1):
                    try:
                        if iter_idx == 1:
                            q_iter = q_base
                        elif iter_idx % 2 == 0:
                            q_iter = divergent_variant(q_base, concept or "", include_cats, None)
                        else:
                            q_iter = refine_query(q_base, last_best) if last_best else q_base
                        items_raw, _ = fetch_aggregate_items(base_url, q_iter, api_key, None, include_cats, per_page=per_page, pages=pages_per_iter)
                        # dedupe
                        seen_local = set()
                        uniq_raw = []
                        for it in items_raw:
                            pid = it.get("id") or (it.get("data") or {}).get("id") or it.get("url")
                            pid = str(pid)
                            if pid and pid not in seen_local:
                                seen_local.add(pid)
                                uniq_raw.append(it)
                        items = [normalise_item(it) for it in uniq_raw]
                        all_items.extend(items)
                        if items:
                            def _score_img(it: Dict[str, Any]) -> float:
                                return score_item(it, concept or "", None, None)
                            best = sorted(items, key=_score_img, reverse=True)[0]
                            last_best = best
                    except Exception as e:
                        errors_img.append(str(e))
                # rank and pick
                ranked = sorted(all_items, key=lambda it: score_item(it, concept or "", None, None), reverse=True)
                seen = set()
                for it in ranked:
                    pid = it.get("id") or it.get("url")
                    if pid and pid not in seen and it.get("url"):
                        chosen_img.append(it)
                        seen.add(pid)
                    if len(chosen_img) >= gifts_opt:
                        break
                if errors_img:
                    st.warning("\n".join(errors_img))
                if chosen_img:
                    st.subheader("Top picks (from image vibe)")
                    for idx, it in enumerate(chosen_img, start=1):
                        title = it.get("title") or "View product"
                        def _full(u: str) -> str:
                            if not u:
                                return ""
                            su = str(u).strip()
                            if su.startswith("http://") or su.startswith("https://"):
                                return su
                            return urljoin("https://www.kmart.com.au/", su.lstrip("/"))
                        url = _full(it.get("url") or "")
                        st.markdown(f"{idx}. [{title}]({url})")
                else:
                    st.info("No products found from image vibe.")

with tabs[1]:
    st.subheader("URLs")
    st.info("Coming soon")
