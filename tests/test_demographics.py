from __future__ import annotations

from src.demographics import infer_demographics_from_photos


def test_infer_demographics_single_photo() -> None:
    meta_index = {
        "photo-1": {
            "demographics": {
                "gender": ["male"],
                "age_group": ["35-44"],
                "recipient": ["man"],
                "occasion": ["birthday"],
                "categories": ["Outdoors"],
            }
        }
    }

    result = infer_demographics_from_photos(["photo-1"], meta_index)

    assert result["gender"] == "Men"
    assert result["age"] == "35-44"
    assert result["recipient"] == "man"
    assert result["occasion"] == "Birthday"
    assert result["categories"] == ["Outdoors"]
    assert result["filters"]["Gender"] == "Men"
    assert result["filters"]["Suitable for ages"] == "35-44 Years"
    assert result["filters"]["Occasion"] == "Birthday"


def test_infer_demographics_falls_back_to_gender() -> None:
    meta_index = {
        "img-5": {
            "demographics": {
                "gender": "female",
            }
        }
    }

    result = infer_demographics_from_photos(["img-5"], meta_index)

    assert result["gender"] == "Women"
    assert result["recipient"] == "woman"
    assert result["filters"]["Gender"] == "Women"
