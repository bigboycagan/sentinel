"""Shared vocabulary for the rule engine: severities, categories, Rule, RuleHit.

Adding a new rule = adding one `Rule(...)` entry to a rules module's list.
Nothing else in the engine needs to change (rules auto-appear in the catalog,
the analyzer run, scoring, and the rules API).
"""

from dataclasses import dataclass
from typing import Any, Callable, Iterable

CRITICAL = "CRITICAL"
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"
INFO = "INFO"

SEVERITIES: tuple[str, ...] = (CRITICAL, HIGH, MEDIUM, LOW, INFO)
SEVERITY_ORDER: dict[str, int] = {sev: rank for rank, sev in enumerate(SEVERITIES)}

CATEGORY_SECURITY = "Security"
CATEGORY_QUALITY = "Code Quality"
CATEGORY_COMPLEXITY = "Complexity"
CATEGORY_MAINTAINABILITY = "Maintainability"
CATEGORIES: tuple[str, ...] = (
    CATEGORY_SECURITY,
    CATEGORY_QUALITY,
    CATEGORY_COMPLEXITY,
    CATEGORY_MAINTAINABILITY,
)


@dataclass
class RuleHit:
    """One concrete occurrence of a rule in the source."""

    line: int
    column: int = 1
    message: str = ""
    severity: str | None = None  # override the rule's default severity


@dataclass
class Rule:
    """A single deterministic check. `check` receives the language RuleContext."""

    rule_id: str
    title: str
    category: str
    severity: str
    description: str
    recommendation: str
    check: Callable[[Any], Iterable[RuleHit]]
    language: str = "python"
