"""Helpers for inferring recipient demographics from selected images."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_GENDER_MAP: Dict[str, str] = {
    "man": "Men",
    "men": "Men",
    "male": "Men",
    "masculine": "Men",
    "woman": "Women",
    "women": "Women",
    "female": "Women",
    "feminine": "Women",
    "mum": "Women",
    "mom": "Women",
    "mother": "Women",
    "dad": "Men",
    "father": "Men",
}

_RECIPIENT_MAP: Dict[str, str] = {
    "man": "man",
    "men": "man",
    "male": "man",
    "husband": "man",
    "woman": "woman",
    "women": "woman",
    "female": "woman",
    "wife": "woman",
    "mum": "woman",
    "mom": "woman",
    "dad": "man",
    "father": "man",
    "boy": "kid",
    "boys": "kid",
    "girl": "kid",
    "girls": "kid",
    "kid": "kid",
    "child": "kid",
    "children": "family",
    "family": "family",
    "families": "family",
    "couple": "couple",
    "couples": "couple",
    "partner": "couple",
    "partners": "couple",
    "parents": "couple",
    "friends": "friends",
    "friend": "friends",
}

_AGE_RANGE_MAP: Dict[str, str] = {
    "toddler": "0-4",
    "toddlers": "0-4",
    "kid": "5-12",
    "kids": "5-12",
    "child": "5-12",
    "children": "5-12",
    "preteen": "10-12",
    "teen": "13-18",
    "teens": "13-18",
    "teenager": "13-18",
    "youth": "13-18",
    "young adult": "18-24",
    "young adults": "18-24",
    "20s": "25-34",
    "twenties": "25-34",
    "30s": "35-44",
    "thirties": "35-44",
    "40s": "45-54",
    "forties": "45-54",
    "50s": "55-64",
    "fifties": "55-64",
    "60s": "65+",
    "sixties": "65+",
    "70s": "65+",
    "seventies": "65+",
    "80s": "65+",
    "eighties": "65+",
    "adult": "25-44",
    "adults": "25-44",
    "middle aged": "45-54",
    "middle-aged": "45-54",
    "older": "55+",
    "elderly": "65+",
    "senior": "65+",
    "seniors": "65+",
}

_OCCASION_MAP: Dict[str, str] = {
    "birthday": "Birthday",
    "anniversary": "Anniversary",
    "wedding": "Wedding",
    "christmas": "Christmas",
    "holiday": "Christmas",
    "holidays": "Christmas",
    "xmas": "Christmas",
    "graduation": "Graduation",
    "baby shower": "New Baby",
    "new baby": "New Baby",
    "newborn": "New Baby",
    "valentine": "Valentine's Day",
    "valentines": "Valentine's Day",
    "mother's day": "Mother's Day",
    "mothers day": "Mother's Day",
    "father's day": "Father's Day",
    "fathers day": "Father's Day",
}

_CATEGORY_MAP: Dict[str, str] = {
    "outdoor": "Outdoors",
    "outdoors": "Outdoors",
    "outdoorsy": "Outdoors",
    "hiking": "Outdoors",
    "camping": "Outdoors",
    "tech": "Tech",
    "technology": "Tech",
    "gadget": "Tech",
    "gadgets": "Tech",
    "book": "Books",
    "books": "Books",
    "reading": "Books",
    "home": "Home",
    "decor": "Home",
    "fashion": "Fashion",
    "style": "Fashion",
    "music": "Entertainment",
    "gaming": "Entertainment",
    "game": "Entertainment",
    "food": "Food",
    "drink": "Food",
    "drinks": "Food",
    "art": "Entertainment",
}

_AXIS_KEYS: Dict[str, Sequence[str]] = {
    "gender": ("gender", "genders"),
    "age": ("age", "ages", "age_group", "age_groups"),
    "recipient": ("recipient", "recipients", "audience"),
    "occasion": ("occasion", "occasions"),
    "category": ("categories", "category", "themes"),
}


def _ensure_list(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return list(value.values())
    try:
        return [str(v) for v in value if str(v).strip()]
    except TypeError:
        return [str(value)]


def _normalise_gender(value: str) -> Optional[str]:
    key = value.strip().lower()
    if not key:
        return None
    if key in _GENDER_MAP:
        return _GENDER_MAP[key]
    if key in {"men", "women"}:
        return key.title()
    if key in {"unisex", "neutral", "gender neutral", "gender-neutral"}:
        return "Unisex"
    return None


def _normalise_recipient(value: str) -> Optional[str]:
    key = value.strip().lower()
    if not key:
        return None
    if key in _RECIPIENT_MAP:
        return _RECIPIENT_MAP[key]
    if key in {"couple", "couples"}:
        return "couple"
    if key in {"family", "families"}:
        return "family"
    if key in {"friends", "friend", "buddies"}:
        return "friends"
    return None


_AGE_RANGE_RE = re.compile(r"(\d+)(?:\s*[-–]\s*(\d+))?\s*\+?")


def _normalise_age(value: str) -> Optional[str]:
    key = value.strip().lower()
    if not key:
        return None
    if key in _AGE_RANGE_MAP:
        return _AGE_RANGE_MAP[key]
    match = _AGE_RANGE_RE.search(key)
    if match:
        start = match.group(1)
        end = match.group(2)
        if end:
            return f"{int(start)}-{int(end)}"
        if key.endswith("+") or "+" in key:
            return f"{int(start)}+"
        return start
    return None


def _age_filter_label(age_value: str) -> Optional[str]:
    if not age_value:
        return None
    if age_value.endswith("+"):
        return f"{age_value} Years"
    if "-" in age_value:
        return f"{age_value} Years"
    if age_value.isdigit():
        return f"{age_value}+ Years"
    return None


def _normalise_occasion(value: str) -> Optional[str]:
    key = value.strip().lower()
    if not key:
        return None
    if key in _OCCASION_MAP:
        return _OCCASION_MAP[key]
    return value.strip().title()


def _normalise_category(value: str) -> Optional[str]:
    key = value.strip().lower()
    if not key:
        return None
    if key in _CATEGORY_MAP:
        return _CATEGORY_MAP[key]
    return value.strip().title()


_AXIS_NORMALISERS = {
    "gender": _normalise_gender,
    "age": _normalise_age,
    "recipient": _normalise_recipient,
    "occasion": _normalise_occasion,
    "category": _normalise_category,
}


def _collect_axis_values(node: Mapping[str, Any], axis: str) -> Iterable[str]:
    values = []
    demographics = node.get("demographics")
    if isinstance(demographics, Mapping):
        for key in _AXIS_KEYS.get(axis, ()):  # type: ignore[arg-type]
            if key in demographics:
                values.extend(_ensure_list(demographics[key]))
    for key in _AXIS_KEYS.get(axis, ()):  # type: ignore[arg-type]
        if key in node:
            values.extend(_ensure_list(node[key]))
    if axis == "category":
        values.extend(_ensure_list(node.get("category")))
    if axis in {"recipient", "gender", "age", "occasion"}:
        values.extend(_ensure_list(node.get(f"{axis}_tags")))
    return values


def _dominant(counter: Counter[str]) -> Optional[str]:
    if not counter:
        return None
    total = sum(counter.values())
    value, count = counter.most_common(1)[0]
    if total <= 1 or len(counter) == 1:
        return value
    if count / total >= 0.6:
        return value
    return None


def infer_demographics_from_photos(
    photo_ids: Sequence[str],
    meta_index: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Infer demographic filters from the selected photo metadata."""

    counters: Dict[str, Counter[str]] = {
        "gender": Counter(),
        "age": Counter(),
        "recipient": Counter(),
        "occasion": Counter(),
        "category": Counter(),
    }

    for pid in photo_ids:
        node = meta_index.get(str(pid))
        if not isinstance(node, Mapping):
            continue
        for axis, counter in counters.items():
            normaliser = _AXIS_NORMALISERS[axis]
            for raw_val in _collect_axis_values(node, axis):
                norm = normaliser(str(raw_val)) if raw_val is not None else None
                if not norm:
                    continue
                counter[str(norm)] += 1

    result: Dict[str, Any] = {}
    filters: Dict[str, Any] = {}

    gender = _dominant(counters["gender"])
    if gender:
        result["gender"] = gender
        if gender in {"Men", "Women"}:
            filters["Gender"] = gender

    age = _dominant(counters["age"])
    if age:
        result["age"] = age
        age_filter = _age_filter_label(age)
        if age_filter:
            filters["Suitable for ages"] = age_filter

    recipient = _dominant(counters["recipient"])
    if not recipient and gender in {"Men", "Women"}:
        recipient = "man" if gender == "Men" else "woman"
    if recipient:
        result["recipient"] = recipient

    occasion = _dominant(counters["occasion"])
    if occasion:
        result["occasion"] = occasion
        filters["Occasion"] = occasion

    categories = [name for name, _ in counters["category"].most_common(3)]
    if categories:
        result["categories"] = categories

    result["votes"] = {axis: dict(counter) for axis, counter in counters.items() if counter}
    result["filters"] = filters

    return result


__all__ = ["infer_demographics_from_photos"]

