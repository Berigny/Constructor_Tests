from typing import Sequence

import numpy as np

from src.taste import (
    ChoiceEvent,
    Photo,
    build_taste_vector,
    select_next_photo_greedy_mmr,
    top_tags_from_events,
)


def _photo(pid: str, vec: Sequence[float], tags):
    return Photo(id=pid, vector=np.array(vec, dtype=np.float32), tags=tuple(tags))


def test_taste_vector_weights_and_signals():
    photos = {
        "p1": _photo("p1", [1.0, 0.0, 0.0], ["retro", "warm"]),
        "p2": _photo("p2", [0.0, 1.0, 0.0], ["modern"]),
        "p3": _photo("p3", [0.0, 0.0, 1.0], ["bold"]),
    }
    events = [
        ChoiceEvent("p1", "super_like", 0),
        ChoiceEvent("p2", "like", 1),
        ChoiceEvent("p3", "dislike", 2),
    ]
    taste = build_taste_vector(photos, events, recency_tau=100.0)

    assert np.dot(taste, photos["p1"].vector) > np.dot(taste, photos["p2"].vector)
    assert np.dot(taste, photos["p3"].vector) < 0


def test_recency_decay_prioritises_recent_choices():
    photos = {
        "p1": _photo("p1", [1.0, 0.0], ["warm"]),
        "p2": _photo("p2", [0.0, 1.0], ["cool"]),
    }
    events = [
        ChoiceEvent("p1", "like", 0),
        ChoiceEvent("p2", "like", 5),
    ]
    taste = build_taste_vector(photos, events, recency_tau=1.0)
    assert np.dot(taste, photos["p2"].vector) > np.dot(taste, photos["p1"].vector)


def test_top_tags_from_events_respects_weights():
    photos = {
        "p1": _photo("p1", [1.0, 0.0], ["retro", "warm"]),
        "p2": _photo("p2", [0.0, 1.0], ["modern", "cool"]),
    }
    events = [
        ChoiceEvent("p1", "super_like", 0),
        ChoiceEvent("p2", "dislike", 1),
    ]
    tags = top_tags_from_events(photos, events, top_k=2, recency_tau=10.0)
    assert tags[0] in {"retro", "warm"}
    assert "modern" not in tags


def test_mmr_selector_prefers_diverse_candidate():
    photos = {
        "a": _photo("a", [1.0, 0.0], []),
        "b": _photo("b", [0.95, 0.05], []),
        "c": _photo("c", [0.0, 1.0], []),
        "d": _photo("d", [-1.0, 0.0], []),
    }
    taste = np.array([1.0, 0.0], dtype=np.float32)
    next_id = select_next_photo_greedy_mmr(
        candidate_ids=["b", "c", "d"],
        photos_by_id=photos,
        taste_vec=taste,
        shown_ids=["a"],
        lambda_diversity=0.3,
    )
    assert next_id == "c"
