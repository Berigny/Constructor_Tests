#!/usr/bin/env python3
"""
Constructor PoC Evaluator
-------------------------
Loads a CSV of test cases, fetches JSON results from a per-row URL,
parses top-3 gifts, and outputs evaluation CSVs. Optionally merges
human scoring to compute metrics and pass/fail.

USAGE:
  python constructor_eval.py \
      --input constructor_tests_sheet1_1.csv \
      --url-col "URL Query" \
      --budget-col Budget \
      --profile-col Profile_Description \
      --filters-col Filters \
      --out-dir out \
      --url-base https://www.kmart.com.au \
      [--human-scores Constructor_Gift_Scoring_Sheet.csv]

NOTES:
- Your input CSV must have one row per test case and a column that contains a URL
  returning JSON (e.g., Constructor API/search endpoint). No auth assumed.
- The JSON schema varies; configure mapping via CLI flags if needed.
- Budget may be a single number or a band like "50-75".

Author: PoC helper
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlparse, unquote, urlencode, parse_qsl, urlunparse, quote


# ----------------------- Helpers -----------------------

def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({"User-Agent": "Constructor-POC-Evaluator/1.0"})
    return s


def parse_budget(value: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if value is None:
        return (None, None)
    v = str(value).strip()
    if not v:
        return (None, None)
    # Match "50-75", "$50-75", "under 30", "≤ 25", "30", "$30"
    vclean = v.replace("$", "").replace("AUD", "").strip()
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$", vclean)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        lo, hi = (min(a, b), max(a, b))
        return (lo, hi)
    # under/less than
    m2 = re.search(r"(under|less\s*than|<=|≤)\s*(\d+(?:\.\d+)?)", vclean, flags=re.I)
    if m2:
        hi = float(m2.group(2))
        return (None, hi)
    # single number treated as "around" with ±20%
    m3 = re.match(r"^\s*(\d+(?:\.\d+)?)\s*$", vclean)
    if m3:
        x = float(m3.group(1))
        return (0.8 * x, 1.2 * x)
    return (None, None)


def in_budget(price: Optional[float], lo: Optional[float], hi: Optional[float]) -> Optional[bool]:
    if price is None:
        return None
    if lo is not None and price < lo:
        return False
    if hi is not None and price > hi:
        return False
    return True


def normalise_price(x: Any) -> Optional[float]:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    s = str(x)
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s)
    except Exception:
        return None


def listify(x: Any) -> List[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x]
    s = str(x)
    # split on common separators
    parts = re.split(r"[|,;/]", s)
    return [p.strip() for p in parts if p.strip()]


# ----------------------- JSON Parsing -----------------------
# We don't know Constructor's JSON schema, so we provide flexible selectors.
# Default assumptions:
#   - Top-level JSON is either a list of items or an object with a key like "results" or "items"
#   - Each item has: id, title/name, price, url, category/tags (optional), rank/score (optional)

POSSIBLE_LIST_KEYS = ["results", "items", "data", "products", "records"]


def extract_items(json_obj: Any) -> List[Dict[str, Any]]:
    # 1) Direct list
    if isinstance(json_obj, list):
        return json_obj
    # 2) Known top-level list keys
    if isinstance(json_obj, dict):
        for k in POSSIBLE_LIST_KEYS:
            if k in json_obj and isinstance(json_obj[k], list):
                return json_obj[k]
        # 3) Constructor-style nesting: response.results may be list or dict of lists
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
            # sometimes nested under "items" or section arrays
            items = resp.get("items")
            if isinstance(items, list):
                return items
    return []


def get_first(d: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def normalise_item(d: Dict[str, Any], rank_idx: int) -> Dict[str, Any]:
    # Many APIs (incl. Constructor) wrap product fields under a `data` key
    base = d.get("data") if isinstance(d, dict) else None
    base = base if isinstance(base, dict) else d
    # try common fields on base first, then fallback to wrapper
    pid = get_first(base, ["id", "product_id", "sku", "uid"]) or get_first(d, ["id", "product_id", "sku", "uid"])  # type: ignore
    title = get_first(base, ["title", "name", "product_title", "productName"]) or get_first(d, ["title", "name"])  # type: ignore
    price_raw = (
        get_first(base, ["price", "sale_price", "amount", "price_value", "final_price"]) or
        get_first(d, ["price", "sale_price", "amount"])
    )
    url = get_first(base, ["url", "product_url", "link", "permalink", "canonical_url"]) or get_first(d, ["url", "product_url"])  # type: ignore
    cat = get_first(base, ["category", "categories"], [])
    tags = get_first(base, ["tags", "labels"], [])
    score = get_first(d, ["score", "rank_score", "relevance"]) or get_first(base, ["score"])  # type: ignore
    # normalise
    price = normalise_price(price_raw)
    cat_list = listify(cat)
    tag_list = listify(tags)
    return {
        "rank": rank_idx + 1,
        "id": pid,
        "title": title,
        "price": price,
        "url": url,
        "categories": "|".join(cat_list) if cat_list else "",
        "tags": "|".join(tag_list) if tag_list else "",
        "score": score,
        "_raw": json.dumps(d, ensure_ascii=False),
    }


# ----------------------- Main -----------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to input CSV of test cases")
    ap.add_argument("--url-col", default="Result_URL", help="Column name with JSON URL per test")
    ap.add_argument("--budget-col", default="Budget", help="Budget column name (optional)")
    ap.add_argument("--profile-col", default="Profile_Description", help="Profile/phrase column (optional)")
    ap.add_argument("--filters-col", default="Filters", help="Filters column (optional)")
    ap.add_argument("--out-dir", default="out", help="Output directory")
    ap.add_argument("--human-scores", default=None, help="Optional CSV/XLSX with human Yes/No per gift")
    ap.add_argument("--topk", type=int, default=3, help="How many top items to evaluate")
    ap.add_argument("--url-base", default="https://www.kmart.com.au", help="Base URL to prepend if item URL is a path")
    ap.add_argument("--print-urls", action="store_true", help="Also print full product URLs to stdout")
    ap.add_argument("--print-urls-only", action="store_true", help="Print only full product URLs (suppress other stdout)")
    ap.add_argument("--print-urls-grouped", action="store_true", help="Print product URLs grouped by test with test name, query, and filters")
    # Prompt emission for LLM-assisted query fixing
    ap.add_argument("--emit-llm-prompts", action="store_true", help="Emit per-test LLM prompts (SYSTEM + USER INPUT) to out/prompts/")
    ap.add_argument("--persona-col", default="Persona", help="Column containing a brief persona descriptor")
    ap.add_argument("--persona-query-encoded-col", default="Persona Query (URL-encoded)", help="Column containing the original NL query (URL-encoded)")
    ap.add_argument("--price-lock-col", default="Price Filter Lock", help="Column containing encoded price filter like [Price]=50-inf")
    ap.add_argument("--llm-fixes-dir", default=None, help="Optional directory of LLM fix JSON files named <Test_ID>.json to auto-apply and re-query")
    args = ap.parse_args()

    # If --print-urls-only is set, we imply --print-urls
    if args.print_urls_only:
        args.print_urls = True
    if args.print_urls_grouped:
        args.print_urls_only = True
        args.print_urls = True

    inp = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "cache"
    cache_dir.mkdir(exist_ok=True)

    # Load input CSV
    df = pd.read_csv(inp)
    for col in [args.url_col]:
        if col not in df.columns:
            print(f"[ERROR] Input missing required column: {col}", file=sys.stderr)
            sys.exit(1)

    s = make_session()

    # Constants for LLM prompt generation
    SYSTEM_PROMPT = (
        "You rewrite a natural-language shopping query to **pull better top-3 gifts** from a retail search API (Constructor).\n"
        "You’ll be given:\n\n"
        "* The **original query** and **constraints** (budget, audience, occasion).\n"
        "* The **API JSON results** (top N).\n"
        "* A **whitelist of useful categories** and a **blocklist of drift categories**.\n\n"
        "Your job:\n\n"
        "1. **Diagnose drift** in the shown results (e.g., beauty, confectionery, party favours, kids).\n"
        "2. **Rewrite the natural-language query** so embeddings anchor to the *right motifs* and *right domain*.\n"
        "3. Propose **include/exclude categories** and **must/negative tokens** to stabilise results.\n"
        "4. Keep **budget** and constraints intact.\n"
        "5. Prefer **adult, maker, or era-specific** cues when appropriate.\n\n"
        "### Heuristics\n\n"
        "* Treat results as **good** if they clearly match the user intent and constraints (title/tags/categories contain the right motifs; price within budget).\n"
        "* Common drift to block: `Beauty`, `Bath & Body`, `Hand Care / Sanitiser`, `Cards / Gift Bags`, `Party Favours & Glow`, `Chocolate / Lollies`, `Kids Art, Craft & Stationery`.\n"
        "* When the theme is era/style (e.g., **90s/Y2K**), inject explicit **motifs** (e.g., `smiley, butterfly clips, checkerboard, neon, cassette, Tamagotchi, Polaroid, scrunchies, Hello Kitty, mood ring`).\n"
        "* When the theme is **maker/craft**, inject **tool/kit/material** terms (e.g., `tool, kit, set, materials, glue gun, precision knife, cutting mat, beads, clay, brushes`).\n"
        "* If catalogue uses `&` in category names, render as **“and”** in URLs.\n\n"
        "### Output format (JSON)\n\n"
        "Return a single JSON object with these keys:\n\n"
        "* `revised_query_text`: string – the new natural-language query (human-readable).\n"
        "* `must_have_tokens`: string[] – words/phrases to add to the query to anchor embeddings.\n"
        "* `negative_tokens`: string[] – words/phrases to add as negatives (or to the NL as “exclude …”).\n"
        "* `include_categories`: string[] – categories to include (names as used by catalogue, `&`→`and` when URL-encoding).\n"
        "* `exclude_categories`: string[] – categories to exclude.\n"
        "* `price_band`: string – the budget to state in-query (e.g., “under $20” or “$20–$60”).\n"
        "* `audience`: string – e.g., “Adults”.\n"
        "* `rationale`: string – brief explanation of what was wrong and what you fixed.\n"
        "* `confidence`: 0–1 – how confident you are the fix will yield 2/3 good results.\n"
        "* `example_titles_expected`: string[] – 3–6 archetypes that should appear if the fix works.\n\n"
        "Ensure the **query text** is natural (no operators needed), and that tokens/categories align with the rationale.\n"
    )

    DEFAULT_WHITELIST = [
        "Craft Supplies", "Artistry", "Jewellery Making", "Jewellery",
        "Hair Accessories", "Yarn and Haberdashery", "Stationery",
        "Notebooks and Journals", "Drawing and Colouring",
        "Electronics", "Gadgets", "Tech", "Gaming", "Cameras",
        "Toys", "Board Games and Puzzles",
    ]
    DEFAULT_BLOCKLIST = [
        "Beauty", "Skincare", "Bath and Body", "Hand Care",
        "Perfumes and Fragrances", "Cards", "Gift Bags",
        "Party Favours and Glow", "Chocolate", "Lollies and Candies",
        "Kids Art, Craft and Stationery", "Novelty Confectionery",
    ]

    def price_lock_to_text(val: Optional[str]) -> str:
        if not val or (isinstance(val, float) and pd.isna(val)):
            return ""
        s = unquote(str(val))
        # Expect like: [Price]=50-inf or [Price]=0-20
        m = re.search(r"\[Price\]=(\d+)(?:-(\d+|inf))?", s)
        if not m:
            return ""
        lo = m.group(1)
        hi = m.group(2)
        if hi is None:
            return f"${lo}"
        if hi == "inf":
            return f"${lo}+"
        return f"${lo}–${hi}"

    def budget_text_to_range(s: str) -> Tuple[Optional[float], Optional[float]]:
        """Parse price_band like 'under $20' or '$20–$60' into lo, hi."""
        if not s:
            return (None, None)
        return parse_budget(s)

    def add_category_filters(params: List[Tuple[str, str]], include_cats: List[str]) -> None:
        for cat in include_cats:
            if not cat:
                continue
            # Heuristic: replace '&' with 'and' for URL consistency if needed
            cat_for_url = cat.replace("&", "and")
            params.append(("filters[Category]", cat_for_url))

    def apply_price_filter(params: List[Tuple[str, str]], lo: Optional[float], hi: Optional[float]) -> None:
        if lo is None and hi is None:
            return
        lo_v = int(lo) if lo is not None else 0
        if hi is None:
            val = f"{lo_v}-inf"
        else:
            hi_v = int(hi)
            val = f"{lo_v}-{hi_v}"
        # remove existing Price filters
        kept = [(k, v) for (k, v) in params if k != "filters[Price]"]
        kept.append(("filters[Price]", val))
        params.clear()
        params.extend(kept)

    def build_revised_url(original_url: str, fix: Dict[str, Any]) -> Optional[str]:
        try:
            pu = urlparse(original_url)
            if pu.scheme not in ("http", "https"):
                return None
            # Build final NL query text, optionally weaving negatives
            q_text = str(fix.get("revised_query_text", "")).strip()
            neg = [str(x) for x in fix.get("negative_tokens", []) if str(x).strip()]
            if neg:
                q_text = f"{q_text}. Exclude {', '.join(neg)}."
            # Replace the natural_language segment
            # Expect path like /v1/search/natural_language/<encoded>
            parts = pu.path.split("/")
            try:
                idx = parts.index("natural_language")
            except ValueError:
                idx = -1
            if idx != -1 and idx + 1 < len(parts):
                parts = parts[: idx + 1] + [quote(q_text, safe="")]  # one segment
            new_path = "/".join(p for p in parts if p)
            new_path = "/" + new_path

            # Start from existing query params and add filters
            params = list(parse_qsl(pu.query, keep_blank_values=True))
            include_cats = [str(x) for x in fix.get("include_categories", []) if str(x).strip()]
            if include_cats:
                add_category_filters(params, include_cats)

            # Apply price band if provided
            lo, hi = budget_text_to_range(str(fix.get("price_band", "")))
            if lo is not None or hi is not None:
                apply_price_filter(params, lo, hi)

            new_query = urlencode(params, doseq=True)
            new_url = urlunparse((pu.scheme, pu.netloc, new_path, pu.params, new_query, pu.fragment))
            return new_url
        except Exception:
            return None

    # Helper to build full URL
    def build_full_url(u: Optional[str]) -> str:
        if u is None:
            return ""
        s = str(u).strip()
        if not s:
            return ""
        if re.match(r"^https?://", s, flags=re.I):
            return s
        base = (args.url_base or "").rstrip("/")
        if base:
            return urljoin(base + "/", s.lstrip("/"))
        return s

    # Fetch & normalise per row
    rows_flat: List[Dict[str, Any]] = []
    grouped_urls: Dict[str, Dict[str, Any]] = {}
    for idx, row in df.iterrows():
        test_id = row.get("Test_ID", f"Row{idx+1}")
        url = str(row[args.url_col]).strip() if pd.notna(row[args.url_col]) else ""
        profile = row.get(args.profile_col, "")
        filters_ = row.get(args.filters_col, "")
        # decode NL query and human-friendly filters
        nl_query_decoded = ""
        if args.persona_query_encoded_col in df.columns:
            qval = row.get(args.persona_query_encoded_col, "")
            nl_query_decoded = unquote(str(qval)) if pd.notna(qval) else ""
        cat_lock = row.get("Category Filter Lock", None)
        cat_text = unquote(str(cat_lock)) if cat_lock is not None and not (isinstance(cat_lock, float) and pd.isna(cat_lock)) else ""
        price_lock = row.get(args.price_lock_col, None)
        price_text = price_lock_to_text(price_lock) if 'price_lock_to_text' in globals() or 'price_lock_to_text' in locals() else ""
        if not price_text and price_lock is not None and not (isinstance(price_lock, float) and pd.isna(price_lock)):
            price_text = unquote(str(price_lock))
        filters_summary = " | ".join([s for s in [cat_text, price_text] if s])
        budget_raw = row.get(args.budget_col, None)
        blo, bhi = parse_budget(budget_raw)

        if not url:
            print(f"[WARN] Empty URL at index {idx}; skipping")
            continue

        cache_file = cache_dir / f"{test_id}.json"
        data = None
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                data = None

        if data is None:
            try:
                # Allow local files via file:// or direct absolute/relative paths
                parsed = urlparse(url)
                if parsed.scheme == "file":
                    p = Path(parsed.path)
                    data = json.loads(p.read_text(encoding="utf-8"))
                elif parsed.scheme in ("http", "https"):
                    r = s.get(url, timeout=10)
                    r.raise_for_status()
                    data = r.json()
                else:
                    p = Path(url)
                    if p.exists():
                        data = json.loads(p.read_text(encoding="utf-8"))
                    else:
                        # fallback to HTTP GET if scheme missing but looks like URL
                        r = s.get("http://" + url, timeout=10)
                        r.raise_for_status()
                        data = r.json()
                cache_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as e:
                print(f"[ERROR] Fetch failed for {test_id}: {e}", file=sys.stderr)
                continue

        # If LLM fixes provided, compute revised URL and results (second pass fetch)
        revised_url = None
        if args.llm_fixes_dir:
            fix_path = Path(args.llm_fixes_dir) / f"{test_id}.json"
            if fix_path.exists():
                try:
                    fix = json.loads(fix_path.read_text(encoding="utf-8"))
                    candidate = build_revised_url(url, fix)
                    if candidate:
                        revised_url = candidate
                        # fetch revised
                        try:
                            r2 = s.get(revised_url, timeout=10)
                            r2.raise_for_status()
                            data = r2.json()
                            (cache_dir / f"{test_id}__revised.json").write_text(
                                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
                            )
                        except Exception as e:
                            print(f"[WARN] Revised fetch failed for {test_id}: {e}")
                except Exception as e:
                    print(f"[WARN] Could not apply LLM fix for {test_id}: {e}")

        items = extract_items(data)
        if not items:
            print(f"[WARN] No items parsed for {test_id}")
            # Even if parsing failed, still emit a prompt with raw JSON if requested
            if args.emit_llm_prompts:
                pass  # fall through to prompt emission section
            else:
                continue

        # take topk in order
        for rank_idx, item in enumerate(items[: args.topk]):
            norm = normalise_item(item, rank_idx)
            # build full URL and attach for printing and output
            full_url = build_full_url(norm.get("url"))
            # budget check
            budget_ok = in_budget(norm.get("price"), blo, bhi)
            norm.update(
                {
                    "Test_ID": test_id,
                    "Profile_Description": profile,
                    "Filters": filters_,
                    "Budget_Lo": blo,
                    "Budget_Hi": bhi,
                    "Budget_OK": budget_ok,
                    "url_full": full_url,
                    "Revised_URL": revised_url or "",
                }
            )
            rows_flat.append(norm)
            # Optional printing of URLs
            if args.print_urls and not args.print_urls_grouped:
                print(full_url)
            if args.print_urls_grouped:
                g = grouped_urls.setdefault(str(test_id), {
                    "persona": str(row.get(args.persona_col, "")),
                    "query": nl_query_decoded,
                    "filters": filters_summary,
                    "urls": []
                })
                if full_url:
                    g["urls"].append(full_url)

        # Emit prompt after processing this test if requested
        if args.emit_llm_prompts:
            prompts_dir = out_dir / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            # Derive original NL query
            nl_q = row.get(args.persona_query_encoded_col, "")
            nl_q = unquote(str(nl_q)) if pd.notna(nl_q) else ""
            # Constraints
            budget_text = row.get(args.budget_col, None)
            if not budget_text or (isinstance(budget_text, float) and pd.isna(budget_text)):
                budget_text = price_lock_to_text(row.get(args.price_lock_col, None))
            audience = "Adults"
            persona = str(row.get(args.persona_col, "")).strip()
            if persona:
                audience = "Adults" if "kid" not in persona.lower() else "Kids"
            # Compose prompt text
            user_input_block = {
                "original_query": nl_q,
                "constraints": {
                    "budget": str(budget_text) if budget_text else "",
                    "audience": audience,
                    "occasion": "",
                },
                "whitelist_categories": DEFAULT_WHITELIST,
                "blocklist_categories": DEFAULT_BLOCKLIST,
                "results_json": data,
            }
            prompt_text = (
                "# SYSTEM (give this to the LLM)\n\n" + SYSTEM_PROMPT + "\n\n" +
                "# USER INPUT (you’ll paste this block each run)\n\n" +
                "```\n" +
                json.dumps(user_input_block, ensure_ascii=False, indent=2) +
                "\n```\n"
            )
            (prompts_dir / f"{test_id}.md").write_text(prompt_text, encoding="utf-8")

    if not rows_flat:
        if not args.emit_llm_prompts:
            print("[ERROR] No items extracted; nothing to write.")
            sys.exit(2)
        else:
            print("[WARN] No items extracted; only LLM prompts were written (if any).")
            return

    flat_df = pd.DataFrame(rows_flat)
    flat_path = out_dir / "results_flat.csv"
    flat_df.to_csv(flat_path, index=False)
    if not args.print_urls_only:
        print(f"[OK] Wrote {flat_path} ({len(flat_df)} rows)")

    # If grouped printing requested, emit grouped sections now
    if args.print_urls_grouped and grouped_urls:
        for tid, meta in grouped_urls.items():
            persona = meta.get("persona", "")
            query = meta.get("query", "")
            filt = meta.get("filters", "")
            header = f"Test: {tid}"
            if persona:
                header += f" | Persona: {persona}"
            if query:
                header += f" | Query: {query}"
            if filt:
                header += f" | Filters: {filt}"
            print(header)
            for u in meta.get("urls", []):
                print(u)
            print("")

    # Simple auto-checks: duplicates per test, empty titles, budget flags
    def eval_autocheck(group: pd.DataFrame) -> Dict[str, Any]:
        titles = group["title"].fillna("").str.strip().tolist()
        ids = group["id"].astype(str).tolist()
        dup_titles = len(titles) != len(set([t.lower() for t in titles if t]))
        dup_ids = len(ids) != len(set(ids))
        budget_flags = group["Budget_OK"].tolist()
        budget_pass_rate = (sum(1 for b in budget_flags if b is True) / len(budget_flags)) if budget_flags else None
        return {
            "dup_titles": dup_titles,
            "dup_ids": dup_ids,
            "budget_pass_rate": budget_pass_rate,
        }

    auto_rows = []
    for tid, g in flat_df.groupby("Test_ID"):
        r = eval_autocheck(g)
        r["Test_ID"] = tid
        auto_rows.append(r)
    auto_df = pd.DataFrame(auto_rows)
    auto_path = out_dir / "eval_autocheck.csv"
    auto_df.to_csv(auto_path, index=False)
    if not args.print_urls_only:
        print(f"[OK] Wrote {auto_path}")

    # Prepare a sheet for human scoring (one row per Test_ID)
    human_cols = ["Test_ID", "Profile_Description", "Filters"]
    for k in range(1, args.topk + 1):
        human_cols += [f"Gift_{k}", f"Gift_{k}_Good"]
    human_rows = []
    for tid, g in flat_df.sort_values(["Test_ID", "rank"]).groupby("Test_ID"):
        row = {
            "Test_ID": tid,
            "Profile_Description": g["Profile_Description"].iloc[0],
            "Filters": g["Filters"].iloc[0],
        }
        for k in range(1, args.topk + 1):
            sub = g[g["rank"] == k]
            title = sub["title"].iloc[0] if not sub.empty else ""
            row[f"Gift_{k}"] = title
            row[f"Gift_{k}_Good"] = ""  # to be filled manually
        human_rows.append(row)
    human_df = pd.DataFrame(human_rows, columns=human_cols)
    human_path = out_dir / "eval_for_human_scoring.csv"
    human_df.to_csv(human_path, index=False)
    if not args.print_urls_only:
        print(f"[OK] Wrote {human_path}")

    # If human scores provided, merge and compute metrics
    if args.human_scores:
        hs_path = Path(args.human_scores)
        if not hs_path.exists():
            print(f"[WARN] human-scores file not found: {hs_path}; skipping merge")
        else:
            if hs_path.suffix.lower() in [".xlsx", ".xls"]:
                hs_df = pd.read_excel(hs_path, sheet_name=0)
            else:
                hs_df = pd.read_csv(hs_path)
            # Expect columns: Test_ID, Gift_1_Good, Gift_2_Good, Gift_3_Good (Yes/No)
            m = human_df[["Test_ID"]].merge(hs_df, on="Test_ID", how="left")

            def yes_no_to_int(x):
                s = str(x).strip().lower()
                if s in ("yes", "y", "1", "true", "t"):
                    return 1
                if s in ("no", "n", "0", "false", "f"):
                    return 0
                return None

            good_counts = []
            for _, row in m.iterrows():
                cnt = 0
                for k in range(1, args.topk + 1):
                    v = row.get(f"Gift_{k}_Good", None)
                    vi = yes_no_to_int(v)
                    if vi == 1:
                        cnt += 1
                good_counts.append(cnt)
            m["Good_Count"] = good_counts
            m["Case_Pass"] = m["Good_Count"] >= 2

            # Metrics
            total_cases = len(m)
            case_pass_rate = m["Case_Pass"].mean() if total_cases else 0.0
            total_gifts = total_cases * args.topk
            # Flatten "good" cells
            good_vals = []
            for k in range(1, args.topk + 1):
                good_vals.extend(m.get(f"Gift_{k}_Good", []).tolist())
            good_yes = sum(1 for x in good_vals if str(x).strip().lower() in ("yes", "y", "1", "true", "t"))
            good_rate = (good_yes / total_gifts) if total_gifts else 0.0

            summary = pd.DataFrame(
                {
                    "Metric": [
                        "Number of Tests",
                        "Total Gifts",
                        "Overall Good Rate",
                        "Case Pass Rate (>=2/3)",
                    ],
                    "Value": [total_cases, total_gifts, good_rate, case_pass_rate],
                }
            )
            summary_path = out_dir / "summary_metrics.csv"
            summary.to_csv(summary_path, index=False)
            if not args.print_urls_only:
                print(f"[OK] Wrote {summary_path}")
            merged_path = out_dir / "human_scored_merged.csv"
            m.to_csv(merged_path, index=False)
            if not args.print_urls_only:
                print(f"[OK] Wrote {merged_path}")


if __name__ == "__main__":
    main()
