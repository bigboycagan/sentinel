"""Engine entry point: language registry + the `analyze_code` boundary.

The engine is the seam for future work:
  * a new language = a new `analyzers/<lang>/` package whose analyzer class is
    registered in `_ANALYZERS` — no core changes;
  * a future AI layer (`intelligence.Explainer`) would consume the
    `AnalysisReport` this function returns. v1 deliberately ships without it.
"""

from __future__ import annotations

from analyzers.base import Rule
from analyzers.python.analyzer import PythonAnalyzer


class EmptySourceError(ValueError):
    """Raised when there is no source code to analyze."""


class UnsupportedLanguageError(ValueError):
    """Raised when no analyzer is registered for the requested language."""


_ANALYZERS = {
    PythonAnalyzer.language: PythonAnalyzer(),
}


def get_analyzer(language: str) -> PythonAnalyzer:
    analyzer = _ANALYZERS.get((language or "").strip().lower())
    if analyzer is None:
        raise UnsupportedLanguageError(
            "Unsupported language. SENTINEL v1 currently supports Python."
        )
    return analyzer


def supports_extension(file_name: str) -> bool:
    lower = file_name.lower()
    return any(lower.endswith(ext) for analyzer in _ANALYZERS.values() for ext in analyzer.extensions)


def all_rules() -> list[Rule]:
    """Every registered rule across every language (catalog source of truth)."""
    rules: list[Rule] = []
    for analyzer in _ANALYZERS.values():
        rules.extend(analyzer.rules)
    return rules


def analyze_code(
    code: str,
    file_name: str,
    language: str = "python",
    disabled_rules: list[str] | None = None,
):
    """Analyze source text and return an AnalysisReport. Pure-static, never executes code."""
    if code is None or not code.strip():
        raise EmptySourceError("Please provide source code to analyze.")
    analyzer = get_analyzer(language)
    return analyzer.analyze(code, file_name, disabled_rules or [])
