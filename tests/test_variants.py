import numpy as np

from src.variants import Photo, find_variants, jaccard_overlap


def test_jaccard_overlap_handles_empty_sets():
    assert jaccard_overlap([], []) == 1.0
    assert jaccard_overlap(["a"], []) == 0.0


def test_find_variants_filters_by_overlap_and_cosine():
    base = Photo("base", np.array([1.0, 0.0, 0.0]), ["retro", "warm", "handcrafted", "calm", "earthy"])
    candidate_good = Photo(
        "c1",
        np.array([0.8, 0.5, 0.0]),
        ["retro", "warm", "handcrafted", "calm"],
    )
    candidate_low_overlap = Photo(
        "c2",
        np.array([0.1, 0.9, 0.0]),
        ["urban", "modern", "cool", "sleek", "tech"],
    )
    candidate_too_similar = Photo(
        "c3",
        np.array([0.99, 0.05, 0.0]),
        ["retro", "warm", "handcrafted", "calm", "earthy"],
    )

    pool = [candidate_good, candidate_low_overlap, candidate_too_similar]
    variants = find_variants(base, pool, min_tag_overlap=0.8, max_cosine=0.95, max_variants=3)
    assert [(vid) for vid, _, _ in variants] == ["c1"]
    assert variants[0][1] >= 0.8
    assert variants[0][2] <= 0.95
