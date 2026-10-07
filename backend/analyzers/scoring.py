"""Deterministic, documented scoring. Same input always yields the same score.

Per-category score (Security / Code Quality / Complexity / Maintainability):

1. Take the category's findings and map each severity to a weight:
       CRITICAL 25, HIGH 15, MEDIUM 7, LOW 2, INFO 0.5
2. Sort the weights descending. The i-th finding contributes
   ``weight * 0.85 ** i`` — repeated findings of the same severity weigh less
   than the first (diminishing penalty), so one bad module does not nuke the
   score into irrelevance the way a flat sum would.
3. ``score = max(0, round(100 - penalty))``.

Overall score: weighted mean of the four category scores —
Security 35%, Code Quality 25%, Complexity 20%, Maintainability 20% —
because a security hole matters more than a missing docstring.

An INFO-only report keeps a 100 (round-half-even of 99.5): informational
findings are advice, not defects. A parse failure scores nothing at all
(`scores: null`) rather than a fake zero.
"""

from models.analysis import Finding, ScoreBreakdown

SEVERITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 25.0,
    "HIGH": 15.0,
    "MEDIUM": 7.0,
    "LOW": 2.0,
    "INFO": 0.5,
}

DIMINISHING_FACTOR = 0.85

CATEGORY_WEIGHTS: dict[str, float] = {
    "security": 0.35,
    "quality": 0.25,
    "complexity": 0.20,
    "maintainability": 0.20,
}


def category_score(findings: list[Finding]) -> int:
    weights = sorted(
        (SEVERITY_WEIGHTS.get(f.severity, 0.0) for f in findings),
        reverse=True,
    )
    penalty = sum(w * DIMINISHING_FACTOR**i for i, w in enumerate(weights))
    return max(0, round(100 - penalty))


def overall_score(scores: ScoreBreakdown) -> int:
    weighted = (
        CATEGORY_WEIGHTS["security"] * scores.security
        + CATEGORY_WEIGHTS["quality"] * scores.quality
        + CATEGORY_WEIGHTS["complexity"] * scores.complexity
        + CATEGORY_WEIGHTS["maintainability"] * scores.maintainability
    )
    return max(0, min(100, round(weighted)))
