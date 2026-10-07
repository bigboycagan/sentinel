"""Shared AST helpers for the tree-sitter based JS/TS rules.

Keeping traversal and name-matching in one place stops every rule module from
re-implementing the same node plumbing.
"""

from __future__ import annotations

import re
from typing import Iterator

from tree_sitter import Node

# --- traversal ---------------------------------------------------------------

FUNCTION_NODES = frozenset(
    {
        "function_declaration",
        "function_expression",
        "function",
        "generator_function",
        "generator_function_declaration",
        "arrow_function",
        "method_definition",
    }
)

CLASS_NODES = frozenset({"class_declaration", "class"})


def is_function_node(node: Node) -> bool:
    """True for real function nodes only.

    The grammar also emits the bare `function` keyword as a node typed
    "function", so matching on type alone double-counts every declaration.
    Real functions are named nodes with children.
    """
    return node.type in FUNCTION_NODES and node.is_named and node.child_count > 0


def is_class_node(node: Node) -> bool:
    """True for real class nodes only (the `class` keyword is also a node)."""
    return node.type in CLASS_NODES and node.is_named and node.child_count > 0


def walk(node: Node) -> Iterator[Node]:
    """Every node in the subtree, pre-order."""
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.children))


def walk_own_scope(node: Node) -> Iterator[Node]:
    """Subtree nodes excluding nested function bodies (for per-function metrics)."""
    stack = list(reversed(node.children))
    while stack:
        current = stack.pop()
        yield current
        if not is_function_node(current):
            stack.extend(reversed(current.children))


def text(node: Node | None) -> str:
    return "" if node is None else node.text.decode("utf-8", "replace")


def line(node: Node) -> int:
    return node.start_point[0] + 1


def column(node: Node) -> int:
    return node.start_point[1] + 1


# --- call / member helpers ---------------------------------------------------


def callee(call: Node) -> tuple[str, str]:
    """(object, property) for a call. `foo()` → ("", "foo"); `a.b()` → ("a", "b")."""
    func = call.child_by_field_name("function")
    if func is None:
        return "", ""
    if func.type == "identifier":
        return "", text(func)
    if func.type == "member_expression":
        return text(func.child_by_field_name("object")), text(
            func.child_by_field_name("property")
        )
    return "", text(func)


def call_args(call: Node) -> list[Node]:
    args = call.child_by_field_name("arguments")
    if args is None:
        return []
    return [child for child in args.named_children if child.type != "comment"]


def object_option(node: Node, key: str) -> Node | None:
    """Value of `key` in an object literal argument, e.g. {rejectUnauthorized: false}."""
    for candidate in walk(node):
        if candidate.type != "pair":
            continue
        name = candidate.child_by_field_name("key")
        if name is not None and text(name).strip("\"'`") == key:
            return candidate.child_by_field_name("value")
    return None


def is_string_literal(node: Node | None) -> bool:
    if node is None:
        return False
    if node.type == "string":
        return True
    return node.type == "template_string" and not any(
        child.type == "template_substitution" for child in node.children
    )


def string_value(node: Node | None) -> str | None:
    """The literal text of a static string, or None if it is not one."""
    if not is_string_literal(node):
        return None
    raw = text(node)
    if len(raw) >= 2 and raw[0] in "\"'`" and raw[-1] == raw[0]:
        return raw[1:-1]
    return raw


def is_dynamic_string(node: Node | None) -> bool:
    """True when a string value is assembled at runtime (template subs or `+`)."""
    if node is None:
        return False
    if node.type == "template_string":
        return any(child.type == "template_substitution" for child in node.children)
    if node.type == "binary_expression":
        operator = text(node.child_by_field_name("operator"))
        if operator != "+":
            return False
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        # Concatenation counts only when a string is being built up.
        return any(
            part is not None and (is_string_literal(part) or is_dynamic_string(part))
            for part in (left, right)
        ) or any(part is not None and part.type == "identifier" for part in (left, right))
    if node.type == "call_expression":
        _, prop = callee(node)
        if prop in {"concat", "join", "format"}:
            return True
    return False


# --- naming ------------------------------------------------------------------

_CAMEL_1 = re.compile(r"(.)([A-Z][a-z]+)")
_CAMEL_2 = re.compile(r"([a-z0-9])([A-Z])")


def to_snake(name: str) -> str:
    """apiKey → api_key, so one regex can match both JS and Python naming styles."""
    stepped = _CAMEL_1.sub(r"\1_\2", name)
    return _CAMEL_2.sub(r"\1_\2", stepped).replace("-", "_").lower()


CREDENTIAL_NAME = re.compile(r"(?:^|_)(?:password|passwd|pwd|passphrase)(?:$|_)")
SECRET_NAME = re.compile(
    r"(?:^|_)(?:secret|token|api_?key|apikey|auth_?key|access_?key|private_?key|"
    r"client_?secret|secret_?key|access_?token|auth_?token|session_?key|signing_?key|"
    r"encryption_?key|jwt_?secret)(?:$|_)"
)
SECURITY_RANDOM_NAME = re.compile(
    r"(?:^|_)(?:token|nonce|salt|otp|csrf|session|secret|password|passwd|pwd|api_?key|"
    r"id|uuid|key)(?:$|_)"
)
CREDENTIAL_PREFIX = re.compile(
    r"^(?:sk-[A-Za-z0-9_-]{16,}|sk-(?:live|test)-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|"
    r"gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{12,}|ASIA[0-9A-Z]{12,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,}|glpat-[A-Za-z0-9_-]{15,}|"
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"
)

PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "...",
        "xxx",
        "changeme",
        "change_me",
        "change-me",
        "placeholder",
        "example",
        "sample",
        "dummy",
        "test",
        "todo",
        "fixme",
        "redacted",
        "n/a",
        "na",
        "none",
        "null",
        "true",
        "false",
        "password",
        "passwd",
        "secret",
        "token",
        "your-password",
        "your_password",
        "my-password",
        "123456",
        "12345678",
    }
)

_ENV_LOOKALIKE = re.compile(r"^(?:\$\{?\w+\}?|%|process\.env|import\.meta)")


def is_placeholder(value: str) -> bool:
    candidate = value.strip()
    return (
        len(candidate) < 3
        or candidate.lower() in PLACEHOLDER_VALUES
        or bool(_ENV_LOOKALIKE.match(candidate))
    )


def matches_credential(name: str) -> bool:
    return bool(CREDENTIAL_NAME.search(to_snake(name)))


def matches_secret(name: str) -> bool:
    return bool(SECRET_NAME.search(to_snake(name)))


# --- declaration helpers -----------------------------------------------------


def assigned_name_nodes(node: Node) -> list[Node]:
    """Identifier/property nodes a declaration or assignment writes to."""
    out: list[Node] = []
    if node.type == "variable_declarator":
        name = node.child_by_field_name("name")
        if name is not None:
            out.append(name)
    elif node.type == "assignment_expression":
        left = node.child_by_field_name("left")
        if left is None:
            pass
        elif left.type == "identifier":
            out.append(left)
        elif left.type == "member_expression":
            prop = left.child_by_field_name("property")
            if prop is not None:
                out.append(prop)
    elif node.type in {"pair", "public_field_definition", "field_definition"}:
        key = node.child_by_field_name("key") or node.child_by_field_name("property")
        if key is not None:
            out.append(key)
    return out


def declaration_value(node: Node) -> Node | None:
    if node.type in {"variable_declarator", "public_field_definition", "field_definition"}:
        return node.child_by_field_name("value")
    if node.type == "assignment_expression":
        return node.child_by_field_name("right")
    if node.type == "pair":
        return node.child_by_field_name("value")
    return None


DECLARATION_NODES = frozenset(
    {
        "variable_declarator",
        "assignment_expression",
        "pair",
        "public_field_definition",
        "field_definition",
    }
)
