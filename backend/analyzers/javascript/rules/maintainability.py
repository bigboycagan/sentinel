"""JS-MNT* — maintainability indicators for JavaScript / TypeScript.

Deterministic formulas over the AST and token stream (see metrics.py) — not
AI-derived insight.
"""

from __future__ import annotations

from analyzers.base import CATEGORY_MAINTAINABILITY, HIGH, INFO, LOW, MEDIUM, Rule, RuleHit
from analyzers.javascript.context import JsRuleContext

LANG = "javascript"

MI_MEDIUM_THRESHOLD = 65
MI_HIGH_THRESHOLD = 50
DOC_MIN_LENGTH = 20
MAX_PARAMS = 5


def _check_maintainability_index(ctx: JsRuleContext):
    mi = ctx.metrics.maintainability_index()
    if mi >= MI_MEDIUM_THRESHOLD:
        return
    yield RuleHit(
        line=1,
        column=1,
        message=f"The file's maintainability index is {mi}/100 "
        f"(thresholds: {MI_MEDIUM_THRESHOLD} medium, {MI_HIGH_THRESHOLD} high).",
        severity=HIGH if mi < MI_HIGH_THRESHOLD else MEDIUM,
    )


def _check_missing_module_doc(ctx: JsRuleContext):
    if not ctx.metrics.module_has_docstring and ctx.metrics.source_lines > 10:
        yield RuleHit(
            line=1,
            column=1,
            message="The module has no header comment describing its purpose.",
            severity=INFO,
        )


def _check_undocumented_function(ctx: JsRuleContext):
    for fm in ctx.metrics.functions:
        if fm.length > DOC_MIN_LENGTH and not fm.has_docstring and fm.name != "(anonymous)":
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function "{fm.name}" is {fm.length} lines long and has no '
                "documentation comment.",
                severity=LOW,
            )


def _check_too_many_parameters(ctx: JsRuleContext):
    for fm in ctx.metrics.functions:
        if fm.param_count > MAX_PARAMS:
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function "{fm.name}" takes {fm.param_count} parameters '
                f"(threshold: {MAX_PARAMS}).",
            )


MAINTAINABILITY_RULES: list[Rule] = [
    Rule(
        rule_id="JS-MNT001",
        title="Low Maintainability Index",
        category=CATEGORY_MAINTAINABILITY,
        severity=MEDIUM,
        description="The maintainability index (Halstead volume, complexity, SLOC) is "
        "below 65/100. Below 50 is HIGH.",
        recommendation="Reduce function size/complexity and break the module up.",
        check=_check_maintainability_index,
        language=LANG,
    ),
    Rule(
        rule_id="JS-MNT002",
        title="Missing Module Header",
        category=CATEGORY_MAINTAINABILITY,
        severity=INFO,
        description="The module does not open with a comment explaining what it is for.",
        recommendation="Add a short header comment.",
        check=_check_missing_module_doc,
        language=LANG,
    ),
    Rule(
        rule_id="JS-MNT003",
        title="Long Function Without Documentation",
        category=CATEGORY_MAINTAINABILITY,
        severity=LOW,
        description="A function longer than 20 lines has no preceding documentation comment.",
        recommendation="Document parameters, return value and side effects (JSDoc).",
        check=_check_undocumented_function,
        language=LANG,
    ),
    Rule(
        rule_id="JS-MNT004",
        title="Too Many Parameters",
        category=CATEGORY_MAINTAINABILITY,
        severity=LOW,
        description="A function takes more than 5 parameters, which is hard to call "
        "correctly and to refactor.",
        recommendation="Group related parameters into an options object.",
        check=_check_too_many_parameters,
        language=LANG,
    ),
]
