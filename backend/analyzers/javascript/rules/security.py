"""JS-SEC* — JavaScript / TypeScript security rules (tree-sitter AST matching)."""

from __future__ import annotations

from analyzers.base import (
    CATEGORY_SECURITY,
    CRITICAL,
    HIGH,
    LOW,
    MEDIUM,
    Rule,
    RuleHit,
)
from analyzers.javascript.context import JsRuleContext
from analyzers.javascript.nodes import (
    CREDENTIAL_PREFIX,
    DECLARATION_NODES,
    SECURITY_RANDOM_NAME,
    assigned_name_nodes,
    call_args,
    callee,
    column,
    declaration_value,
    is_dynamic_string,
    is_placeholder,
    line,
    matches_credential,
    matches_secret,
    object_option,
    string_value,
    text,
    to_snake,
    walk,
)

LANG = "javascript"


def _credential_declarations(ctx: JsRuleContext, matcher, label: str):
    for node in walk(ctx.root):
        if node.type not in DECLARATION_NODES:
            continue
        value = declaration_value(node)
        literal = string_value(value)
        if literal is None or is_placeholder(literal):
            continue
        for name_node in assigned_name_nodes(node):
            name = text(name_node)
            if matcher(name):
                yield RuleHit(
                    line=line(node),
                    column=column(node),
                    message=f'{label} appears to be directly embedded in "{name}".',
                )
                break


def _check_hardcoded_password(ctx: JsRuleContext):
    yield from _credential_declarations(ctx, matches_credential, "A password")

    # password === "literal"
    for node in walk(ctx.root):
        if node.type != "binary_expression":
            continue
        if text(node.child_by_field_name("operator")) not in {"===", "==", "!==", "!="}:
            continue
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        for side, other in ((left, right), (right, left)):
            if side is None or other is None:
                continue
            if side.type not in {"identifier", "member_expression"}:
                continue
            name = text(side.child_by_field_name("property")) if side.type == "member_expression" else text(side)
            literal = string_value(other)
            if name and matches_credential(name) and literal and not is_placeholder(literal):
                yield RuleHit(
                    line=line(node),
                    column=column(node),
                    message=f'A password is compared against a hardcoded literal "{literal}".',
                )
                break


def _check_hardcoded_secret(ctx: JsRuleContext):
    yield from _credential_declarations(ctx, matches_secret, "A secret/API key")

    for node in walk(ctx.root):
        literal = string_value(node) if node.type in {"string", "template_string"} else None
        if literal and CREDENTIAL_PREFIX.search(literal.strip()):
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="A string literal matches a known service credential format "
                "(API key / OAuth token / JWT prefix).",
            )


def _check_eval(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        obj, prop = callee(node)
        if prop == "eval" and obj in {"", "window", "globalThis", "self"}:
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="eval() executes arbitrary JavaScript from a string at runtime.",
            )


def _check_implied_eval(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type == "new_expression":
            constructor = node.child_by_field_name("constructor")
            if constructor is not None and text(constructor) == "Function":
                yield RuleHit(
                    line=line(node),
                    column=column(node),
                    message="new Function(...) compiles a string into executable code, "
                    "exactly like eval().",
                )
            continue
        if node.type != "call_expression":
            continue
        _, prop = callee(node)
        if prop in {"setTimeout", "setInterval"}:
            args = call_args(node)
            if args and args[0].type in {"string", "template_string"}:
                yield RuleHit(
                    line=line(node),
                    column=column(node),
                    message=f"{prop}() is called with a string body, which is evaluated as "
                    "code (implied eval). Pass a function instead.",
                )


def _check_sql_injection(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        _, prop = callee(node)
        if prop not in {"query", "execute", "exec", "raw", "run", "all", "get"}:
            continue
        args = call_args(node)
        if not args or not is_dynamic_string(args[0]):
            continue
        snippet = text(args[0]).upper()
        if not any(
            keyword in snippet
            for keyword in ("SELECT", "INSERT", "UPDATE", "DELETE", "WHERE", "FROM", "DROP")
        ):
            continue
        yield RuleHit(
            line=line(node),
            column=column(node),
            message="A SQL statement appears to be built with string interpolation; "
            "use parameterized queries instead.",
        )


_COMMAND_CALLS = {"exec", "execSync", "spawn", "spawnSync", "execFile", "execFileSync"}


def _check_command_injection(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        obj, prop = callee(node)
        if prop not in _COMMAND_CALLS:
            continue
        args = call_args(node)
        if not args:
            continue
        dynamic = is_dynamic_string(args[0])
        shell_opt = any(object_option(arg, "shell") is not None for arg in args[1:])
        if dynamic:
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f"{(obj + '.') if obj else ''}{prop}() runs a command built by string "
                "interpolation; injected input becomes shell code.",
            )
        elif shell_opt and prop in {"spawn", "spawnSync"}:
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f"{prop}() is configured with a shell, so arguments pass through "
                "shell metacharacter expansion.",
                severity=MEDIUM,
            )


_HTML_SINKS = {"innerHTML", "outerHTML"}


def _check_xss_sink(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            if left is not None and left.type == "member_expression":
                prop = text(left.child_by_field_name("property"))
                if prop in _HTML_SINKS and string_value(node.child_by_field_name("right")) is None:
                    yield RuleHit(
                        line=line(node),
                        column=column(node),
                        message=f"Assigning dynamic content to {prop} injects raw HTML and is a "
                        "cross-site scripting sink.",
                    )
            continue
        if node.type != "call_expression":
            continue
        _, prop = callee(node)
        if prop == "insertAdjacentHTML":
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="insertAdjacentHTML() writes raw HTML into the document and is an "
                "XSS sink.",
            )
        elif prop == "write" and callee(node)[0] == "document":
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="document.write() injects raw markup and is an XSS sink.",
                severity=MEDIUM,
            )


def _check_dangerously_set_inner_html(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type not in {"jsx_attribute", "pair"}:
            continue
        key = node.child_by_field_name("key") or (
            node.children[0] if node.children else None
        )
        if key is None or text(key).strip("\"'") != "dangerouslySetInnerHTML":
            continue
        yield RuleHit(
            line=line(node),
            column=column(node),
            message="dangerouslySetInnerHTML bypasses React's escaping; unsanitized values "
            "become executable markup.",
        )


def _check_weak_hash(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        _, prop = callee(node)
        if prop not in {"createHash", "createHmac"}:
            continue
        args = call_args(node)
        if not args:
            continue
        algorithm = (string_value(args[0]) or "").strip().lower()
        if algorithm in {"md5", "sha1", "sha-1", "md4", "ripemd"}:
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f"'{algorithm}' is a broken/weak hash; use SHA-256 or better "
                "(and a salted KDF such as bcrypt/argon2 for passwords).",
            )


def _check_insecure_randomness(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type not in DECLARATION_NODES:
            continue
        value = declaration_value(node)
        if value is None:
            continue
        uses_math_random = any(
            candidate.type == "call_expression" and callee(candidate) == ("Math", "random")
            for candidate in walk(value)
        )
        if not uses_math_random:
            continue
        for name_node in assigned_name_nodes(node):
            name = text(name_node)
            if SECURITY_RANDOM_NAME.search(to_snake(name)):
                yield RuleHit(
                    line=line(node),
                    column=column(node),
                    message=f'"{name}" is generated with Math.random(), which is not '
                    "cryptographically secure. Use crypto.randomUUID() or "
                    "crypto.getRandomValues().",
                )
                break


def _check_tls_verification_disabled(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type == "pair":
            key = node.child_by_field_name("key")
            value = node.child_by_field_name("value")
            if key is not None and text(key).strip("\"'") == "rejectUnauthorized":
                if value is not None and text(value) == "false":
                    yield RuleHit(
                        line=line(node),
                        column=column(node),
                        message="rejectUnauthorized: false disables TLS certificate "
                        "verification, enabling man-in-the-middle attacks.",
                    )
            continue
        if node.type == "assignment_expression":
            left = node.child_by_field_name("left")
            if left is not None and "NODE_TLS_REJECT_UNAUTHORIZED" in text(left):
                yield RuleHit(
                    line=line(node),
                    column=column(node),
                    message="Setting NODE_TLS_REJECT_UNAUTHORIZED disables TLS verification "
                    "process-wide.",
                )


_FS_CALLS = {
    "readFile",
    "readFileSync",
    "writeFile",
    "writeFileSync",
    "appendFile",
    "appendFileSync",
    "unlink",
    "unlinkSync",
    "createReadStream",
    "createWriteStream",
    "sendFile",
    "rm",
    "rmSync",
}


def _check_path_traversal(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        _, prop = callee(node)
        if prop not in _FS_CALLS:
            continue
        args = call_args(node)
        if args and is_dynamic_string(args[0]):
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f"{prop}() receives a path built by string interpolation; validate and "
                "canonicalize it (path.resolve + prefix check) to prevent path traversal.",
            )


def _check_dynamic_require(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        obj, prop = callee(node)
        if prop not in {"require", "import"} or obj:
            continue
        args = call_args(node)
        if args and is_dynamic_string(args[0]):
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f"{prop}() is called with a dynamically built path, which can load "
                "and execute unintended modules.",
            )


def _check_vm_execution(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        _, prop = callee(node)
        if prop in {"runInNewContext", "runInThisContext", "runInContext", "compileFunction"}:
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f"vm.{prop}() executes arbitrary source at runtime; the vm module is "
                "not a security sandbox.",
            )


def _check_postmessage_wildcard(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        _, prop = callee(node)
        if prop != "postMessage":
            continue
        args = call_args(node)
        if len(args) >= 2 and string_value(args[1]) == "*":
            yield RuleHit(
                line=line(node),
                column=column(node),
                message='postMessage() with the "*" target origin leaks the message to any '
                "window that can receive it.",
            )


_STORAGE_OBJECTS = {"localStorage", "sessionStorage"}


def _check_sensitive_web_storage(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type != "call_expression":
            continue
        obj, prop = callee(node)
        if obj not in _STORAGE_OBJECTS or prop != "setItem":
            continue
        args = call_args(node)
        key = (string_value(args[0]) if args else None) or ""
        if matches_secret(key) or matches_credential(key):
            yield RuleHit(
                line=line(node),
                column=column(node),
                message=f'"{key}" is stored in {obj}, which is readable by any script on the '
                "page (XSS token theft). Prefer httpOnly cookies.",
            )


def _check_javascript_url(ctx: JsRuleContext):
    for node in walk(ctx.root):
        if node.type not in {"string", "template_string"}:
            continue
        literal = (string_value(node) or "").strip().lower()
        if literal.startswith("javascript:") or literal.startswith("data:text/html"):
            yield RuleHit(
                line=line(node),
                column=column(node),
                message="A javascript:/data:text/html URL executes code when navigated to or "
                "rendered.",
            )


SECURITY_RULES: list[Rule] = [
    Rule(
        rule_id="JS-SEC001",
        title="Hardcoded Password",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="A password-like variable or property is assigned (or compared against) "
        "a string literal directly in the source.",
        recommendation="Load credentials from environment variables or a secret manager, "
        "never from source literals.",
        check=_check_hardcoded_password,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC002",
        title="Dangerous eval()",
        category=CATEGORY_SECURITY,
        severity=CRITICAL,
        description="eval() compiles and runs arbitrary JavaScript from a string, so any "
        "injected input becomes executable code.",
        recommendation="Use JSON.parse for data, or an explicit parser/validator for the input.",
        check=_check_eval,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC003",
        title="Implied eval (Function / string timer)",
        category=CATEGORY_SECURITY,
        severity=CRITICAL,
        description="new Function(...) and setTimeout/setInterval with a string body compile "
        "strings into executable code, exactly like eval().",
        recommendation="Pass real function references and build logic explicitly.",
        check=_check_implied_eval,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC004",
        title="Hardcoded Secret / API Key",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="A secret-like name (apiKey, token, secret…) is assigned a string "
        "literal, or a literal matches a known service key/JWT format.",
        recommendation="Move secrets to environment variables or a secret manager and rotate "
        "anything that was committed.",
        check=_check_hardcoded_secret,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC005",
        title="SQL Injection Pattern",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="A SQL statement is assembled with template literals or concatenation, "
        "allowing input to alter the query.",
        recommendation="Use parameterized queries (placeholders + values array) or a query "
        "builder/ORM.",
        check=_check_sql_injection,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC006",
        title="Command Injection",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="child_process exec/spawn receives a command built from interpolated "
        "strings, or is given a shell, so input can inject commands.",
        recommendation="Use execFile/spawn with an argument array and no shell, and validate "
        "every dynamic argument.",
        check=_check_command_injection,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC007",
        title="XSS Sink (innerHTML / document.write)",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="Dynamic content is written into innerHTML/outerHTML, "
        "insertAdjacentHTML or document.write, which parses it as HTML.",
        recommendation="Use textContent, or sanitize with a vetted library before injecting "
        "markup.",
        check=_check_xss_sink,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC008",
        title="React dangerouslySetInnerHTML",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="dangerouslySetInnerHTML bypasses React's automatic escaping.",
        recommendation="Render text normally, or sanitize the HTML before passing it in.",
        check=_check_dangerously_set_inner_html,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC009",
        title="Weak Cryptographic Hash",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="crypto.createHash/createHmac is used with MD5, SHA-1 or another "
        "broken algorithm.",
        recommendation="Use SHA-256+ for hashing and bcrypt/argon2/PBKDF2 for passwords.",
        check=_check_weak_hash,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC010",
        title="Insecure Randomness",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="A security-sensitive value (token/salt/nonce/id/key) is generated with "
        "Math.random(), which is not cryptographically secure.",
        recommendation="Use crypto.randomUUID() or crypto.getRandomValues().",
        check=_check_insecure_randomness,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC011",
        title="TLS Verification Disabled",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="rejectUnauthorized: false or NODE_TLS_REJECT_UNAUTHORIZED turns off "
        "certificate validation.",
        recommendation="Keep verification on; supply a trusted CA bundle instead.",
        check=_check_tls_verification_disabled,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC012",
        title="Dynamic Path Construction",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="An fs/sendFile path is built with interpolation, so crafted input can "
        "escape the intended directory (path traversal).",
        recommendation="Resolve with path.resolve and verify the result stays inside the "
        "expected base directory.",
        check=_check_path_traversal,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC013",
        title="Dynamic Module Loading",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="require()/import() is called with a dynamically built path, which can "
        "load and execute unintended modules.",
        recommendation="Import from static paths, or map untrusted input through an explicit "
        "allow-list.",
        check=_check_dynamic_require,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC014",
        title="Runtime Code Execution via vm",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="The vm module executes arbitrary source at runtime and is explicitly "
        "not a security sandbox.",
        recommendation="Avoid executing supplied code; if unavoidable, isolate it in a "
        "separate process with dropped privileges.",
        check=_check_vm_execution,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC015",
        title="postMessage Wildcard Origin",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description='postMessage() is called with the "*" target origin, leaking the message '
        "to any receiving window.",
        recommendation="Pass the exact expected origin, and validate event.origin on receipt.",
        check=_check_postmessage_wildcard,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC016",
        title="Credentials in Web Storage",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="A token or password is written to localStorage/sessionStorage, which any "
        "script on the page can read.",
        recommendation="Keep session tokens in httpOnly cookies set by the server.",
        check=_check_sensitive_web_storage,
        language=LANG,
    ),
    Rule(
        rule_id="JS-SEC017",
        title="Executable URL Literal",
        category=CATEGORY_SECURITY,
        severity=LOW,
        description="A javascript: or data:text/html URL executes code when navigated to or "
        "rendered.",
        recommendation="Use normal http(s) URLs and attach behaviour with event listeners.",
        check=_check_javascript_url,
        language=LANG,
    ),
]
