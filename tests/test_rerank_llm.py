from src.rank_embed import Gift
from src.rerank_llm import RerankResult, choose_final_best, heuristic_rerank


def test_heuristic_rerank_prioritises_tag_overlap_and_budget():
    gifts = [
        Gift("sku1", "Retro Mug", 40.0, ("retro", "warm", "handcrafted"), meta={"age_fit": ["adult"]}),
        Gift("sku2", "Neon Sign", 140.0, ("neon", "tech"), meta={"age_fit": ["teen"]}),
        Gift("sku3", "Vintage Camera", 95.0, ("retro", "nostalgic"), meta={"age_fit": ["adult"]}),
    ]
    results = heuristic_rerank(
        gifts,
        taste_top_tags=["retro", "warm", "handcrafted"],
        budget=(30.0, 120.0),
        age_soft_prior=["adult"],
    )
    assert results[0].sku == "sku1"
    assert results[0].passed is True
    assert all(r.passed for r in results)
    assert "sku2" not in [r.sku for r in results]


def test_choose_final_best_selects_highest_score():
    results = [
        RerankResult("a", 0.7, True, True, "Matches retro; in budget"),
        RerankResult("b", 0.8, True, True, "Matches cosy; in budget"),
        RerankResult("c", 0.6, True, True, "Broad appeal"),
    ]
    best = choose_final_best(results)
    assert best == {"best_sku": "b", "why": "Matches cosy in budget"}


def test_out_of_budget_penalty_is_at_least_point15():
    gifts = [
        Gift("mid", "Cozy Throw", 80.0, ("cozy",), meta={}),
        Gift("out", "Premium Throw", 140.0, ("cozy",), meta={}),
    ]
    results = heuristic_rerank(
        gifts,
        taste_top_tags=["cozy"],
        budget=(30.0, 60.0),
        age_soft_prior=[],
        keep_top=2,
    )
    scores = {r.sku: r.score for r in results}
    base_score = 0.45 + 0.4  # overlap ratio = 1.0
    assert base_score - scores.get("out", base_score) >= 0.15
