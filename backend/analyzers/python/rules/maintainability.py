"""MNT* — maintainability indicators computed from measurable metrics.

None of these are AI insights: they are deterministic formulas over the AST
and token stream (see analyzers/python/metrics.py for the formulas).
"""

from __future__ import annotations

from analyzers.base import CATEGORY_MAINTAINABILITY, HIGH, INFO, LOW, MEDIUM, Rule, RuleHit
from analyzers.python.context import RuleContext

MI_MEDIUM_THRESHOLD = 65
MI_HIGH_THRESHOLD = 50
DOCSTRING_MIN_LENGTH = 20


def _check_maintainability_index(ctx: RuleContext):
    mi = ctx.metrics.maintainability_index()
    if mi >= MI_MEDIUM_THRESHOLD:
        return
    severity = HIGH if mi < MI_HIGH_THRESHOLD else MEDIUM
    yield RuleHit(
        line=1,
        column=1,
        message=f"The file's maintainability index is {mi}/100 "
        f"(thresholds: {MI_MEDIUM_THRESHOLD} medium, {MI_HIGH_THRESHOLD} high).",
        severity=severity,
    )


def _check_missing_module_docstring(ctx: RuleContext):
    if not ctx.metrics.module_has_docstring:
        yield RuleHit(
            line=1,
            column=1,
            message="The module has no docstring describing its purpose.",
            severity=INFO,
        )


def _check_undocumented_function(ctx: RuleContext):
    for fm in ctx.metrics.functions:
        if fm.length > DOCSTRING_MIN_LENGTH and not fm.has_docstring:
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function "{fm.name}" is {fm.length} lines long and has no docstring.',
                severity=LOW,
            )


MAINTAINABILITY_RULES: list[Rule] = [
    Rule(
        rule_id="MNT001",
        title="Low Maintainability Index",
        category=CATEGORY_MAINTAINABILITY,
        severity=MEDIUM,
        description="The radon-derived maintainability index (volume, complexity, SLOC) "
        "is below 65/100. Below 50 is HIGH.",
        recommendation="Reduce function size/complexity and break the module up.",
        check=_check_maintainability_index,
    ),
    Rule(
        rule_id="MNT002",
        title="Missing Module Docstring",
        category=CATEGORY_MAINTAINABILITY,
        severity=INFO,
        description="The module does not start with a docstring explaining what it is for.",
        recommendation="Add a one-paragraph module docstring.",
        check=_check_missing_module_docstring,
    ),
    Rule(
        rule_id="MNT003",
        title="Long Function Without Docstring",
        category=CATEGORY_MAINTAINABILITY,
        severity=LOW,
        description="A function longer than 20 lines has no docstring.",
        recommendation="Document parameters, return values and side effects.",
        check=_check_undocumented_function,
    ),
]
