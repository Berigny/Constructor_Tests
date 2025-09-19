"""Simple HTML-based image choice Streamlit component."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import streamlit.components.v1 as components

_COMPONENT_FUNC = components.declare_component(
    "image_choice",
    path=str(Path(__file__).parent),
)


def _prepare_alts(images: Sequence[str], alts: Optional[Sequence[str]]) -> Sequence[str]:
    if alts is None:
        return ["" for _ in images]
    prepared = [str(a) if a is not None else "" for a in alts]
    if len(prepared) < len(images):
        prepared.extend(["" for _ in range(len(images) - len(prepared))])
    elif len(prepared) > len(images):
        prepared = prepared[: len(images)]
    return prepared


def image_choice(
    *,
    images: Sequence[str],
    alts: Optional[Sequence[str]] = None,
    key: Optional[str] = None,
) -> Optional[str]:
    """Render two selectable images and return the chosen action."""

    safe_images = [str(src) if src is not None else "" for src in images]
    safe_alts = list(_prepare_alts(safe_images, alts))
    return _COMPONENT_FUNC(images=safe_images, alts=safe_alts, key=key, default=None)


__all__ = ["image_choice"]
