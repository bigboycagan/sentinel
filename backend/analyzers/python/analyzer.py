"""PythonAnalyzer — orchestrates parsing, metrics, rules and scoring.

Report assembly, severity counting and scoring are shared with every other
language analyzer via `analyzers/report.py`.
"""

from __future__ import annotations

from analyzers.base import Rule
from analyzers.python.context import RuleContext
from analyzers.python.metrics import compute_module_metrics, textual_line_metrics
from analyzers.python.parser import parse_source
from analyzers.python.rules import (
    COMPLEXITY_RULES,
    MAINTAINABILITY_RULES,
    QUALITY_RULES,
    SECURITY_RULES,
)
from analyzers.report import assemble_report, parse_error_report, run_rules
from models.analysis import AnalysisReport


class PythonAnalyzer:
    """One analyzer per language. Registered in analyzers/engine.py."""

    language = "python"
    extensions = (".py", ".pyi")

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
        lines = code.splitlines()
        textual = textual_line_metrics(code)
        tree, parse_error = parse_source(code)

        if parse_error is not None:
            return parse_error_report(file_name, self.language, textual, parse_error)

        metrics = compute_module_metrics(tree, code)
        ctx = RuleContext(
            tree=tree,
            code=code,
            lines=lines,
            file_name=file_name,
            metrics=metrics,
        )
        findings = run_rules(self.rules, ctx, file_name, lines, disabled_rules)
        return assemble_report(file_name, self.language, metrics, findings)
