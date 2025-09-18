from __future__ import annotations
from typing import Iterable, Mapping, Sequence
from urllib.parse import quote, urlencode
import json

BASE = "https://ac.cnstrc.com/v1/search/natural_language/"

DEFAULT_PREFILTER_NOT: list[tuple[str, str]] = [
    ("Audience", "Kids"),
    ("Suitable for ages", "0-24 Months"),
    ("Suitable for ages", "2-4 Years"),
    ("Suitable for ages", "3+ Years"),
    ("Suitable for ages", "5+ Years"),
    ("Suitable for ages", "6+ Years"),
    ("Suitable for ages", "8+ Years"),
    ("Suitable for ages", "10+ Years"),
    ("Suitable for ages", "12-15 Years"),
    ("Suitable for ages", "14+ Years"),
    ("Shop By Pet", "Dog"),
    ("Shop By Pet", "Cat"),
    ("Shop By Pet", "Fish"),
]


def _normalise_filters(filters: Mapping[str, str | Sequence[str]] | None) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if not filters:
        return pairs
    for field, value in filters.items():
        key = f"filters[{field}]"
        if isinstance(value, (list, tuple, set)):
            for v in value:
                pairs.append((key, str(v)))
        else:
            pairs.append((key, str(value)))
    return pairs


def _iter_extra(extra: Iterable[tuple[str, str]] | Mapping[str, str] | None) -> list[tuple[str, str]]:
    if extra is None:
        return []
    if isinstance(extra, Mapping):
        return [(str(k), str(v)) for k, v in extra.items()]
    return [(str(k), str(v)) for k, v in extra]


def build_constructor_url(
    *,
    nl_query: str,
    api_key: str,
    base_url: str | None = None,
    page: int = 1,
    per_page: int = 50,
    sort_by: str = "relevance",
    sort_order: str = "descending",
    filters: Mapping[str, str | Sequence[str]] | None = None,
    prefilter_not: Sequence[tuple[str, str]] | None = None,
    client: str = "ciojs-client-2.66.2",
    session: int | str = 1,
    extra_params: Iterable[tuple[str, str]] | Mapping[str, str] | None = None,
) -> str:
    """Build a Constructor NL search URL with filters and optional pre-filter."""

    prefix = (base_url or BASE).rstrip("/")
    path = f"{prefix}/{quote(nl_query)}"

    params: list[tuple[str, str]] = [
        ("key", api_key),
        ("s", str(session)),
        ("page", str(page)),
        ("num_results_per_page", str(per_page)),
        ("sort_by", sort_by),
        ("sort_order", sort_order),
        ("c", client),
    ]

    params.extend(_normalise_filters(filters))

    if prefilter_not:
        expr = {
            "not": {
                "or": [
                    {"name": name, "value": value}
                    for name, value in prefilter_not
                ]
            }
        }
        params.append(("pre_filter_expression", json.dumps(expr)))

    params.extend(_iter_extra(extra_params))

    query_string = urlencode(params, doseq=True, quote_via=quote)
    return f"{path}?{query_string}"


__all__ = [
    "build_constructor_url",
    "DEFAULT_PREFILTER_NOT",
]
