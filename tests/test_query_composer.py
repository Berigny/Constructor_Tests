from src.query_composer import (
    FORBIDDEN_TERMS,
    compose_query_from_tags,
    sanitize_query,
    select_allowed_terms,
    top_tags_from_rows,
)


def test_compose_query_from_tags_uses_whitelist_and_tokens():
    tags = ["nature", "calm", "earthy", "handcrafted", "retro"]
    plan = compose_query_from_tags(tags)

    assert plan.query.endswith("gift ideas")
    assert len(plan.tokens) >= 2
    assert all(token in plan.query for token in plan.tokens)
    for bad in FORBIDDEN_TERMS:
        assert bad not in plan.query

    # Ensure categories only come from the deterministic map
    assert "Outdoors" in plan.categories
    assert "Home" in plan.categories


def test_sanitize_query_strips_forbidden_terms_and_giftcards():
    dirty = "Cozy gift ideas for her and boys giftcards"
    cleaned = sanitize_query(dirty)
    assert "for her" not in cleaned.lower()
    assert "boys" not in cleaned.lower()
    assert "giftcards" not in cleaned.lower()
    assert cleaned.lower().startswith("cozy gift ideas")


def test_select_allowed_terms_minimum_coverage():
    tags = ["nature", "handcrafted"]
    tokens = select_allowed_terms(tags, max_terms=4, min_terms=2)
    assert len(tokens) >= 2


def test_top_tags_from_rows_preserves_order_by_weight():
    rows = [
        {"tags": ["Nature", "Calm", "Nature"]},
        {"tags": ["Earthy", "Calm"]},
        {"tags": ["Handcrafted"]},
    ]
    top = top_tags_from_rows(rows, top_k=4)
    assert top[:2] == ["Nature", "Calm"]
    assert "Earthy" in top
