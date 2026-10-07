"""Rule context handed to every JS/TS check function."""

from __future__ import annotations

from dataclasses import dataclass

from tree_sitter import Node, Tree

from analyzers.javascript.metrics import ModuleMetrics


@dataclass
class JsRuleContext:
    tree: Tree
    code: str
    lines: list[str]
    file_name: str
    language: str  # "javascript" | "typescript"
    metrics: ModuleMetrics

    @property
    def root(self) -> Node:
        return self.tree.root_node

    @property
    def is_typescript(self) -> bool:
        return self.language == "typescript"
