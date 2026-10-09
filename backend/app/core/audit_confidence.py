from typing import Optional


def derive_confidence_band(
    *,
    numeric_confidence: Optional[float] = None,
    urgency_level: Optional[str] = None,
    red_flags_count: int = 0,
    output_summary: Optional[str] = None,
) -> str:
    """Derive a normalized low/medium/high confidence band for audit logs.

    Prefers explicit numeric confidence when present; otherwise falls back to
    deterministic heuristics from urgency, red flags, and linguistic certainty.
    """
    if numeric_confidence is not None:
        value = float(numeric_confidence)
        if value >= 0.80:
            return "high"
        if value >= 0.45:
            return "medium"
        return "low"

    score = 0
    urgency = (urgency_level or "").strip().upper()
    text = (output_summary or "").lower()

    if urgency in {"EMERGENCY", "CRITICAL", "EMERGENCY"}:
        score += 2
    elif urgency in {"URGENT", "HIGH"}:
        score += 1

    if red_flags_count >= 2:
        score += 2
    elif red_flags_count == 1:
        score += 1

    uncertainty_markers = [
        "unclear",
        "not sure",
        "possibly",
        "might",
        "cannot determine",
        "unable to determine",
        "unknown",
    ]
    if any(marker in text for marker in uncertainty_markers):
        score -= 2

    if len(text.strip()) < 40:
        score -= 1

    if score >= 2:
        return "high"
    if score >= 0:
        return "medium"
    return "low"

