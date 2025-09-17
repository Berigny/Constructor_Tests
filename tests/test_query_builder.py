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

    assert query.startswith("outdoor retro")
    assert "gift ideas" in query
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

    assert query == "gift ideas"
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

    assert "kids" not in query
    assert "women" not in query
    assert query.startswith("outdoor retro")
