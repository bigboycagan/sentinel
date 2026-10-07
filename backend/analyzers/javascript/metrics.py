"""Deterministic source metrics for JavaScript / TypeScript.

Mirrors the Python analyzer's definitions so scores are comparable:

* Line classes are textual — blank, comment (`//` or `/*` opener), else source.
* Cyclomatic complexity per function: ``1 + branch points`` where a branch
  point is if, ternary, for / for-in / for-of, while, do-while, each switch
  case, each catch clause, and each `&&` / `||` / `??` operator. Nested
  functions are measured as their own blocks.
* Max nesting depth: deepest chain of if/for/while/do/try/switch/with inside a
  function (nested scopes measured separately).
* Halstead volume: ``V = (N1 + N2) * log2(n1 + n2)`` over operator tokens and
  operand tokens (identifiers, literals) taken from the syntax tree.
* Maintainability Index, identical formula to the Python side:
  ``MI = (171 - 5.2*ln(V) - 0.23*avg_cc - 16.2*SLOC/1000) * 100 / 171``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from tree_sitter import Node, Tree

from analyzers.javascript.nodes import (
    is_class_node,
    is_function_node,
    text,
    walk,
    walk_own_scope,
)

BRANCH_NODES = frozenset(
    {
        "if_statement",
        "ternary_expression",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "catch_clause",
        "switch_case",
    }
)

NESTING_NODES = frozenset(
    {
        "if_statement",
        "for_statement",
        "for_in_statement",
        "while_statement",
        "do_statement",
        "try_statement",
        "switch_statement",
        "with_statement",
    }
)

SHORT_CIRCUIT_OPERATORS = frozenset({"&&", "||", "??"})

OPERAND_NODES = frozenset(
    {
        "identifier",
        "property_identifier",
        "shorthand_property_identifier",
        "number",
        "string_fragment",
        "regex",
        "true",
        "false",
        "null",
        "undefined",
        "this",
        "super",
        "type_identifier",
    }
)

IMPORT_NODES = frozenset({"import_statement", "import_require_clause"})


@dataclass
class FunctionMetrics:
    name: str
    line: int
    length: int
    complexity: int
    max_nesting: int
    has_docstring: bool
    param_count: int


@dataclass
class ModuleMetrics:
    total_lines: int
    source_lines: int
    comment_lines: int
    blank_lines: int
    halstead_volume: float
    functions: list[FunctionMetrics] = field(default_factory=list)
    class_count: int = 0
    import_count: int = 0
    module_has_docstring: bool = False

    @property
    def function_count(self) -> int:
        return len(self.functions)

    @property
    def max_complexity(self) -> int | None:
        return max((f.complexity for f in self.functions), default=None)

    @property
    def avg_complexity(self) -> float | None:
        if not self.functions:
            return None
        return round(sum(f.complexity for f in self.functions) / len(self.functions), 1)

    @property
    def avg_function_length(self) -> float | None:
        if not self.functions:
            return None
        return round(sum(f.length for f in self.functions) / len(self.functions), 1)

    @property
    def max_nesting_depth(self) -> int | None:
        return max((f.max_nesting for f in self.functions), default=None)

    def maintainability_index(self) -> int:
        if self.source_lines <= 0:
            return 100
        avg_cc = max(self.avg_complexity or 1.0, 1.0)
        volume = self.halstead_volume if self.halstead_volume > 1 else 1.0
        raw = (
            171
            - 5.2 * math.log(volume)
            - 0.23 * avg_cc
            - 16.2 * (self.source_lines / 1000)
        ) * 100.0 / 171.0
        return max(0, min(100, round(raw)))


@dataclass
class TextualLineMetrics:
    total: int
    source: int
    comments: int
    blank: int


def textual_line_metrics(code: str) -> TextualLineMetrics:
    lines = code.splitlines()
    total = len(lines)
    blank = 0
    comments = 0
    in_block = False
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            blank += 1
            continue
        if in_block:
            comments += 1
            if "*/" in stripped:
                in_block = False
            continue
        if stripped.startswith("//"):
            comments += 1
            continue
        if stripped.startswith("/*"):
            comments += 1
            if "*/" not in stripped[2:]:
                in_block = True
            continue
    return TextualLineMetrics(
        total=total,
        source=total - blank - comments,
        comments=comments,
        blank=blank,
    )


def cyclomatic_complexity(func: Node) -> int:
    score = 1
    for node in walk_own_scope(func):
        if node.type in BRANCH_NODES:
            score += 1
        elif node.type == "binary_expression":
            if text(node.child_by_field_name("operator")) in SHORT_CIRCUIT_OPERATORS:
                score += 1
    return score


def max_nesting_depth(func: Node) -> int:
    best = 0

    def visit(node: Node, depth: int) -> None:
        nonlocal best
        for child in node.children:
            if is_function_node(child):
                visit(child, depth)  # nested scope: measured separately
                continue
            child_depth = depth + (1 if child.type in NESTING_NODES else 0)
            best = max(best, child_depth)
            visit(child, child_depth)

    visit(func, 0)
    return best


def halstead_volume(root: Node) -> float:
    distinct_ops: set[str] = set()
    distinct_operands: set[str] = set()
    total_ops = 0
    total_operands = 0
    for node in walk(root):
        if node.child_count > 0:
            continue  # leaves only
        token = text(node)
        if not token:
            continue
        if node.type in OPERAND_NODES or node.type == "string":
            distinct_operands.add(token)
            total_operands += 1
        elif not node.type[0].isalpha() or node.type in {"=", "=>"}:
            distinct_ops.add(token)
            total_ops += 1
        else:
            distinct_ops.add(token)  # keywords act as operators
            total_ops += 1
    vocabulary = len(distinct_ops) + len(distinct_operands)
    length = total_ops + total_operands
    if vocabulary == 0 or length == 0:
        return 0.0
    return length * math.log2(vocabulary)


def function_name(node: Node) -> str:
    name = node.child_by_field_name("name")
    if name is not None:
        return text(name)
    # const handler = () => {} / foo: function () {}
    parent = node.parent
    if parent is not None:
        if parent.type == "variable_declarator":
            return text(parent.child_by_field_name("name"))
        if parent.type in {"pair", "public_field_definition", "field_definition"}:
            return text(parent.child_by_field_name("key") or parent.child_by_field_name("property"))
        if parent.type == "assignment_expression":
            left = parent.child_by_field_name("left")
            if left is not None:
                return text(left)
    return "(anonymous)"


def param_count(node: Node) -> int:
    params = node.child_by_field_name("parameters")
    if params is None:
        single = node.child_by_field_name("parameter")
        return 1 if single is not None else 0
    return len(
        [
            child
            for child in params.named_children
            if child.type not in {"comment", "type_annotation"}
        ]
    )


def _has_leading_doc_comment(node: Node) -> bool:
    """True when a /** ... */ or // comment sits directly above the function."""
    anchor = node
    while anchor.parent is not None and anchor.parent.type in {
        "variable_declarator",
        "lexical_declaration",
        "variable_declaration",
        "export_statement",
        "expression_statement",
    }:
        anchor = anchor.parent
    previous = anchor.prev_sibling
    if previous is None or previous.type != "comment":
        return False
    return previous.end_point[0] + 1 >= anchor.start_point[0]


def compute_module_metrics(tree: Tree, code: str) -> ModuleMetrics:
    lines = textual_line_metrics(code)
    root = tree.root_node
    functions: list[FunctionMetrics] = []
    class_count = 0
    import_count = 0

    for node in walk(root):
        if is_function_node(node):
            start = node.start_point[0] + 1
            end = node.end_point[0] + 1
            functions.append(
                FunctionMetrics(
                    name=function_name(node),
                    line=start,
                    length=end - start + 1,
                    complexity=cyclomatic_complexity(node),
                    max_nesting=max_nesting_depth(node),
                    has_docstring=_has_leading_doc_comment(node),
                    param_count=param_count(node),
                )
            )
        elif is_class_node(node):
            class_count += 1
        elif node.type in IMPORT_NODES:
            import_count += 1

    first = root.named_children[0] if root.named_children else None
    module_doc = first is not None and first.type == "comment"

    return ModuleMetrics(
        total_lines=lines.total,
        source_lines=lines.source,
        comment_lines=lines.comments,
        blank_lines=lines.blank,
        halstead_volume=halstead_volume(root),
        functions=functions,
        class_count=class_count,
        import_count=import_count,
        module_has_docstring=module_doc,
    )
