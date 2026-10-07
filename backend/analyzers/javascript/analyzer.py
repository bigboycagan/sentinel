"""JavaScriptAnalyzer — handles JavaScript and TypeScript (incl. JSX/TSX).

One analyzer serves both languages because they share a rule set; TypeScript
additionally runs rules declared with `language="typescript"` (e.g. explicit
`any`). Registered in analyzers/engine.py.
"""

from __future__ import annotations

from analyzers.base import Rule
from analyzers.javascript.context import JsRuleContext
from analyzers.javascript.metrics import compute_module_metrics, textual_line_metrics
from analyzers.javascript.parser import parse_source
from analyzers.javascript.rules import (
    COMPLEXITY_RULES,
    MAINTAINABILITY_RULES,
    QUALITY_RULES,
    SECURITY_RULES,
)
from analyzers.report import assemble_report, parse_error_report, run_rules
from models.analysis import AnalysisReport

JAVASCRIPT = "javascript"
TYPESCRIPT = "typescript"


class JavaScriptAnalyzer:
    """Analyzer for one JS-family language; instantiated per language id."""

    extensions_by_language = {
        JAVASCRIPT: (".js", ".jsx", ".mjs", ".cjs"),
        TYPESCRIPT: (".ts", ".tsx", ".mts", ".cts"),
    }

    def __init__(self, language: str = JAVASCRIPT) -> None:
        if language not in self.extensions_by_language:
            raise ValueError(f"unsupported JS-family language: {language}")
        self.language = language
        self.extensions = self.extensions_by_language[language]
        allowed = {JAVASCRIPT, language}
        self.rules: list[Rule] = [
            rule
            for rule in (
                *SECURITY_RULES,
                *QUALITY_RULES,
                *COMPLEXITY_RULES,
                *MAINTAINABILITY_RULES,
            )
            if rule.language in allowed
        ]

    def analyze(
        self,
        code: str,
        file_name: str,
        disabled_rules: list[str],
    ) -> AnalysisReport:
        lines = code.splitlines()
        textual = textual_line_metrics(code)
        tree, parse_error = parse_source(code, file_name, self.language)

        if parse_error is not None:
            return parse_error_report(file_name, self.language, textual, parse_error)

        metrics = compute_module_metrics(tree, code)
        ctx = JsRuleContext(
            tree=tree,
            code=code,
            lines=lines,
            file_name=file_name,
            language=self.language,
            metrics=metrics,
        )
        findings = run_rules(self.rules, ctx, file_name, lines, disabled_rules)
        return assemble_report(file_name, self.language, metrics, findings)
