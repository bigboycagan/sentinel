"""Safe parsing of untrusted Python source.

`ast.parse` / `compile(..., "exec")`-free parsing only builds a syntax tree; it
does NOT execute the code. Deeply-nested or hostile inputs are handled: a
RecursionError / MemoryError / ValueError becomes a structured parse error, not
a 500 and never an execution.
"""

from __future__ import annotations

import ast


def parse_source(code: str) -> tuple[ast.Module | None, dict | None]:
    """Return (tree, None) on success or (None, {"message", "line", "column"}) on failure."""
    try:
        return ast.parse(code), None
    except SyntaxError as exc:
        return None, {
            "message": exc.msg or "invalid syntax",
            "line": int(exc.lineno or 1),
            "column": int(exc.offset or 1),
        }
    except (RecursionError, MemoryError, ValueError):
        # ValueError covers source with null bytes; RecursionError covers nesting bombs.
        return None, {
            "message": "The source could not be parsed (malformed or too deeply nested).",
            "line": 1,
            "column": 1,
        }
