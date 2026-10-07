"""JS/TS rule modules. One module per category; each exports a list of Rule.

Adding a rule = appending a Rule(...) to the relevant list. The analyzer, the
/api/rules catalog and Settings' toggles pick it up automatically.
"""

from analyzers.javascript.rules.complexity import COMPLEXITY_RULES
from analyzers.javascript.rules.maintainability import MAINTAINABILITY_RULES
from analyzers.javascript.rules.quality import QUALITY_RULES
from analyzers.javascript.rules.security import SECURITY_RULES

__all__ = [
    "SECURITY_RULES",
    "QUALITY_RULES",
    "COMPLEXITY_RULES",
    "MAINTAINABILITY_RULES",
]
