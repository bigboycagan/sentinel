"""PythonAnalyzer — orchestrates parsing, metrics, rules and scoring."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from analyzers.base import (
    CATEGORIES,
    CATEGORY_COMPLEXITY,
    CATEGORY_MAINTAINABILITY,
    CATEGORY_QUALITY,
    CATEGORY_SECURITY,
    SEVERITIES,
    SEVERITY_ORDER,
    Rule,
    RuleHit,
)
from analyzers.python.context import RuleContext
from analyzers.python.metrics import (
    ModuleMetrics,
    compute_module_metrics,
    textual_line_metrics,
)
from analyzers.python.parser import parse_source
from analyzers.python.rules import (
    COMPLEXITY_RULES,
    MAINTAINABILITY_RULES,
    QUALITY_RULES,
    SECURITY_RULES,
)
from analyzers.scoring import category_score, overall_score
from models.analysis import (
    AnalysisReport,
    FileMetrics,
    Finding,
    ParseErrorInfo,
    ScoreBreakdown,
    SeverityCounts,
)


def _build_finding(rule: Rule, hit: RuleHit, file_name: str, lines: list[str]) -> Finding:
    snippet = None
    if 1 <= hit.line <= len(lines):
        snippet = lines[hit.line - 1].strip()[:240] or None
    return Finding(
        rule_id=rule.rule_id,
        severity=hit.severity or rule.severity,
        category=rule.category,
        title=rule.title,
        message=hit.message or rule.description,
        file=file_name,
        line=hit.line,
        column=hit.column,
        recommendation=rule.recommendation,
        code_snippet=snippet,
    )


def _counts(findings: list[Finding]) -> SeverityCounts:
    counts = {sev: 0 for sev in SEVERITIES}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return SeverityCounts(
        total=len(findings),
        critical=counts["CRITICAL"],
        high=counts["HIGH"],
        medium=counts["MEDIUM"],
        low=counts["LOW"],
        info=counts["INFO"],
    )


def _metrics_model(metrics: ModuleMetrics) -> FileMetrics:
    return FileMetrics(
        total_lines=metrics.total_lines,
        source_lines=metrics.source_lines,
        comment_lines=metrics.comment_lines,
        blank_lines=metrics.blank_lines,
        function_count=metrics.function_count,
        class_count=metrics.class_count,
        max_nesting_depth=metrics.max_nesting_depth,
        avg_function_length=metrics.avg_function_length,
        avg_complexity=metrics.avg_complexity,
        max_complexity=metrics.max_complexity,
        maintainability_index=metrics.maintainability_index(),
    )


def _empty_metrics(total: int, source: int, comments: int, blank: int) -> FileMetrics:
    return FileMetrics(
        total_lines=total,
        source_lines=source,
        comment_lines=comments,
        blank_lines=blank,
        function_count=0,
        class_count=0,
        max_nesting_depth=None,
        avg_function_length=None,
        avg_complexity=None,
        max_complexity=None,
        maintainability_index=None,
    )


class PythonAnalyzer:
    """One analyzer per language. Registered in analyzers/engine.py."""

    language = "python"
    extensions = (".py",)

    def __init__(self) -> None:
        self.rules: list[Rule] = [
            *SECURITY_RULES,
            *QUALITY_RULES,
            *COMPLEXITY_RULES,
            *MAINTAINABILITY_RULES,
        ]

    def analyze(
        self,
        code: str,
        file_name: str,
        disabled_rules: list[str],
    ) -> AnalysisReport:
        now = datetime.now(timezone.utc)
        lines = code.splitlines()
        textual = textual_line_metrics(code)
        tree, parse_error = parse_source(code)

        if parse_error is not None:
            # No AST → no findings, no fake scores. Surface the syntax error instead.
            return AnalysisReport(
                id=str(uuid.uuid4()),
                file_name=file_name,
                language=self.language,
                analyzed_at=now,
                scores=None,
                overall_score=None,
                counts=_counts([]),
                metrics=_empty_metrics(textual.total, textual.source, textual.comments, textual.blank),
                findings=[],
                parse_error=ParseErrorInfo(**parse_error),
            )

        metrics = compute_module_metrics(tree, code)
        ctx = RuleContext(tree=tree, code=code, lines=lines, file_name=file_name, metrics=metrics)
        disabled = set(disabled_rules or [])
        seen: set[tuple[str, int]] = set()
        findings: list[Finding] = []
        for rule in self.rules:
            if rule.rule_id in disabled:
                continue
            for hit in rule.check(ctx):
                key = (rule.rule_id, hit.line)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(_build_finding(rule, hit, file_name, lines))

        findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.line, f.column, f.rule_id))
        by_category = {cat: [] for cat in CATEGORIES}
        for finding in findings:
            by_category.setdefault(finding.category, []).append(finding)
        scores = ScoreBreakdown(
            security=category_score(by_category[CATEGORY_SECURITY]),
            quality=category_score(by_category[CATEGORY_QUALITY]),
            complexity=category_score(by_category[CATEGORY_COMPLEXITY]),
            maintainability=category_score(by_category[CATEGORY_MAINTAINABILITY]),
        )
        return AnalysisReport(
            id=str(uuid.uuid4()),
            file_name=file_name,
            language=self.language,
            analyzed_at=now,
            scores=scores,
            overall_score=overall_score(scores),
            counts=_counts(findings),
            metrics=_metrics_model(metrics),
            findings=findings,
            parse_error=None,
        )
