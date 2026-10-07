"""JS-CPL* — complexity findings for JavaScript / TypeScript, driven by metrics."""

from __future__ import annotations

from analyzers.base import CATEGORY_COMPLEXITY, CRITICAL, HIGH, LOW, MEDIUM, Rule, RuleHit
from analyzers.javascript.context import JsRuleContext

LANG = "javascript"

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


def _check_high_complexity(ctx: JsRuleContext):
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


def _check_avg_complexity(ctx: JsRuleContext):
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
        rule_id="JS-CPL001",
        title="High Cyclomatic Complexity",
        category=CATEGORY_COMPLEXITY,
        severity=MEDIUM,
        description="A function contains more than 10 independent branches (if/ternary/"
        "loops/switch cases/catch/&&/||/??). Severity escalates: >15 HIGH, >20 CRITICAL.",
        recommendation="Split the function and replace branch chains with lookup tables or "
        "polymorphism.",
        check=_check_high_complexity,
        language=LANG,
    ),
    Rule(
        rule_id="JS-CPL002",
        title="High Average Complexity",
        category=CATEGORY_COMPLEXITY,
        severity=LOW,
        description="The file's average cyclomatic complexity exceeds 8 across 3+ functions.",
        recommendation="Refactor the densest functions; the module's logic is getting heavy.",
        check=_check_avg_complexity,
        language=LANG,
    ),
]
