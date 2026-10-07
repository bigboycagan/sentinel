"""QUA* — code quality rules (unused code, structure, lint classics)."""

from __future__ import annotations

import ast
import re

from analyzers.base import (
    CATEGORY_QUALITY,
    INFO,
    LOW,
    MEDIUM,
    Rule,
    RuleHit,
)
from analyzers.python.context import RuleContext

MAX_NESTING = 4
MAX_FUNCTION_LINES = 50
MAX_FILE_SLOC = 500
MAX_TODO_FINDINGS = 10

_GENERIC_NAME = re.compile(r"(?i)^(?:func|fn|function|method|foo|bar|baz|temp|tmp|var|obj|object|thing|data)\d*$")
_TODO_MARKER = re.compile(r"(?i)#\s*(TODO|FIXME|HACK|XXX)\b")

_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
_TERMINALS = (ast.Return, ast.Raise, ast.Break, ast.Continue)


def _bound_names(target: ast.AST, out: list[tuple[str, ast.Name]]) -> None:
    if isinstance(target, ast.Name):
        out.append((target.id, target))
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            _bound_names(element, out)
    elif isinstance(target, ast.Starred):
        _bound_names(target.value, out)
    # Attribute stores (self.x = ...) are attributes, not locals — skipped.


def _function_scopes(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _check_unused_variables(ctx: RuleContext):
    for func in _function_scopes(ctx.tree):
        stores: list[tuple[str, ast.Name]] = []
        loads: set[str] = set()

        # AugAssign targets are both a load and a store — count them as uses.
        for node in ast.walk(func):
            if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
                loads.add(node.target.id)

        def visit(node: ast.AST) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, _SCOPE_NODES):
                    # Nested scope: its loads may read our locals; its stores are its own.
                    for nested in ast.walk(child):
                        if isinstance(nested, ast.Name) and not isinstance(nested.ctx, ast.Store):
                            loads.add(nested.id)
                    continue
                if isinstance(child, ast.Name):
                    if isinstance(child.ctx, ast.Store):
                        stores.append((child.id, child))
                    else:
                        loads.add(child.id)
                elif isinstance(child, (ast.Global, ast.Nonlocal)):
                    loads.update(child.names)
                elif isinstance(child, ast.ExceptHandler) and child.name:
                    loads.add(child.name)
                visit(child)

        visit(func)
        for name, node in stores:
            if name.startswith("_") or name in loads:
                continue
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message=f'Local variable "{name}" is assigned but never used.',
            )


def _all_string_literals(tree: ast.Module) -> set[str]:
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _check_unused_imports(ctx: RuleContext):
    used = {
        node.id
        for node in ast.walk(ctx.tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Load, ast.Del))
    }
    # Names re-exported via __all__ count as used.
    for node in ast.walk(ctx.tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
        ):
            used.update(name for name in _all_string_literals(node) if isinstance(name, str))

    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                if local not in used:
                    yield RuleHit(
                        line=node.lineno,
                        column=node.col_offset + 1,
                        message=f'Import "{alias.name}" is never used in this file.',
                    )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue  # covered by QUA010
                local = alias.asname or alias.name
                if local not in used:
                    yield RuleHit(
                        line=node.lineno,
                        column=node.col_offset + 1,
                        message=f'Import "{alias.name}" is never used in this file.',
                    )


def _check_unreachable_code(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        stmt_lists = []
        body = getattr(node, "body", None)
        if isinstance(body, list):
            stmt_lists.append(body)
        orelse = getattr(node, "orelse", None)
        if isinstance(orelse, list):
            stmt_lists.append(orelse)
        finalbody = getattr(node, "finalbody", None)
        if isinstance(finalbody, list):
            stmt_lists.append(finalbody)
        for stmts in stmt_lists:
            if not stmts or not all(isinstance(s, ast.stmt) for s in stmts):
                continue
            for prev, stmt in zip(stmts, stmts[1:]):
                if isinstance(prev, _TERMINALS):
                    yield RuleHit(
                        line=stmt.lineno,
                        column=stmt.col_offset + 1,
                        message="This code is unreachable: it follows a return/raise/"
                        "break/continue in the same block.",
                    )
                    break


def _check_excessive_nesting(ctx: RuleContext):
    for fm in ctx.metrics.functions:
        if fm.max_nesting > MAX_NESTING:
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function "{fm.name}" nests {fm.max_nesting} levels deep '
                f"(threshold: {MAX_NESTING}); extract the inner blocks.",
            )


def _check_function_too_long(ctx: RuleContext):
    for fm in ctx.metrics.functions:
        if fm.length > MAX_FUNCTION_LINES:
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function "{fm.name}" is {fm.length} lines long '
                f"(threshold: {MAX_FUNCTION_LINES}).",
            )


def _check_file_too_long(ctx: RuleContext):
    if ctx.metrics.source_lines > MAX_FILE_SLOC:
        yield RuleHit(
            line=1,
            column=1,
            message=f"The file has {ctx.metrics.source_lines} source lines "
            f"(threshold: {MAX_FILE_SLOC}); consider splitting it into modules.",
        )


def _check_poor_naming(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        name = node.name
        if name.startswith("__") and name.endswith("__"):
            continue  # dunders are language-defined
        kind = "Class" if isinstance(node, ast.ClassDef) else "Function"
        if _GENERIC_NAME.match(name) or len(name.replace("_", "")) <= 2:
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message=f'{kind} name "{name}" is too short or generic; use a descriptive name.',
            )


def _check_bare_except(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="Bare except also catches SystemExit and KeyboardInterrupt; "
                "catch the specific exception (or at least Exception).",
            )


def _check_mutable_default(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        defaults = list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]
        for default in defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                yield RuleHit(
                    line=default.lineno,
                    column=default.col_offset + 1,
                    message="Mutable default argument: the same list/dict/set is shared "
                    "across every call of this function.",
                )
            elif (
                isinstance(default, ast.Call)
                and isinstance(default.func, ast.Name)
                and default.func.id in {"list", "dict", "set"}
            ):
                yield RuleHit(
                    line=default.lineno,
                    column=default.col_offset + 1,
                    message=f'Mutable default argument: {default.func.id}() is evaluated once, '
                    "at definition time.",
                )


def _check_wildcard_import(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message=f'Wildcard import from "{node.module}": pollutes the namespace and '
                "hides what the code actually depends on.",
            )


def _check_todo_comments(ctx: RuleContext):
    emitted = 0
    for index, line in enumerate(ctx.lines, start=1):
        match = _TODO_MARKER.search(line)
        if match and emitted < MAX_TODO_FINDINGS:
            emitted += 1
            yield RuleHit(
                line=index,
                column=1,
                message=f"Unresolved {match.group(1).upper()} marker left in a comment.",
                severity=INFO,
            )


QUALITY_RULES: list[Rule] = [
    Rule(
        rule_id="QUA001",
        title="Unused Variable",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="A local variable is assigned but never read anywhere in its scope.",
        recommendation="Remove the assignment or use the value; prefix intentional "
        "throwaways with an underscore.",
        check=_check_unused_variables,
    ),
    Rule(
        rule_id="QUA002",
        title="Unused Import",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="The module imports a name that is never used in the file.",
        recommendation="Remove the import (or move it into the branch that needs it).",
        check=_check_unused_imports,
    ),
    Rule(
        rule_id="QUA003",
        title="Unreachable Code",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="Statements appear after a return/raise/break/continue in the same "
        "block and can never execute.",
        recommendation="Delete the dead statements or restructure the control flow.",
        check=_check_unreachable_code,
    ),
    Rule(
        rule_id="QUA004",
        title="Excessive Nesting",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="A function nests conditionals/loops more than 4 levels deep, which is "
        "hard to read and test.",
        recommendation="Extract inner blocks into helpers and use early returns to flatten "
        "the flow.",
        check=_check_excessive_nesting,
    ),
    Rule(
        rule_id="QUA005",
        title="Function Too Long",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="A function exceeds 50 lines, usually meaning it does more than one thing.",
        recommendation="Split it into focused helper functions with clear responsibilities.",
        check=_check_function_too_long,
    ),
    Rule(
        rule_id="QUA006",
        title="File Too Long",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="The file exceeds 500 source lines, which complicates review and merging.",
        recommendation="Split the module along its natural responsibilities.",
        check=_check_file_too_long,
    ),
    Rule(
        rule_id="QUA007",
        title="Poor Naming",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="A function/class name is a single letter or a generic placeholder "
        "(foo, tmp, var1...).",
        recommendation="Name things after what they do or contain.",
        check=_check_poor_naming,
    ),
    Rule(
        rule_id="QUA008",
        title="Bare Except",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="except: without an exception type swallows everything, including "
        "SystemExit and KeyboardInterrupt.",
        recommendation="Catch the narrowest exception you can handle.",
        check=_check_bare_except,
    ),
    Rule(
        rule_id="QUA009",
        title="Mutable Default Argument",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="A list/dict/set default argument is evaluated once at definition time "
        "and shared across all calls — a classic Python bug.",
        recommendation="Default to None and create the mutable value inside the function.",
        check=_check_mutable_default,
    ),
    Rule(
        rule_id="QUA010",
        title="Wildcard Import",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="from module import * hides dependencies and can shadow names.",
        recommendation="Import the specific names you use.",
        check=_check_wildcard_import,
    ),
    Rule(
        rule_id="QUA011",
        title="Unresolved TODO Marker",
        category=CATEGORY_QUALITY,
        severity=INFO,
        description="A comment contains TODO/FIXME/HACK/XXX — an acknowledged gap in the code.",
        recommendation="Resolve the marker or track it in an issue instead of the source.",
        check=_check_todo_comments,
    ),
]
