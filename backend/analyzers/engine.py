"""Engine entry point: language registry + the `analyze_code` boundary.

The engine is the seam for future work:
  * a new language = a new `analyzers/<lang>/` package whose analyzer class is
    registered in `_ANALYZERS` — no core, scoring or API changes;
  * a future AI layer (`intelligence.Explainer`) would consume the
    `AnalysisReport` this function returns. v1 deliberately ships without it.
"""

from __future__ import annotations

from dataclasses import dataclass

from analyzers.base import Rule
from analyzers.javascript.analyzer import JAVASCRIPT, TYPESCRIPT, JavaScriptAnalyzer
from analyzers.python.analyzer import PythonAnalyzer


class EmptySourceError(ValueError):
    """Raised when there is no source code to analyze."""


class UnsupportedLanguageError(ValueError):
    """Raised when no analyzer is registered for the requested language."""


# Every registered language. Adding one here is the only wiring a new
# analyzer needs: the rules catalog, upload validation, the /languages
# endpoint and the frontend selector are all derived from this map.
_ANALYZERS = {
    PythonAnalyzer.language: PythonAnalyzer(),
    JAVASCRIPT: JavaScriptAnalyzer(JAVASCRIPT),
    TYPESCRIPT: JavaScriptAnalyzer(TYPESCRIPT),
}

_LABELS = {
    "python": "Python",
    JAVASCRIPT: "JavaScript",
    TYPESCRIPT: "TypeScript",
}


@dataclass(frozen=True)
class LanguageInfo:
    id: str
    label: str
    extensions: tuple[str, ...]


def supported_languages() -> list[LanguageInfo]:
    return [
        LanguageInfo(id=key, label=_LABELS.get(key, key.title()), extensions=analyzer.extensions)
        for key, analyzer in _ANALYZERS.items()
    ]


def all_extensions() -> tuple[str, ...]:
    seen: list[str] = []
    for analyzer in _ANALYZERS.values():
        for extension in analyzer.extensions:
            if extension not in seen:
                seen.append(extension)
    return tuple(seen)


def get_analyzer(language: str):
    analyzer = _ANALYZERS.get((language or "").strip().lower())
    if analyzer is None:
        supported = ", ".join(info.label for info in supported_languages())
        raise UnsupportedLanguageError(f"Unsupported language. SENTINEL supports: {supported}.")
    return analyzer


def language_for_file(file_name: str) -> str | None:
    """Infer the language from a file extension, or None when unsupported."""
    lower = (file_name or "").lower()
    for key, analyzer in _ANALYZERS.items():
        if lower.endswith(analyzer.extensions):
            return key
    return None


def supports_extension(file_name: str) -> bool:
    return language_for_file(file_name) is not None


def all_rules() -> list[Rule]:
    """Every registered rule, de-duplicated by rule id (catalog source of truth).

    Analyzers may share rule objects — the JS and TS analyzers deliberately
    reuse the JavaScript rule set — so the catalog dedupes.
    """
    rules: list[Rule] = []
    seen: set[str] = set()
    for analyzer in _ANALYZERS.values():
        for rule in analyzer.rules:
            if rule.rule_id in seen:
                continue
            seen.add(rule.rule_id)
            rules.append(rule)
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
