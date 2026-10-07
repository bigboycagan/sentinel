"""Shared report assembly for every language analyzer.

Both the Python and JavaScript/TypeScript analyzers produce the same
`AnalysisReport`, so finding construction, severity counting, metric mapping
and scoring live here once. A new language analyzer only has to supply a
parsed context plus its metrics object.

The metrics argument is duck-typed: any object exposing the properties of
`analyzers.python.metrics.ModuleMetrics` works, which is what keeps the
per-language metrics modules independent.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Iterable, Protocol

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
from analyzers.scoring import category_score, overall_score
from models.analysis import (
    AnalysisReport,
    FileMetrics,
    Finding,
    ParseErrorInfo,
    ScoreBreakdown,
    SeverityCounts,
)


class LineCounts(Protocol):
    total: int
    source: int
    comments: int
    blank: int


def build_finding(rule: Rule, hit: RuleHit, file_name: str, lines: list[str]) -> Finding:
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


def run_rules(
    rules: Iterable[Rule],
    ctx: Any,
    file_name: str,
    lines: list[str],
    disabled_rules: Iterable[str],
) -> list[Finding]:
    """Execute every enabled rule, de-duplicating (rule_id, line) pairs."""
    disabled = set(disabled_rules or ())
    seen: set[tuple[str, int]] = set()
    findings: list[Finding] = []
    for rule in rules:
        if rule.rule_id in disabled:
            continue
        for hit in rule.check(ctx):
            key = (rule.rule_id, hit.line)
            if key in seen:
                continue
            seen.add(key)
            findings.append(build_finding(rule, hit, file_name, lines))
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.line, f.column, f.rule_id))
    return findings


def severity_counts(findings: list[Finding]) -> SeverityCounts:
    counts = {severity: 0 for severity in SEVERITIES}
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


def metrics_model(metrics: Any) -> FileMetrics:
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


def empty_metrics(lines: LineCounts) -> FileMetrics:
    return FileMetrics(
        total_lines=lines.total,
        source_lines=lines.source,
        comment_lines=lines.comments,
        blank_lines=lines.blank,
        function_count=0,
        class_count=0,
        max_nesting_depth=None,
        avg_function_length=None,
        avg_complexity=None,
        max_complexity=None,
        maintainability_index=None,
    )


def parse_error_report(
    file_name: str,
    language: str,
    lines: LineCounts,
    parse_error: dict,
) -> AnalysisReport:
    """No AST means no findings and NO scores — never a fabricated zero."""
    return AnalysisReport(
        id=str(uuid.uuid4()),
        file_name=file_name,
        language=language,
        analyzed_at=datetime.now(timezone.utc),
        scores=None,
        overall_score=None,
        counts=severity_counts([]),
        metrics=empty_metrics(lines),
        findings=[],
        parse_error=ParseErrorInfo(**parse_error),
    )


def assemble_report(
    file_name: str,
    language: str,
    metrics: Any,
    findings: list[Finding],
) -> AnalysisReport:
    by_category: dict[str, list[Finding]] = {category: [] for category in CATEGORIES}
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
        language=language,
        analyzed_at=datetime.now(timezone.utc),
        scores=scores,
        overall_score=overall_score(scores),
        counts=severity_counts(findings),
        metrics=metrics_model(metrics),
        findings=findings,
        parse_error=None,
    )
