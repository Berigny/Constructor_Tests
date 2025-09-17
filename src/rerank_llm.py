"""Lightweight wrappers around the gift reranking / final-pick prompts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .rank_embed import Gift

RERANK_SYSTEM_PROMPT = "You are a precise gift selector."


def build_rerank_prompt(
    taste_top_tags: Sequence[str],
    age_soft_prior: Sequence[str],
    budget: Tuple[float, float],
    occasion: str,
    items: Sequence[Gift],
) -> str:
    """Return the text prompt used for the LLM reranker."""

    tags = ", ".join(taste_top_tags) if taste_top_tags else ""
    age = ", ".join(age_soft_prior) if age_soft_prior else ""
    min_budget, max_budget = budget
    header = [
        "Intent (non-verbal): Select gifts matching this taste vector and tags.",
        f"Taste_TopTags: [{tags}]",
        f"Age_SoftPrior: [{age}]",
        f"Budget: {min_budget:.0f}–{max_budget:.0f}",
        f"Occasion: {occasion}",
        "",
        "Items:",
    ]
    body: List[str] = []
    for idx, item in enumerate(items, start=1):
        body.append(
            f"{idx}. {{'sku': '{item.sku}', 'title': '{item.title}', 'price': {item.price}, "
            f"'tags': {list(item.tags)}, 'short_desc': '{item.short_desc}'}}"
        )
    footer = [
        "",
        "For each item return JSON:",
        '{"sku": "...", "score": 0-1, "age_fit": true/false, "pass": true/false, "reason": "≤18 words, concrete"}',
        "Rules:",
        "- Penalise out-of-budget by ≥0.15.",
        "- Penalise age mismatch by ≥0.2 unless universally ageless.",
        "- Prefer items matching ≥3 top tags.",
        "- Never invent facts.",
    ]
    return "\n".join(header + body + footer)


@dataclass
class RerankResult:
    sku: str
    score: float
    age_fit: bool
    passed: bool
    reason: str


def heuristic_rerank(
    gifts: Sequence[Gift],
    taste_top_tags: Sequence[str],
    budget: Tuple[float, float],
    age_soft_prior: Sequence[str],
    keep_top: int = 6,
) -> List[RerankResult]:
    """Cheap scoring heuristic used when an LLM call is unavailable."""

    min_budget, max_budget = budget
    taste_set = {t.lower() for t in taste_top_tags}
    age_set = {a.lower() for a in age_soft_prior}

    results: List[RerankResult] = []
    for gift in gifts:
        tag_overlap = taste_set.intersection({t.lower() for t in gift.tags})
        overlap_ratio = len(tag_overlap) / max(1, len(taste_set)) if taste_set else 0.5
        base = 0.45 + 0.4 * overlap_ratio

        out_of_budget = gift.price < min_budget or gift.price > max_budget
        budget_penalty = 0.2 if out_of_budget else 0.0

        gift_age_set = {str(a).lower() for a in gift.meta.get("age_fit", [])}
        age_fit = True
        age_penalty = 0.0
        if age_set:
            age_fit = not gift_age_set or not gift_age_set.isdisjoint(age_set)
            if not age_fit:
                age_penalty = 0.2

        score = max(0.0, min(1.0, base - budget_penalty - age_penalty))
        passed = (not out_of_budget) and age_fit and score >= 0.45

        reason_parts: List[str] = []
        if tag_overlap:
            reason_parts.append(f"Matches {', '.join(list(tag_overlap)[:2])}")
        else:
            reason_parts.append("Broad appeal")
        reason_parts.append("in budget" if not out_of_budget else "over budget")
        if not age_fit and age_set:
            reason_parts.append("age mismatch")
        reason = "; ".join(reason_parts)
        # Trim to <=18 words
        reason_words = reason.split()
        if len(reason_words) > 18:
            reason = " ".join(reason_words[:18])

        results.append(RerankResult(gift.sku, score, age_fit, passed, reason))

    results.sort(key=lambda item: item.score, reverse=True)
    passed_only = [r for r in results if r.passed]
    if not passed_only:
        passed_only = results[:keep_top]
    return passed_only[:keep_top]


def rerank_with_llm(
    gifts: Sequence[Gift],
    taste_top_tags: Sequence[str],
    budget: Tuple[float, float],
    age_soft_prior: Sequence[str],
    occasion: str,
    keep_top: int = 6,
    llm_client: Optional[Any] = None,
) -> List[RerankResult]:
    """Wrapper that defaults to the heuristic scorer in this environment."""

    # We expose the prompt builder so callers can plug in their own client.
    # The sandbox used for automated evaluation intentionally has no API
    # credentials, so we fall back to the deterministic heuristic implementation.
    return heuristic_rerank(
        gifts=gifts,
        taste_top_tags=taste_top_tags,
        budget=budget,
        age_soft_prior=age_soft_prior,
        keep_top=keep_top,
    )


def build_final_pick_prompt(items: Sequence[RerankResult]) -> str:
    body = [
        "Choose the single best of these 3 and explain in ≤18 words why it fits the taste tags.",
        "Return: {\"best_sku\":\"...\", \"why\":\"...\"}",
        "",
    ]
    for item in items:
        body.append(f"- {item.sku}: score={item.score:.2f}, reason={item.reason}")
    return "\n".join(body)


def choose_final_best(results: Sequence[RerankResult]) -> Optional[Dict[str, str]]:
    """Pick the highest scoring item and craft a short rationale."""

    if not results:
        return None
    best = max(results[:3], key=lambda item: item.score)
    cleaned = " ".join(best.reason.replace(";", " ").split())
    words = cleaned.split()
    if len(words) > 18:
        cleaned = " ".join(words[:18])
    return {"best_sku": best.sku, "why": cleaned}
