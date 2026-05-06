"""Resume / JD analysis: similarity + recommendation."""

from __future__ import annotations

from scripts.preprocess import preprocess_text
from scripts.semantic_similarity import get_semantic_similarity


def similarity(resume_text: str, jd_text: str) -> float:
    """Cosine similarity of sentence-transformer embeddings, clamped to [0, 1]."""
    cleaned_resume = preprocess_text(resume_text or "")
    cleaned_jd = preprocess_text(jd_text or "")
    try:
        s = float(get_semantic_similarity(cleaned_resume, cleaned_jd))
    except Exception:
        return 0.0
    return max(0.0, min(1.0, s))


def recommendation(sim: float, missing_count: int) -> str:
    if sim >= 0.70 and missing_count <= 2:
        return "STRONG MATCH – Recommended to Apply"
    if sim >= 0.40:
        return "MODERATE MATCH – You Can Apply"
    return "WEAK MATCH – Not Recommended"
