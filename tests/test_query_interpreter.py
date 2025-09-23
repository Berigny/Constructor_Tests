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
    )

    assert result["tokens"] == ["summer", "sun", "window"]
    assert set(result["categories"]) >= {"Fashion", "Home", "Outdoors"}
    assert "sunglasses" in result["product_terms"]
    assert "ceramic vase" in result["product_terms"]
    assert result["llm_phrase_preview"] is None
    queries_multi = dict(result["queries_multi"])
    assert "Fashion" in queries_multi
    assert queries_multi["Fashion"].endswith("under $60")
    assert any(bucket == "Outdoors" for bucket, _ in result["queries_multi"])
    assert result["need_more_images"] is True
    assert "style" in result["probe_axes"]


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
    assert all("girl" not in term for term in result["product_terms"])
    assert all("girl" not in q for _, q in result["queries_multi"])
    assert result["cohort"] == "Millennial nostalgia"


def test_interpreter_reads_cohort_from_metadata(tmp_path) -> None:
    metadata = [
        {
            "id": "photo-1",
            "style": ["minimalist"],
            "palette": ["black"],
            "cohort": "Gen Z",
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
        tokens=["retro"],
        categories=[],
        photo_ids=["photo-1"],
        use_llm=False,
    )

    assert result["cohort"] == "Gen Z"
    assert result["styles"] == ["minimalist"]
    assert result["palettes"] == ["black"]
    assert result["need_more_images"] is False
    queries_multi = dict(result["queries_multi"])
    assert queries_multi["Fashion"].startswith("plain in black")


def test_interpreter_uses_metadata_signals_in_queries(tmp_path) -> None:
    metadata = [
        {
            "id": "photo-9",
            "style": ["minimalist", "90s"],
            "palette": ["black", "blue"],
            "cohort": "Gen X",
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
        tokens=["tech", "art", "philosophy"],
        categories=["Tech"],
        photo_ids=["photo-9"],
        budget_aud=(20, 100),
        use_llm=False,
    )

    assert result["styles"] == ["minimalist", "90s"]
    assert result["palettes"] == ["black", "blue"]
    queries_multi = dict(result["queries_multi"])
    assert "Tech" in queries_multi and "Books" in queries_multi
    assert "Gen X sensibility" in queries_multi["Tech"]
    assert queries_multi["Tech"].endswith("under $100")
    assert "art and philosophy and tech" in queries_multi["Books"]
    assert "style" in result["probe_axes"]


def test_interpreter_infers_demographic_filters(tmp_path) -> None:
    metadata = [
        {
            "id": "photo-42",
            "demographics": {
                "gender": ["male"],
                "age_group": ["35-44"],
                "recipient": ["man"],
                "occasion": ["anniversary"],
                "categories": ["Outdoors"],
            },
            "style": ["minimalist"],
            "palette": ["blue"],
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
        tokens=["hiking"],
        categories=[],
        photo_ids=["photo-42"],
        use_llm=False,
    )

    assert result["recipient"] == "man"
    assert "Outdoors" in result["categories"]
    assert "Occasion" in result["categories"]
    assert result["filters"]["Gender"] == "Men"
    assert result["filters"]["Suitable for ages"] == "35-44 Years"
    assert result["filters"]["Occasion"] == "Anniversary"
