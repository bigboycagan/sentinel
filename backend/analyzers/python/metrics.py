"""Deterministic source metrics for Python: lines, complexity, nesting, Halstead, MI.

Formulas (documented on purpose — SENTINEL never fakes a number):

* Line classes (textual, per line): blank (whitespace only), comment
  (stripped line starts with "#"), else source. Inline comments keep the line
  classified as source.
* Cyclomatic complexity per function: ``1 + branch points`` where branch points
  are: if/elif (each If), ternary IfExp, for/async for, while, except handler,
  assert, each comprehension ``for`` plus each of its ``if`` clauses,
  ``len(values) - 1`` for every and/or BoolOp, and one per ``match`` case.
  Nested functions/lambdas are measured as their own blocks and excluded from
  the enclosing function's score.
* Max nesting depth: deepest chain of if/for/while/try/with/match inside a
  function (nested scopes measured separately).
* Halstead volume (tokenize): ``V = (N1 + N2) * log2(n1 + n2)`` with operators
  (OP tokens) and operands (NAME/NUMBER/STRING/f-string tokens).
* Maintainability Index (radon-derived, clamped 0-100):
  ``MI = (171 - 5.2*ln(V) - 0.23*avg_cc - 16.2*SLOC/1000) * 100 / 171``.
"""

from __future__ import annotations

import ast
import io
import math
import tokenize
from dataclasses import dataclass, field

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
_NESTING_BASE = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
)
_MATCH = (ast.Match,) if hasattr(ast, "Match") else ()
_MATCH_CASE = (ast.match_case,) if hasattr(ast, "match_case") else ()
_NESTING_NODES = _NESTING_BASE + _MATCH
_FSTRING_TOKENS = tuple(
    getattr(tokenize, name)
    for name in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_STRING", "FSTRING_END")
    if hasattr(tokenize, name)
)


@dataclass
class FunctionMetrics:
    name: str
    line: int
    length: int
    complexity: int
    max_nesting: int
    has_docstring: bool


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
    blank = sum(1 for line in lines if not line.strip())
    comment_only = sum(1 for line in lines if line.strip().startswith("#"))
    return TextualLineMetrics(
        total=total,
        source=total - blank - comment_only,
        comments=comment_only,
        blank=blank,
    )


def _own_nodes(root: ast.AST):
    """Yield the nodes belonging to `root`'s own scope (no nested functions/lambdas)."""
    stack = [root]
    while stack:
        node = stack.pop()
        for child in ast.iter_child_nodes(node):
            yield child
            if not isinstance(child, _SCOPE_NODES):
                stack.append(child)


def cyclomatic_complexity(func: ast.AST) -> int:
    score = 1
    for node in _own_nodes(func):
        if isinstance(
            node,
            (
                ast.If,
                ast.IfExp,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.ExceptHandler,
                ast.Assert,
                *_MATCH_CASE,
            ),
        ):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)
    return score


def max_nesting_depth(func: ast.AST) -> int:
    best = 0

    def walk(node: ast.AST, depth: int) -> None:
        nonlocal best
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _SCOPE_NODES):
                walk(child, depth)  # nested scope: measured separately
                continue
            child_depth = depth + (1 if isinstance(child, _NESTING_NODES) else 0)
            best = max(best, child_depth)
            walk(child, child_depth)

    walk(func, 0)
    return best


def halstead_volume(code: str) -> float:
    distinct_ops: set[str] = set()
    distinct_operands: set[str] = set()
    total_ops = 0
    total_operands = 0
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.OP:
                distinct_ops.add(tok.string)
                total_ops += 1
            elif tok.type in (tokenize.NAME, tokenize.NUMBER, tokenize.STRING) or (
                _FSTRING_TOKENS and tok.type in _FSTRING_TOKENS
            ):
                distinct_operands.add(tok.string)
                total_operands += 1
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        pass  # partial token stream is fine; the metric stays deterministic
    vocab = len(distinct_ops) + len(distinct_operands)
    length = total_ops + total_operands
    if vocab == 0 or length == 0:
        return 0.0
    return length * math.log2(vocab)


def compute_module_metrics(tree: ast.Module, code: str) -> ModuleMetrics:
    lines = textual_line_metrics(code)
    functions: list[FunctionMetrics] = []
    class_count = 0
    import_count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.lineno
            functions.append(
                FunctionMetrics(
                    name=node.name,
                    line=node.lineno,
                    length=end - node.lineno + 1,
                    complexity=cyclomatic_complexity(node),
                    max_nesting=max_nesting_depth(node),
                    has_docstring=ast.get_docstring(node) is not None,
                )
            )
        elif isinstance(node, ast.ClassDef):
            class_count += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += 1
    return ModuleMetrics(
        total_lines=lines.total,
        source_lines=lines.source,
        comment_lines=lines.comments,
        blank_lines=lines.blank,
        halstead_volume=halstead_volume(code),
        functions=functions,
        class_count=class_count,
        import_count=import_count,
        module_has_docstring=ast.get_docstring(tree) is not None,
    )
