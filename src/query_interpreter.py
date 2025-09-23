"""
query_interpreter.py
Hybrid interpreter with:
  - metadata-driven inference of style, palette, cohort
  - multi-query composer (Fashion, Books, Tech, Outdoors, Home)
  - optional LLM rewrite with strict allow-list
  - confidence scoring; suggest probing images if signal is weak

Assumptions:
  unsplash_images/metadata.json contains, per photo:
    {
      "id": "ph_001",
      "tags": ["art","retro","vinyl"],
      "style": ["minimalist","90s","casual"],   # optional
      "palette": ["black","blue","neutral"],    # optional
      "cohort": "Gen X"                          # optional
    }

Usage (typical):
  qi = QueryInterpreter()
  res = qi.interpret(
      tokens=filtered_tokens,            # from QueryBuilder
      categories=categories,             # from QueryBuilder
      photo_ids=selected_photo_ids,      # from UI
      budget_aud=(25,100),
      use_llm=True
  )
  if res["need_more_images"]:
      # Ask UI to show res["probe_tags"] / res["probe_axes"] focused images
  else:
      # Send res["queries_multi"] (bucket, query) to Constructor
"""

from __future__ import annotations
import json, os, math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Literal

from .demographics import infer_demographics_from_photos

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_METADATA_PATH = "unsplash_images/metadata.json"
DEFAULT_MANIFEST_PATH = "queries_manifest.json"

Bucket = Literal["Fashion","Books","Tech","Outdoors","Home","Entertainment"]

FORBIDDEN = {
    "girl","girls","boy","boys","woman","women","man","men","female","male",
    "adult","adults","kids","children","mum","mom","dad","grandma","grandpa",
    "lady","gentleman"
}

# Lightweight vibe → cohort hints (fallback if metadata lacks cohort)
TOKEN_TO_COHORT = {
    "vintage": "Gen X / Millennial nostalgia",
    "retro": "Millennial nostalgia",
    "90s": "Gen X / Millennial",
    "aesthetic": "Gen Z",
    "festival": "Gen Z / Millennial",
    "classic": "Gen X / Boomer",
    "polaroid": "Gen X / Millennial",
    "neon": "Gen Z",
}

SAFE_RECIPIENT_TOKENS = {"couple", "ring", "wedding", "anniversary"}

# Token → product seed terms (deterministic)
TOKEN_TO_PRODUCT_TERMS: Dict[str, List[str]] = {
    "summer": ["sunglasses","sun hat","beach towel","cooler bag"],
    "sun": ["sunscreen set","cap","sunglasses"],
    "beach": ["beach towel","dry bag","sand-proof blanket"],
    "outdoor": ["insulated bottle","daypack","picnic set","camping mug"],
    "hiking": ["trekking socks","hydration flask","compact first-aid kit"],
    "camping": ["enamel mug","compact lantern","firestarter kit"],
    "window": ["indoor plant kit","aromatherapy diffuser","scented candle","ceramic vase"],
    "home": ["throw blanket","planter","coaster set"],
    "retro": ["vinyl record","retro poster","polaroid film"],
    "vintage": ["vinyl record","analogue photo album"],
    "vinyl": ["record","anti-static brush","slipmat"],
    "coffee": ["pour-over kit","hand grinder","ceramic mug","cold brew bottle"],
    "tea": ["loose leaf sampler","teapot infuser"],
    "gaming": ["controller stand","desk mat","headset holder"],
    "books": ["gift book","journal","reading light"],
    "book": ["gift book","journal","reading light"],
    "crafts": ["ceramic kit","embroidery kit"],
    "travel": ["packing cubes","weekender bag","passport wallet"],
    "minimalist": ["clean desk organiser","wireless charger","matte water bottle"],
    "art": ["art print","museum membership","colouring book for adults"],
    "philosophy": ["gift book","journal"],
    "tech": ["power bank","wireless charger","bluetooth tracker"],
    "nature": ["insulated bottle","hiking socks"],
    "anniversary": ["champagne gift set","couples journal","photo frame"],
    "wedding": ["champagne flutes","keepsake frame","ring dish"],
    "couple": ["matching mugs","experience voucher","photo frame"],
    "ring": ["ring dish","jewellery tray"],
}

CATEGORY_TO_DEFAULT_TERMS: Dict[str, List[str]] = {
    "Outdoors": ["sunglasses","insulated bottle","daypack","picnic set","camping mug"],
    "Home": ["aromatherapy diffuser","scented candle","indoor plant kit","ceramic vase"],
    "Tech": ["power bank","wireless charger","bluetooth tracker"],
    "Entertainment": ["board game","vinyl record","bluetooth speaker"],
    "Books": ["gift book","journal","reading light"],
    "Fashion": ["cap","sunglasses","scarf"],
    "Food": ["gourmet chocolate","coffee beans","tea sampler"],
    "Crafts": ["ceramic kit","embroidery kit","woodcraft kit"],
    "Sports": ["yoga mat","microfibre towel","sports bottle"],
    "Travel": ["packing cubes","weekender bag","passport wallet"],
    "Occasion": ["anniversary keepsake","wedding photo frame","champagne flutes"],
    "Jewellery": ["bracelet","necklace","ring dish"],
}

BUCKET_TEMPLATES: Dict[Bucket, str] = {
    "Fashion": "{styles} {palette} clothes {recipient_phrase} {cohort_twist} under {hi}",
    "Books": "books and ideas on {themes} {recipient_phrase} {cohort_twist} under {hi}",
    "Tech": "tech and gadgets {style_practical} {recipient_phrase} {cohort_twist} under {hi}",
    "Outdoors": "{palette} outdoor gear and apparel {recipient_phrase} {cohort_twist} under {hi}",
    "Home": "{palette} home items {style_practical} {recipient_phrase} {cohort_twist} under {hi}",
    "Entertainment": "{styles} {palette} entertainment and experiences {recipient_phrase} {cohort_twist} under {hi}",
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

# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try: return json.loads(path.read_text())
    except Exception: return None

def _normalise(xs: List[str]) -> List[str]:
    out = []
    for t in xs or []:
        t = (t or "").strip().lower()
        if not t or t in FORBIDDEN: continue
        t = t.replace("_","-")
        if t == "cosy": t = "cozy"
        out.append(t)
    # dedupe preserve order
    seen, keep = set(), []
    for t in out:
        if t not in seen:
            seen.add(t); keep.append(t)
    return keep

def _entropy_from_counts(counter: Counter) -> float:
    total = sum(counter.values()) or 1
    ent = 0.0
    for _, n in counter.items():
        p = n / total
        if p > 0:
            ent -= p * math.log2(p)
    return ent

def _recipient_phrase(recipient: Optional[str]) -> str:
    rec = (recipient or "me").lower()
    return {
        "me": "for me",
        "man": "for men",
        "woman": "for women",
        "teen": "for teens",
        "kid": "for kids",
        "couple": "for couples",
        "family": "for families",
    }.get(rec, "for me")

def _palette_phrase(colours: List[str] | None) -> str:
    if not colours: return ""
    keep = [c for c in colours if c in {"black","blue","neutral","earthy"}]
    return ("in " + " and ".join(keep)) if keep else ""

def _styles_phrase(styles: List[str] | None) -> Tuple[str, str]:
    if not styles: return "", ""
    mapped = [STYLE_PHRASES.get(s.lower(), s.lower()) for s in styles]
    style_str = " ".join(sorted(set(mapped)))
    practical = "that are practical" if "practical" in mapped else "that are plain and practical" if "plain" in mapped else ""
    return style_str, practical

def _themes_from_tokens(tokens: List[str]) -> str:
    keep = [t for t in tokens if t in {"philosophy","art","tech","nature","design","book"}]
    return " and ".join(sorted(set(keep))) if keep else "philosophy and tech"

# ---------------------------------------------------------------------------
# LLM rewrite (optional, allowed-terms only)
# ---------------------------------------------------------------------------

def _llm_rewrite(allowed_terms: List[str], cohort: Optional[str], budget: Optional[Tuple[int,int]]) -> Optional[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key: return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system","content":"Compose a single clean gift search string."},
                {"role":"user","content":(
                    "Use ONLY these terms (reorder/trim ok). "
                    "Do NOT add age/gender/demographics.\n"
                    f"TERMS: {', '.join(allowed_terms)}\n"
                    f"Cohort: {cohort or ''}\n"
                    f"Budget: {'under '+str(budget[1])+' AUD' if budget else ''}\n"
                    "Output: one line, no lists."
                )}
            ],
            temperature=0
        )
        s = (resp.choices[0].message.content or "").strip().lower()
    except Exception:
        return None
    # Final sanitise
    for bad in FORBIDDEN:
        s = s.replace(bad, "")
    s = " ".join(s.split())
    return s or None

# ---------------------------------------------------------------------------
# Interpreter class
# ---------------------------------------------------------------------------

class QueryInterpreter:
    def __init__(self,
                 manifest_path: str = DEFAULT_MANIFEST_PATH,
                 metadata_path: str = DEFAULT_METADATA_PATH):
        self.manifest_path = Path(manifest_path)
        self.metadata_path = Path(metadata_path)
        self.manifest = _read_json(self.manifest_path) or {}
        # normalise tag_to_categories keys to lowercase
        t2c = self.manifest.get("tag_to_categories", {})
        self.tag_to_categories = { (k or "").lower(): v for k, v in t2c.items() }
        # build quick id->meta index
        meta = _read_json(self.metadata_path)
        self.meta_index: Dict[str, Dict[str, Any]] = {}
        if isinstance(meta, dict) and "photos" in meta:
            meta = meta["photos"]
        if isinstance(meta, list):
            for m in meta:
                if isinstance(m, dict) and "id" in m:
                    self.meta_index[str(m["id"])] = m

    # ---- inference from metadata -------------------------------------------

    def _infer_style_palette_cohort(self, photo_ids: List[str]) -> Tuple[List[str], List[str], Optional[str], Dict[str, Counter]]:
        style_ctr, palette_ctr, cohort_ctr = Counter(), Counter(), Counter()
        for pid in photo_ids or []:
            node = self.meta_index.get(str(pid)) or {}
            for s in node.get("style", []) or []:
                style_ctr[s.lower()] += 1
            for c in node.get("palette", []) or []:
                palette_ctr[c.lower()] += 1
            coh = node.get("cohort")
            if isinstance(coh, str):
                cohort_ctr[coh] += 1

        styles = [k for k, _ in style_ctr.most_common(3)]
        palettes = [k for k, _ in palette_ctr.most_common(3)]
        cohort = cohort_ctr.most_common(1)[0][0] if cohort_ctr else None
        return styles, palettes, cohort, {"style": style_ctr, "palette": palette_ctr, "cohort": cohort_ctr}

    # ---- category expansion -------------------------------------------------

    def _expand_categories(self, tokens: List[str], base_categories: List[str]) -> List[str]:
        cats = set(base_categories or [])
        for t in tokens:
            for c in self.tag_to_categories.get(t, []) or []:
                cats.add(c)
        return sorted(cats)

    # ---- product seed expansion --------------------------------------------

    def _product_seeds(self, tokens: List[str], categories: List[str], max_terms: int) -> List[str]:
        seeds: List[str] = []
        for t in tokens:
            seeds += TOKEN_TO_PRODUCT_TERMS.get(t, [])
        for c in categories:
            seeds += CATEGORY_TO_DEFAULT_TERMS.get(c, [])
        # normalise & dedupe
        seeds = _normalise(seeds)
        out: List[str] = []
        for s in seeds:
            if s not in out and len(out) < max_terms:
                out.append(s)
        return out

    # ---- confidence & probing ----------------------------------------------

    def _confidence(self, ctrs: Dict[str, Counter]) -> Dict[str, float]:
        """Lower entropy = higher confidence."""
        conf = {}
        for axis, c in ctrs.items():
            if not c:
                conf[axis] = 0.0
                continue
            ent = _entropy_from_counts(c)
            # normalise to [0..1] by dividing by log2(K) where K is number of bins
            k = max(1, len(c))
            max_ent = math.log2(k) if k > 1 else 1.0
            score = 1.0 - min(1.0, ent / max_ent)
            conf[axis] = round(score, 3)
        return conf

    def _probe_axes(self, conf: Dict[str, float], styles: List[str], palettes: List[str]) -> Tuple[List[str], List[str]]:
        """Suggest which axes to probe and the tags to look for in the next images."""
        probe_axes, probe_tags = [], []
        if conf.get("style", 0) < 0.55:
            probe_axes.append("style")
            # ask for contrasts
            probe_tags += ["minimalist","maximalist","retro","90s","premium","streetwear","outdoor"]
        if conf.get("palette", 0) < 0.55:
            probe_axes.append("palette")
            probe_tags += ["black","blue","neutral","earthy","pastel","neon"]
        if conf.get("cohort", 0) < 0.55:
            probe_axes.append("cohort")
            probe_tags += ["retro","90s","classic","tiktok","polaroid","vinyl"]
        # Remove things we already have plural votes for
        probe_tags = [t for t in probe_tags if t not in set(styles + palettes)]
        # Make unique, keep short
        seen, unique_tags = set(), []
        for t in probe_tags:
            if t not in seen:
                seen.add(t); unique_tags.append(t)
        return probe_axes, unique_tags[:8]

    # ---- multi-query composition -------------------------------------------

    def _compose_queries_multi(
        self,
        tokens: List[str],
        categories: List[str],
        recipient: str,
        styles: List[str],
        palettes: List[str],
        cohort: Optional[str],
        budget_aud: Optional[Tuple[int,int]],
    ) -> List[Tuple[Bucket, str]]:
        lo, hi = (budget_aud or (None, None))
        styles_phrase, style_practical = _styles_phrase(styles)
        palette_phrase = _palette_phrase(palettes)
        cohort_twist = COHORT_PHRASE.get(cohort or "", "").strip()
        themes = _themes_from_tokens(tokens)

        # choose buckets based on tokens/categories
        buckets: List[Bucket] = []
        if (
            "Fashion" in categories
            or any(t in tokens for t in ("casual", "retro", "90s", "minimalist"))
        ):
            buckets.append("Fashion")
        if (
            "Books" in categories
            or any(t in tokens for t in ("book", "books", "philosophy", "art", "tech", "design"))
        ):
            buckets.append("Books")
        if "Tech" in categories or "tech" in tokens:
            buckets.append("Tech")
        if (
            "Outdoors" in categories
            or any(t in tokens for t in ("outdoor", "nature", "hiking", "camping", "summer", "sun", "beach"))
        ):
            buckets.append("Outdoors")
        if "Home" in categories or "window" in tokens:
            buckets.append("Home")
        if (
            "Entertainment" in categories
            or any(t in tokens for t in ("gaming", "records", "music", "entertainment"))
        ):
            buckets.append("Entertainment")

        if not buckets:
            buckets = ["Tech", "Books"]

        seen: set[Bucket] = set()
        deduped: List[Bucket] = []
        for b in buckets:
            if b in seen:
                continue
            seen.add(b)
            deduped.append(b)

        if recipient == "couple":
            for candidate in ["Home", "Fashion", "Entertainment"]:
                if candidate not in seen:
                    deduped.append(candidate)
                    seen.add(candidate)
            priority = ["Home", "Fashion", "Entertainment", "Tech", "Books", "Outdoors"]
            ordered: List[Bucket] = [b for b in priority if b in seen]
            for b in deduped:
                if b not in ordered:
                    ordered.append(b)
            deduped = ordered

        buckets = deduped[:5] or ["Tech", "Books"]

        out: List[Tuple[Bucket, str]] = []
        for b in buckets:
            tpl = BUCKET_TEMPLATES[b]
            q = tpl.format(
                styles=styles_phrase or "casual",
                palette=palette_phrase,
                recipient_phrase=_recipient_phrase(recipient),
                cohort_twist=(" " + cohort_twist) if cohort_twist else "",
                style_practical=style_practical or "that are plain and practical",
                themes=themes,
                hi=f"${hi}" if hi else "$100",
            )
            q = " ".join(q.split())
            out.append((b, q))
        return out

    # ---- public entry -------------------------------------------------------

    def interpret(
        self,
        tokens: List[str],
        categories: List[str] | None,
        photo_ids: List[str] | None,
        budget_aud: Tuple[int,int] | None = None,
        use_llm: bool = True,
        recipient_hint: Optional[str] = None,   # "me","man","woman","family","couple","teen","kid"
    ) -> Dict[str, Any]:

        toks = _normalise(tokens)
        cats = self._expand_categories(toks, categories or [])

        demographics = infer_demographics_from_photos(photo_ids or [], self.meta_index)
        demo_filters: Dict[str, Any] = demographics.get("filters", {}) or {}
        demo_recipient = demographics.get("recipient")
        demo_categories = demographics.get("categories") or []
        if demo_categories:
            cats = sorted({*cats, *(c for c in demo_categories if c)})

        recipient = recipient_hint or demo_recipient or "me"
        if recipient == "me" and any(t in SAFE_RECIPIENT_TOKENS for t in toks):
            recipient = "couple"
        if recipient == "couple":
            cats = sorted(set(cats + ["Occasion", "Jewellery", "Home"]))
        if demographics.get("occasion") and "Occasion" not in cats:
            cats = sorted(set(cats + ["Occasion"]))

        # infer from selected photos
        styles, palettes, cohort_meta, ctrs = self._infer_style_palette_cohort(photo_ids or [])
        conf = self._confidence(ctrs)

        # fallback cohort using tokens if metadata missing
        cohort = cohort_meta
        if not cohort:
            for t in toks:
                if t in TOKEN_TO_COHORT:
                    cohort = TOKEN_TO_COHORT[t]; break

        # deterministic product seeds (useful for debugging/rerank)
        product_terms = self._product_seeds(toks, cats, max_terms=12)

        # build allowed term list for optional LLM rewrite
        demo_terms = []
        if demographics.get("occasion"):
            demo_terms.append(str(demographics["occasion"]).lower())
        demo_terms.extend(str(cat).lower() for cat in demo_categories if cat)
        allowed_terms = list(dict.fromkeys(toks + cats + styles + palettes + product_terms + demo_terms))
        if cohort: allowed_terms.append(cohort)
        llm_phrase = _llm_rewrite(allowed_terms, cohort, budget_aud) if use_llm else None

        # compose several bucketed queries (deterministic)
        queries_multi = self._compose_queries_multi(
            tokens=toks, categories=cats, recipient=recipient,
            styles=styles, palettes=palettes, cohort=cohort, budget_aud=budget_aud
        )

        # If LLM produced a neat string, you can optionally replace each query,
        # but keep it deterministic for now; the LLM is already used for rerank later.

        # decide if we need more images (low confidence on key axes)
        probe_axes, probe_tags = self._probe_axes(conf, styles, palettes)
        need_more_images = bool(probe_axes)

        return {
            "tokens": toks,
            "categories": cats,
            "styles": styles,
            "palettes": palettes,
            "cohort": cohort,
            "confidence": conf,               # e.g., {"style":0.61,"palette":0.48,"cohort":0.35}
            "product_terms": product_terms,
            "llm_phrase_preview": llm_phrase, # optional; not used if you prefer deterministic
            "queries_multi": queries_multi,   # [(bucket, query), ...]
            "recipient": recipient,
            "demographics": demographics,
            "filters": demo_filters,
            "need_more_images": need_more_images,
            "probe_axes": probe_axes,         # e.g., ["palette","cohort"]
            "probe_tags": probe_tags,         # e.g., ["black","blue","neutral","retro","90s","classic"]
        }
