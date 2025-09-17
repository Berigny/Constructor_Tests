import json

import pytest

from src.query_builder import QueryBuilder


def write_manifest(tmp_path, manifest):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return path


def test_basic_compose(tmp_path):
    manifest = {
        "allowed_tokens": ["outdoor", "retro", "cozy"],
        "forbidden_tokens": ["girl", "boy", "adult"],
        "synonyms": {"cozy": ["cosy", "snug"]},
        "tag_to_categories": {"outdoor": ["Outdoors"], "retro": ["Entertainment"]},
        "query_rules": {"min_tokens": 2, "max_tokens": 6},
    }
    manifest_path = write_manifest(tmp_path, manifest)

    qb = QueryBuilder(str(manifest_path))
    query, categories = qb.compose(["outdoor", "retro", "girl", "adult"])

    assert query == "outdoor retro"
    assert categories == ["Entertainment", "Outdoors"]


def test_fallback_if_too_few_tokens(tmp_path):
    manifest = {
        "allowed_tokens": ["outdoor"],
        "forbidden_tokens": [],
        "synonyms": {},
        "tag_to_categories": {},
        "query_rules": {"min_tokens": 2, "max_tokens": 6},
    }
    manifest_path = write_manifest(tmp_path, manifest)

    qb = QueryBuilder(str(manifest_path))
    query, categories = qb.compose(["outdoor"])

    assert query is None
    assert categories == []


def test_no_demographics_in_query(tmp_path):
    manifest = {
        "allowed_tokens": ["outdoor", "retro"],
        "forbidden_tokens": ["men", "women", "kids"],
        "synonyms": {},
        "tag_to_categories": {},
        "query_rules": {"min_tokens": 2, "max_tokens": 6},
    }
    manifest_path = write_manifest(tmp_path, manifest)

    qb = QueryBuilder(str(manifest_path))
    query, _ = qb.compose(["outdoor", "kids", "retro", "women"])

    assert query == "outdoor retro"


def test_category_fallback_when_tokens_sparse(tmp_path):
    manifest = {
        "allowed_tokens": ["outdoor"],
        "forbidden_tokens": [],
        "synonyms": {},
        "tag_to_categories": {"outdoor": ["Travel", "Outdoors"]},
        "query_rules": {"min_tokens": 2, "max_tokens": 6},
    }
    manifest_path = write_manifest(tmp_path, manifest)

    qb = QueryBuilder(str(manifest_path))
    query, categories = qb.compose(["outdoor"])

    assert query == "Outdoors Travel"
    assert categories == ["Outdoors", "Travel"]


def test_compose_with_debug_reports_dropped(tmp_path):
    manifest = {
        "allowed_tokens": ["outdoor", "retro"],
        "forbidden_tokens": ["woman"],
        "synonyms": {"retro": ["vintage"]},
        "tag_to_categories": {},
        "query_rules": {"min_tokens": 1, "max_tokens": 4},
    }
    manifest_path = write_manifest(tmp_path, manifest)

    qb = QueryBuilder(str(manifest_path))
    query, categories, debug = qb.compose_with_debug(
        ["Outdoor", "Vintage", "Woman", "Unknown"],
    )

    assert query == "outdoor retro"
    assert categories == []
    assert debug["raw_tags"] == ["Outdoor", "Vintage", "Woman", "Unknown"]
    assert debug["filtered_tokens"] == ["outdoor", "retro"]
    assert debug["dropped_forbidden"] == ["woman"]
    assert debug["dropped_not_allowed"] == ["unknown"]


def test_non_string_tags_are_cast(tmp_path):
    class Wrapper:
        def __init__(self, value: str) -> None:
            self.value = value

        def __str__(self) -> str:  # pragma: no cover - trivial
            return self.value

    manifest = {
        "allowed_tokens": ["outdoor"],
        "forbidden_tokens": ["woman"],
        "synonyms": {},
        "tag_to_categories": {},
        "query_rules": {"min_tokens": 1, "max_tokens": 4},
    }
    manifest_path = write_manifest(tmp_path, manifest)

    qb = QueryBuilder(str(manifest_path))
    wrapped = [Wrapper("Outdoor"), Wrapper("Woman")]
    query, categories, debug = qb.compose_with_debug(wrapped)

    assert query == "outdoor"
    assert categories == []
    assert debug["raw_tags"] == ["Outdoor", "Woman"]
    assert debug["dropped_forbidden"] == ["woman"]
