"""SENTINEL rule modules. One module per category; each exports a list of Rule.

Adding a rule = appending a Rule(...) to the relevant module's list. The
analyzer, the /api/rules catalog and scoring pick it up automatically.
"""

from analyzers.python.rules.complexity import COMPLEXITY_RULES
from analyzers.python.rules.maintainability import MAINTAINABILITY_RULES
from analyzers.python.rules.quality import QUALITY_RULES
from analyzers.python.rules.security import SECURITY_RULES

__all__ = [
    "SECURITY_RULES",
    "QUALITY_RULES",
    "COMPLEXITY_RULES",
    "MAINTAINABILITY_RULES",
]
