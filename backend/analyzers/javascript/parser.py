"""Safe tree-sitter parsing of untrusted JavaScript / TypeScript source.

Grammars are selected per dialect: the TSX grammar is required for `.tsx`
(and is also the right choice for JSX-bearing TypeScript), while plain `.ts`
uses the TypeScript grammar and `.js`/`.jsx` the JavaScript grammar (which
already understands JSX).

tree-sitter recovers from syntax errors rather than raising, so a tree is
always produced; `first_error` finds the earliest ERROR/MISSING node so the
API can report a real syntax location instead of silently analyzing garbage.
"""

from __future__ import annotations

from functools import lru_cache

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser, Tree

JS = "javascript"
TS = "typescript"
TSX = "tsx"

_GRAMMARS = {
    JS: lambda: tree_sitter_javascript.language(),
    TS: lambda: tree_sitter_typescript.language_typescript(),
    TSX: lambda: tree_sitter_typescript.language_tsx(),
}

# Max bytes handed to the parser. The HTTP layer enforces the user-facing limit;
# this is a second, absolute backstop against pathological inputs.
MAX_PARSE_BYTES = 10_000_000


@lru_cache(maxsize=4)
def _parser(dialect: str) -> Parser:
    return Parser(Language(_GRAMMARS[dialect]()))


def dialect_for(file_name: str, language: str) -> str:
    """Pick the grammar for a file: .tsx/.jsx-in-TS need the TSX grammar."""
    lower = (file_name or "").lower()
    if language == TS:
        return TSX if lower.endswith(".tsx") else TS
    return JS


def first_error(root: Node) -> dict | None:
    """Earliest syntax error in the tree, as {message, line, column}."""
    if not root.has_error:
        return None
    best: Node | None = None
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "ERROR" or node.is_missing:
            if best is None or node.start_point[0] < best.start_point[0]:
                best = node
            continue  # no need to descend into an error subtree
        if node.has_error:
            stack.extend(node.children)
    if best is None:
        return None
    return {
        "message": "unexpected token" if best.type == "ERROR" else "missing syntax element",
        "line": best.start_point[0] + 1,
        "column": best.start_point[1] + 1,
    }


def parse_source(code: str, file_name: str, language: str) -> tuple[Tree | None, dict | None]:
    """Return (tree, None) on success or (None, {message, line, column}) on failure."""
    raw = code.encode("utf-8")
    if len(raw) > MAX_PARSE_BYTES:
        return None, {"message": "source is too large to parse", "line": 1, "column": 1}
    try:
        tree = _parser(dialect_for(file_name, language)).parse(raw)
    except (RecursionError, MemoryError, ValueError):
        return None, {
            "message": "The source could not be parsed (malformed or too deeply nested).",
            "line": 1,
            "column": 1,
        }
    error = first_error(tree.root_node)
    if error is not None:
        return None, error
    return tree, None
