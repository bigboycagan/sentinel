"""CPL* — complexity findings, driven by the metrics module."""

from __future__ import annotations

from analyzers.base import CATEGORY_COMPLEXITY, CRITICAL, HIGH, LOW, MEDIUM, Rule, RuleHit
from analyzers.python.context import RuleContext

COMPLEXITY_THRESHOLD = 10
HIGH_COMPLEXITY_THRESHOLD = 15
CRITICAL_COMPLEXITY_THRESHOLD = 20
AVG_COMPLEXITY_THRESHOLD = 8
AVG_COMPLEXITY_MIN_FUNCTIONS = 3


def _tier(complexity: int) -> str | None:
    if complexity > CRITICAL_COMPLEXITY_THRESHOLD:
        return CRITICAL
    if complexity > HIGH_COMPLEXITY_THRESHOLD:
        return HIGH
    if complexity > COMPLEXITY_THRESHOLD:
        return MEDIUM
    return None


def _check_high_complexity(ctx: RuleContext):
    for fm in ctx.metrics.functions:
        severity = _tier(fm.complexity)
        if severity is None:
            continue
        yield RuleHit(
            line=fm.line,
            column=1,
            message=f'Function "{fm.name}" has a cyclomatic complexity of {fm.complexity} '
            f"(threshold: {COMPLEXITY_THRESHOLD}).",
            severity=severity,
        )


def _check_avg_complexity(ctx: RuleContext):
    metrics = ctx.metrics
    if (
        metrics.function_count >= AVG_COMPLEXITY_MIN_FUNCTIONS
        and (metrics.avg_complexity or 0) > AVG_COMPLEXITY_THRESHOLD
    ):
        yield RuleHit(
            line=1,
            column=1,
            message=f"Average cyclomatic complexity across {metrics.function_count} functions "
            f"is {metrics.avg_complexity} (threshold: {AVG_COMPLEXITY_THRESHOLD}).",
            severity=LOW,
        )


COMPLEXITY_RULES: list[Rule] = [
    Rule(
        rule_id="CPL001",
        title="High Cyclomatic Complexity",
        category=CATEGORY_COMPLEXITY,
        severity=MEDIUM,
        description="A function contains more than 10 independent branches (if/for/while/"
        "except/bool-ops/comprehensions). Severity escalates: >15 HIGH, >20 CRITICAL.",
        recommendation="Split the function and replace branch chains with lookups/"
        "polymorphism where possible.",
        check=_check_high_complexity,
    ),
    Rule(
        rule_id="CPL002",
        title="High Average Complexity",
        category=CATEGORY_COMPLEXITY,
        severity=LOW,
        description="The file's average cyclomatic complexity exceeds 8 across 3+ functions.",
        recommendation="Refactor the densest functions; the file's logic is getting heavy.",
        check=_check_avg_complexity,
    ),
]
