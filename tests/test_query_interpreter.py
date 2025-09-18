from __future__ import annotations

import json
from pathlib import Path

from src.query_interpreter import QueryInterpreter


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_interpreter_expands_tokens_and_categories() -> None:
    root = _project_root()
    interpreter = QueryInterpreter(
        manifest_path=str(root / "queries_manifest.json"),
        metadata_path=str(root / "unsplash_images" / "metadata.json"),
    )

    result = interpreter.interpret(
        tokens=["summer", "sun", "window"],
        categories=[],
        photo_ids=[],
        budget_aud=(25, 60),
        use_llm=False,
        max_terms=10,
    )

    assert result["tokens"] == ["summer", "sun", "window"]
    assert result["categories"] == ["Fashion", "Home", "Outdoors", "Travel"]
    assert "sunglasses" in result["product_terms"]
    assert "ceramic vase" in result["product_terms"]
    assert result["query_llm"] is None
    assert result["query_no_llm"].endswith("under 60 aud")
    queries_multi = result["queries_multi"]
    assert queries_multi[0] == ("Fashion", "casual clothes for me under $60")
    assert result["final_query"] == "casual clothes for me under $60"
    assert any(bucket == "Outdoors" for bucket, _ in queries_multi)
    assert all(query.endswith("under $60") for _, query in queries_multi)


def test_interpreter_filters_forbidden_tokens() -> None:
    root = _project_root()
    interpreter = QueryInterpreter(
        manifest_path=str(root / "queries_manifest.json"),
        metadata_path=str(root / "unsplash_images" / "metadata.json"),
    )

    result = interpreter.interpret(
        tokens=["girl", "retro", "vintage"],
        categories=[],
        photo_ids=[],
        use_llm=False,
    )

    assert result["tokens"] == ["retro", "vintage"]
    assert "girl" not in result["tokens"]
    assert all("girl" not in term for term in result["product_terms"])
    assert "girl" not in result["query_no_llm"]
    assert all("girl" not in q for _, q in result["queries_multi"])


def test_interpreter_reads_cohort_from_metadata(tmp_path) -> None:
    metadata = [
        {
            "id": "photo-1",
            "gen_marker": ["genz-coded"],
        }
    ]
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps(metadata))

    root = _project_root()
    interpreter = QueryInterpreter(
        manifest_path=str(root / "queries_manifest.json"),
        metadata_path=str(metadata_path),
    )

    result = interpreter.interpret(
        tokens=["vintage"],
        categories=[],
        photo_ids=["photo-1"],
        use_llm=False,
    )

    assert result["cohort"] == "Gen Z"
    assert "vinyl record" in result["product_terms"]
    assert result["queries_multi"]


def test_interpreter_uses_user_hints() -> None:
    root = _project_root()
    interpreter = QueryInterpreter(
        manifest_path=str(root / "queries_manifest.json"),
        metadata_path=str(root / "unsplash_images" / "metadata.json"),
    )

    result = interpreter.interpret(
        tokens=["tech", "art", "philosophy", "90s"],
        categories=["Tech"],
        photo_ids=[],
        budget_aud=(20, 100),
        use_llm=False,
        ui_recipient="man",
        ui_colours=["black", "blue"],
        ui_styles=["casual", "90s"],
        ui_cohort="Gen X",
    )

    queries_multi = dict(result["queries_multi"])
    fashion_query = queries_multi["Fashion"]
    assert "for men" in fashion_query
    assert "black and blue" in fashion_query
    assert fashion_query.endswith("under $100")
    books_query = queries_multi.get("Books")
    if books_query:
        assert "philosophy" in books_query
    tech_query = queries_multi["Tech"]
    assert "gadgets" in tech_query and "for men" in tech_query
