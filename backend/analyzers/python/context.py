"""Per-language rule context handed to every check function."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from analyzers.python.metrics import ModuleMetrics


@dataclass
class RuleContext:
    tree: ast.Module
    code: str
    lines: list[str]
    file_name: str
    metrics: ModuleMetrics
