"""JS-QUA* / TS-QUA* — code quality rules for JavaScript and TypeScript."""

from __future__ import annotations

import re

from analyzers.base import CATEGORY_QUALITY, INFO, LOW, MEDIUM, Rule, RuleHit
from analyzers.javascript.context import JsRuleContext
from analyzers.javascript.nodes import (
    FUNCTION_NODES,
    callee,
    column,
    line,
    text,
    walk,
)

LANG = "javascript"
TS_LANG = "typescript"

MAX_NESTING = 4
MAX_FUNCTION_LINES = 50
MAX_FILE_SLOC = 500
MAX_TODO_FINDINGS = 10

_GENERIC_NAME = re.compile(
    r"(?i)^(?:func|fn|function|foo|bar|baz|temp|tmp|var|obj|object|thing|data|test\d*)\d*$"
)
_TODO_MARKER = re.compile(r"(?i)(?://|/\*|\*)\s*(TODO|FIXME|HACK|XXX)\b")
_TS_SUPPRESSION = re.compile(r"@ts-(ignore|nocheck|expect-error)")

_REFERENCE_NODES = frozenset(
    {"identifier", "shorthand_property_identifier", "shorthand_property_identifier_pattern"}
)

_TERMINALS = frozenset({"return_statement", "throw_statement", "break_statement", "continue_statement"})

_STATEMENT_PARENTS = frozenset({"statement_block", "program", "switch_case", "switch_default"})


def _reference_counts(ctx: JsRuleContext) -> dict[str, int]:
    """How often each bare identifier name appears anywhere in the file.

    A declaration contributes one occurrence, so a name seen exactly once is
    never read. This is intentionally conservative: shadowing in a nested
    scope inflates the count and simply suppresses the finding.
    """
    counts: dict[str, int] = {}
    for node in walk(ctx.root):
        if node.type in _REFERENCE_NODES:
            name = text(node)
            counts[name] = counts.get(name, 0) + 1
    return counts


def _is_exported(node) -> bool:
    """True only when the declaration itself is exported.

    The chain must be declarator → (lexical|variable)_declaration →
    export_statement. Walking further would treat every local inside an
    exported function as exported, suppressing real findings.
    """
    declaration = node.parent
    if declaration is None or declaration.type not in {
        "lexical_declaration",
        "variable_declaration",
    }:
        return False
    return declaration.parent is not None and declaration.parent.type == "export_statement"


def _check_unused_variables(ctx: JsRuleContext):
    counts = _reference_counts(ctx)
    for node in walk(ctx.root):
        if node.type != "variable_declarator":
            continue
        name_node = node.child_by_field_name("name")
        if name_node is None or name_node.type != "identifier":
            continue  # destructuring patterns are not tracked
        name = text(name_node)
        if name.startswith("_") or _is_exported(node):
            continue
        # A function assigned to a const is reported by its own rules, not here.
        value = node.child_by_field_name("value")
        if value is not None and value.type in FUNCTION_NODES:
            continue
        if counts.get(name, 0) <= 1:
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f'Variable "{name}" is declared but never used.',
            )


def _check_unused_imports(ctx: JsRuleContext):
    counts = _reference_counts(ctx)
    for node in walk(ctx.root):
        if node.type != "import_statement":
            continue
        for candidate in walk(node):
            if candidate.type == "import_specifier":
                alias = candidate.child_by_field_name("alias")
                name_node = alias or candidate.child_by_field_name("name")
                bound = text(name_node)
                # The imported name itself also counts as an occurrence.
                threshold = 2 if alias is None else 1
                if bound and counts.get(bound, 0) <= threshold:
                    yield RuleHit(
                        line=line(node),
                        column=column(node),
                        message=f'Import "{bound}" is never used in this file.',
                    )
            elif candidate.type == "namespace_import":
                for child in candidate.children:
                    if child.type == "identifier" and counts.get(text(child), 0) <= 1:
                        yield RuleHit(
                            line=line(node),
                            column=column(node),
                            message=f'Import "{text(child)}" is never used in this file.',
                        )
            elif (
                candidate.type == "identifier"
                and candidate.parent is not None
                and candidate.parent.type == "import_clause"
            ):
                if counts.get(text(candidate), 0) <= 1:
                    yield RuleHit(
                        line=line(node),
                        column=column(node),
                        message=f'Default import "{text(candidate)}" is never used in this file.',
                    )


def _check_unreachable_code(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type not in _STATEMENT_PARENTS:
            continue
        statements = [child for child in node.named_children if child.type != "comment"]
        for previous, current in zip(statements, statements[1:]):
            if previous.type in _TERMINALS:
                yield RuleHit(
                    line=line(current),
                    column=column(current),
                    message="This code is unreachable: it follows a return/throw/break/"
                    "continue in the same block.",
                )
                break


def _check_excessive_nesting(ctx: JsRuleContext):
    for fm in ctx.metrics.functions:
        if fm.max_nesting > MAX_NESTING:
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function "{fm.name}" nests {fm.max_nesting} levels deep '
                f"(threshold: {MAX_NESTING}); extract the inner blocks.",
            )


def _check_function_too_long(ctx: JsRuleContext):
    for fm in ctx.metrics.functions:
        if fm.length > MAX_FUNCTION_LINES:
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function "{fm.name}" is {fm.length} lines long '
                f"(threshold: {MAX_FUNCTION_LINES}).",
            )


def _check_file_too_long(ctx: JsRuleContext):
    if ctx.metrics.source_lines > MAX_FILE_SLOC:
        yield RuleHit(
            line=1,
            column=1,
            message=f"The file has {ctx.metrics.source_lines} source lines "
            f"(threshold: {MAX_FILE_SLOC}); consider splitting it into modules.",
        )


def _check_poor_naming(ctx: JsRuleContext):
    for fm in ctx.metrics.functions:
        name = fm.name
        if name in {"(anonymous)", "constructor"} or name.startswith("_"):
            continue
        bare = name.split(".")[-1]
        if _GENERIC_NAME.match(bare) or len(bare.replace("_", "")) <= 2:
            yield RuleHit(
                line=fm.line,
                column=1,
                message=f'Function name "{name}" is too short or generic; use a descriptive name.',
            )


def _check_empty_catch(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "catch_clause":
            continue
        body = node.child_by_field_name("body")
        if body is None:
            continue
        statements = [child for child in body.named_children if child.type != "comment"]
        if not statements:
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="This catch block is empty, so the error is silently swallowed.",
            )


def _check_loose_equality(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "binary_expression":
            continue
        operator = text(node.child_by_field_name("operator"))
        if operator not in {"==", "!="}:
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        # `x == null` is an idiomatic null+undefined check; don't flag it.
        if any(part is not None and text(part) == "null" for part in (left, right)):
            continue
        yield RuleHit(
            line=line(node),
            column=column(node),
            message=f'"{operator}" performs type coercion; use '
            f'"{"===" if operator == "==" else "!=="}" instead.',
        )


def _check_var_declaration(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type == "variable_declaration":  # `var`; let/const are lexical_declaration
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="`var` is function-scoped and hoisted; prefer `const` or `let`.",
            )


def _check_console_statement(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        obj, _ = callee(node)
        if obj == "console":
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="A console statement is left in the source.",
                severity=INFO,
            )


def _check_debugger_statement(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type == "debugger_statement":
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="A `debugger` statement halts execution in any browser with devtools "
                "open; it must not ship.",
            )


def _check_todo_comments(ctx: JsRuleContext):
    emitted = 0
    for index, raw in enumerate(ctx.lines, start=1):
        match = _TODO_MARKER.search(raw)
        if match and emitted < MAX_TODO_FINDINGS:
            emitted += 1
            yield RuleHit(
                line=index,
                column=1,
                message=f"Unresolved {match.group(1).upper()} marker left in a comment.",
                severity=INFO,
            )


def _check_explicit_any(ctx: JsRuleContext):
    if not ctx.is_typescript:
        return
    for node in walk(ctx.root):
        if node.type == "predefined_type" and text(node) == "any":
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="An explicit `any` disables type checking for this value.",
            )


def _check_ts_suppression(ctx: JsRuleContext):
    if not ctx.is_typescript:
        return
    for index, raw in enumerate(ctx.lines, start=1):
        match = _TS_SUPPRESSION.search(raw)
        if match:
            yield RuleHit(
                line=index,
                column=1,
                message=f"@ts-{match.group(1)} suppresses a real type error instead of "
                "fixing it.",
            )


QUALITY_RULES: list[Rule] = [
    Rule(
        rule_id="JS-QUA001",
        title="Unused Variable",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="A variable is declared but never read anywhere in the file.",
        recommendation="Remove the declaration, or prefix an intentional throwaway with "
        "an underscore.",
        check=_check_unused_variables,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA002",
        title="Unused Import",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="The module imports a binding that is never used.",
        recommendation="Remove the import to keep the dependency graph honest.",
        check=_check_unused_imports,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA003",
        title="Unreachable Code",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="Statements follow a return/throw/break/continue in the same block and "
        "can never execute.",
        recommendation="Delete the dead statements or restructure the control flow.",
        check=_check_unreachable_code,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA004",
        title="Excessive Nesting",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="A function nests conditionals/loops more than 4 levels deep.",
        recommendation="Extract inner blocks into helpers and use early returns.",
        check=_check_excessive_nesting,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA005",
        title="Function Too Long",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="A function exceeds 50 lines, usually meaning it does more than one thing.",
        recommendation="Split it into focused helpers with clear responsibilities.",
        check=_check_function_too_long,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA006",
        title="File Too Long",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="The file exceeds 500 source lines, complicating review and merging.",
        recommendation="Split the module along its natural responsibilities.",
        check=_check_file_too_long,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA007",
        title="Poor Naming",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="A function name is a single letter or a generic placeholder "
        "(foo, tmp, data…).",
        recommendation="Name functions after what they do.",
        check=_check_poor_naming,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA008",
        title="Empty Catch Block",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="A catch block has no body, so the error is silently swallowed.",
        recommendation="Handle, log or rethrow the error.",
        check=_check_empty_catch,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA009",
        title="Loose Equality",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="== / != coerce types before comparing, a classic source of JavaScript "
        "bugs. `x == null` is excluded as an idiomatic nullish check.",
        recommendation="Use === / !== .",
        check=_check_loose_equality,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA010",
        title="var Declaration",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="`var` is function-scoped and hoisted, which leaks bindings out of blocks.",
        recommendation="Use `const` by default and `let` when reassignment is required.",
        check=_check_var_declaration,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA011",
        title="Leftover console Statement",
        category=CATEGORY_QUALITY,
        severity=INFO,
        description="A console call remains in the source.",
        recommendation="Remove it or route it through a real logger.",
        check=_check_console_statement,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA012",
        title="debugger Statement",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="A `debugger` statement pauses execution wherever devtools are open.",
        recommendation="Remove it before committing.",
        check=_check_debugger_statement,
        language=LANG,
    ),
    Rule(
        rule_id="JS-QUA013",
        title="Unresolved TODO Marker",
        category=CATEGORY_QUALITY,
        severity=INFO,
        description="A comment contains TODO/FIXME/HACK/XXX — an acknowledged gap.",
        recommendation="Resolve it or track it in an issue instead of the source.",
        check=_check_todo_comments,
        language=LANG,
    ),
    Rule(
        rule_id="TS-QUA001",
        title="Explicit any Type",
        category=CATEGORY_QUALITY,
        severity=LOW,
        description="An explicit `any` opts the value out of type checking, losing the "
        "guarantees TypeScript exists to provide.",
        recommendation="Use a precise type, a generic, or `unknown` plus narrowing.",
        check=_check_explicit_any,
        language=TS_LANG,
    ),
    Rule(
        rule_id="TS-QUA002",
        title="Suppressed Type Error",
        category=CATEGORY_QUALITY,
        severity=MEDIUM,
        description="@ts-ignore / @ts-nocheck / @ts-expect-error hides a real type error "
        "from the compiler.",
        recommendation="Fix the underlying type problem; if truly unavoidable, narrow the "
        "suppression and document why.",
        check=_check_ts_suppression,
        language=TS_LANG,
    ),
]
