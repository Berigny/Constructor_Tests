import numpy as np

from src.rank_embed import Gift, filter_budget_and_age, rank_gifts_by_taste


def test_rank_gifts_prefers_high_cosine():
    gifts = [
        Gift("a", "Warm Mug", 20.0, ("warm",), vector=np.array([1.0, 0.0], dtype=np.float32)),
        Gift("b", "Cool Lamp", 20.0, ("cool",), vector=np.array([0.0, 1.0], dtype=np.float32)),
    ]
    taste = np.array([1.0, 0.0], dtype=np.float32)
    ranked = rank_gifts_by_taste(gifts, taste, top_k=2)
    assert ranked[0][0].sku == "a"
    assert ranked[0][1] > ranked[1][1]


def test_rank_gifts_tfidf_fallback_uses_tags():
    gifts = [
        Gift("a", "Retro Mug", 30.0, ("retro", "warm")),
        Gift("b", "Neon Sign", 30.0, ("neon", "tech")),
    ]
    ranked = rank_gifts_by_taste(gifts, taste_vec=None, taste_top_tags=["retro", "warm"], top_k=2)
    assert ranked[0][0].sku == "a"
    assert ranked[0][1] > ranked[1][1]


def test_filter_budget_and_age_applies_guards():
    gifts = [
        (Gift("a", "Budget", 20.0, ("warm",), meta={"age_fit": ["adult"]}), 0.8),
        (Gift("b", "Spend", 200.0, ("warm",), meta={"age_fit": ["teen"]}), 0.9),
    ]
    filtered = filter_budget_and_age(gifts, budget=(30.0, 150.0), age_prior=["adult"])
    assert len(filtered) == 0
