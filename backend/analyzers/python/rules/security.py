"""SEC* — security rules. Every check is deterministic pattern/AST matching."""

from __future__ import annotations

import ast
import re

from analyzers.base import (
    CATEGORY_SECURITY,
    CRITICAL,
    HIGH,
    LOW,
    MEDIUM,
    Rule,
    RuleHit,
)
from analyzers.python.context import RuleContext

# --- shared helpers ---------------------------------------------------------

CREDENTIAL_NAME = re.compile(r"(?i)(?:^|_)(?:password|passwd|pwd|passphrase)(?:$|_)")
SECRET_NAME = re.compile(
    r"(?i)(?:^|_)(?:secret|token|api_?key|apikey|auth_?key|access_?key|private_?key|"
    r"client_?secret|secret_?key|access_?token|auth_?token|session_?key|signing_?key|"
    r"encryption_?key)(?:$|_)"
)
SECURITY_RANDOM_NAME = re.compile(
    r"(?i)token|nonce|salt|otp|csrf|session|secret|password|passwd|pwd|api_?key"
)
ENV_LOOKALIKE = re.compile(r"^(?:\$\{?\w+\}?|%|\{\{|os\.environ)")
CREDENTIAL_PREFIX = re.compile(
    r"^(?:sk-[A-Za-z0-9_-]{16,}|sk-(?:live|test)-[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{20,}|"
    r"gho_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{12,}|ASIA[0-9A-Z]{12,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{20,}|glpat-[A-Za-z0-9_-]{15,}|"
    r"sq0atp-[A-Za-z0-9_-]{20,})"
)
PLACEHOLDER_VALUES = {
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
    "your-password-here",
    "my-password",
    "123456",
    "12345678",
}


def _const_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _is_placeholder(value: str) -> bool:
    v = value.strip()
    if len(v) < 3 or v.lower() in PLACEHOLDER_VALUES or ENV_LOOKALIKE.match(v):
        return True
    return False


def _assigned_names(targets: list[ast.AST]) -> list[str]:
    names: list[str] = []
    for target in targets:
        for node in ast.walk(target):
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
    return names


def _check_hardcoded_password(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        s = _const_str(value)
        if s is None or _is_placeholder(s):
            continue
        for name in _assigned_names(targets):
            if CREDENTIAL_NAME.search(name):
                yield RuleHit(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    message=f'A password appears to be directly embedded in "{name}".',
                )
                break

    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Compare):
            continue
        sides = [node.left, *node.comparators]
        for side in sides:
            if isinstance(side, ast.Name) and CREDENTIAL_NAME.search(side.id):
                for other in sides:
                    s = _const_str(other)
                    if other is not side and s is not None and not _is_placeholder(s):
                        yield RuleHit(
                            line=node.lineno,
                            column=node.col_offset + 1,
                            message=f'A password is compared against a hardcoded literal "{s}".',
                        )
                        break

    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg and CREDENTIAL_NAME.search(kw.arg):
                s = _const_str(kw.value)
                if s is not None and not _is_placeholder(s):
                    yield RuleHit(
                        line=node.lineno,
                        column=node.col_offset + 1,
                        message=f'A password appears to be directly embedded in keyword "{kw.arg}".',
                    )


def _check_hardcoded_secret(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Assign):
            targets, value = list(node.targets), node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        else:
            continue
        s = _const_str(value)
        if s is None or _is_placeholder(s):
            continue
        for name in _assigned_names(targets):
            if SECRET_NAME.search(name):
                yield RuleHit(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    message=f'A secret/API key appears to be directly embedded in "{name}".',
                )
                break

    for node in ast.walk(ctx.tree):
        s = _const_str(node)
        if s and CREDENTIAL_PREFIX.search(s.strip()):
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="A string literal matches a known service credential format "
                "(API key / OAuth token prefix).",
            )


def _check_dangerous_eval(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="eval() executes arbitrary Python source from a string at runtime.",
            )


def _check_dangerous_exec(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "exec":
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="exec() executes arbitrary Python source from a string at runtime.",
            )


_DESERIALIZE_ROOTS = {"pickle", "cpickle", "dill"}


def _root_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _check_unsafe_deserialization(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        func = node.func
        root = _root_name(func.value)
        attr = func.attr
        if root and root.lower() in _DESERIALIZE_ROOTS and attr in {"load", "loads"}:
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message=f"{root}.{attr}() deserializes untrusted data and can execute "
                "arbitrary code during unpickling.",
            )
        elif root == "yaml" and attr == "load":
            loader = next((kw.value for kw in node.keywords if kw.arg == "Loader"), None)
            if loader is None:
                yield RuleHit(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    message="yaml.load() without an explicit safe Loader can construct "
                    "arbitrary Python objects from the YAML input.",
                )
            else:
                loader_name = (
                    loader.id if isinstance(loader, ast.Name) else _root_name(loader) or ""
                )
                if "safe" not in loader_name.lower():
                    yield RuleHit(
                        line=node.lineno,
                        column=node.col_offset + 1,
                        message=f"yaml.load() with Loader={loader_name or '?'} is unsafe; "
                        "use yaml.safe_load() / Loader=SafeLoader.",
                    )


def _is_dynamic_string(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    ):
        return True
    return False


def _check_sql_injection(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in {"execute", "executemany", "executescript"}:
            continue
        if node.args and _is_dynamic_string(node.args[0]):
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="A SQL statement appears to be built with string interpolation; "
                "use parameterized queries instead.",
            )


_SUBPROCESS_CALLS = {"Popen", "run", "call", "check_call", "check_output"}


def _check_shell_true(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else (node.func.attr if isinstance(node.func, ast.Attribute) else None)
        )
        if func_name not in _SUBPROCESS_CALLS:
            continue
        if any(
            kw.arg == "shell"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
            for kw in node.keywords
        ):
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="A subprocess is started with shell=True; command strings can be "
                "injected through shell metacharacters.",
            )


def _check_shell_execution(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        root = node.func.value
        if isinstance(root, ast.Name) and root.id == "os" and node.func.attr in {"system", "popen"}:
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message=f"os.{node.func.attr}() runs a shell command; prefer the subprocess "
                "module with argument lists (never shell=True with user input).",
            )


def _check_weak_hash(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.ImportFrom) and node.module in {
            "Crypto.Cipher.DES",
            "Crypto.Cipher.DES3",
            "Crypto.Cipher.ARC4",
            "Crypto.Hash.MD5",
            "Crypto.Hash.SHA1",
        }:
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message=f"Weak cryptographic primitive imported: {node.module}.",
            )
            continue
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        root = node.func.value
        if isinstance(root, ast.Name) and root.id == "hashlib":
            if node.func.attr in {"md5", "sha1"}:
                skip = any(
                    kw.arg == "usedforsecurity"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is False
                    for kw in node.keywords
                )
                if not skip:
                    yield RuleHit(
                        line=node.lineno,
                        column=node.col_offset + 1,
                        message=f"hashlib.{node.func.attr}() is a broken/weak hash; use SHA-256 "
                        "or better (and a salted KDF for passwords).",
                    )
            elif node.func.attr == "new" and node.args:
                algo = _const_str(node.args[0])
                if algo and algo.strip().lower() in {"md5", "sha1"}:
                    yield RuleHit(
                        line=node.lineno,
                        column=node.col_offset + 1,
                        message=f"hashlib.new('{algo}') selects a weak hash algorithm.",
                    )


_RANDOM_ATTRS = {
    "random",
    "randint",
    "randrange",
    "choice",
    "choices",
    "randbytes",
    "uniform",
    "sample",
}


def _check_insecure_randomness(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Assign):
            continue
        if not (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Name)
            and node.value.func.value.id == "random"
            and node.value.func.attr in _RANDOM_ATTRS
        ):
            continue
        for name in _assigned_names(list(node.targets)):
            if SECURITY_RANDOM_NAME.search(name):
                yield RuleHit(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    message=f'"{name}" is generated with the non-cryptographic "random" module; '
                    "use the \"secrets\" module for tokens, salts and keys.",
                )


def _check_tls_verification_disabled(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "verify" and isinstance(kw.value, ast.Constant) and kw.value.value is False:
                    yield RuleHit(
                        line=node.lineno,
                        column=node.col_offset + 1,
                        message="TLS certificate verification is disabled (verify=False); "
                        "connections become vulnerable to man-in-the-middle attacks.",
                    )
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "_create_unverified_context":
                yield RuleHit(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    message="An unverified SSL context is created; certificate validation is off.",
                )
        if isinstance(node, ast.Attribute) and node.attr == "CERT_NONE":
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="ssl.CERT_NONE disables certificate validation on this connection.",
            )


def _check_debug_mode(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "debug" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                yield RuleHit(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    message="Debug mode is enabled; debug servers leak internals and can "
                    "allow remote code execution (e.g. Werkzeug debugger).",
                )


_PATH_CALLS = {"open", "Path", "remove", "unlink", "rename", "mkdir", "makedirs", "rmtree"}


def _check_path_traversal(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else (node.func.attr if isinstance(node.func, ast.Attribute) else None)
        )
        if func_name not in _PATH_CALLS or not node.args:
            continue
        if _is_dynamic_string(node.args[0]):
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="A filesystem path is built by string interpolation; validate/canonicalize "
                "it (e.g. os.path.realpath + prefix check) to prevent path traversal.",
            )


def _check_insecure_temp_file(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        root = node.func.value
        root_name = root.id if isinstance(root, ast.Name) else None
        combo = (root_name, node.func.attr)
        if combo == ("tempfile", "mktemp") or (root_name == "os" and node.func.attr in {"tempnam", "tmpnam"}):
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="Insecure temporary file creation (race-prone); use tempfile.mkstemp().",
            )


def _check_assert(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if isinstance(node, ast.Assert):
            yield RuleHit(
                line=node.lineno,
                column=node.col_offset + 1,
                message="assert statements are stripped when Python runs with -O; never use "
                "them for validation, access control or security checks.",
            )


def _check_bind_all_interfaces(ctx: RuleContext):
    for node in ast.walk(ctx.tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == "host" and isinstance(kw.value, ast.Constant) and kw.value.value in {"0.0.0.0", "::"}:
                yield RuleHit(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    message='The server binds to "all interfaces" (0.0.0.0/::).',
                )


SECURITY_RULES: list[Rule] = [
    Rule(
        rule_id="SEC001",
        title="Hardcoded Password",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="A password-like variable is assigned (or compared against) a string "
        "literal directly in the source code.",
        recommendation="Load credentials from environment variables or a secret manager, "
        "never from source literals.",
        check=_check_hardcoded_password,
    ),
    Rule(
        rule_id="SEC002",
        title="Dangerous eval()",
        category=CATEGORY_SECURITY,
        severity=CRITICAL,
        description="eval() compiles and runs arbitrary Python expressions from a string, "
        "so any injected input becomes executable code.",
        recommendation="Replace with ast.literal_eval for data, or parse/validate the input "
        "explicitly.",
        check=_check_dangerous_eval,
    ),
    Rule(
        rule_id="SEC003",
        title="Dangerous exec()",
        category=CATEGORY_SECURITY,
        severity=CRITICAL,
        description="exec() runs arbitrary Python statements from a string; injected input "
        "becomes executable code with full process privileges.",
        recommendation="Refactor to explicit functions/classes; never execute dynamic source.",
        check=_check_dangerous_exec,
    ),
    Rule(
        rule_id="SEC004",
        title="Unsafe Deserialization",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="pickle/dill/yaml.load can instantiate arbitrary objects; untrusted "
        "payloads lead to remote code execution.",
        recommendation="Use JSON for untrusted data, yaml.safe_load for YAML, and never "
        "unpickle untrusted bytes.",
        check=_check_unsafe_deserialization,
    ),
    Rule(
        rule_id="SEC005",
        title="SQL Injection Pattern",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="A SQL statement is assembled with f-strings/concatenation/format, "
        "allowing input to alter the query.",
        recommendation="Use parameterized queries (cursor.execute(sql, params)) or an ORM.",
        check=_check_sql_injection,
    ),
    Rule(
        rule_id="SEC006",
        title="Subprocess shell=True",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="A subprocess call runs through the shell, so metacharacters in any "
        "argument can inject commands.",
        recommendation="Pass an argument list and shell=False; validate/shlex-join anything dynamic.",
        check=_check_shell_true,
    ),
    Rule(
        rule_id="SEC007",
        title="Shell Execution (os.system)",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="os.system/os.popen spawn a shell; embedded input can run arbitrary commands.",
        recommendation="Use subprocess.run with an argument list and shell=False.",
        check=_check_shell_execution,
    ),
    Rule(
        rule_id="SEC008",
        title="Weak Cryptographic Hash",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="MD5/SHA-1 (or legacy ciphers like DES/RC4) are cryptographically broken "
        "or weak.",
        recommendation="Use SHA-256+ for hashing and a salted KDF (bcrypt/argon2/PBKDF2) for passwords.",
        check=_check_weak_hash,
    ),
    Rule(
        rule_id="SEC009",
        title="Insecure Randomness",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="A security-sensitive value (token/salt/nonce/password) is generated with "
        "the non-cryptographic random module.",
        recommendation="Use the secrets module: secrets.token_hex/token_bytes/randbelow.",
        check=_check_insecure_randomness,
    ),
    Rule(
        rule_id="SEC010",
        title="TLS Verification Disabled",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="Certificate verification is turned off (verify=False / CERT_NONE / "
        "unverified context), enabling man-in-the-middle attacks.",
        recommendation="Keep verification on; pin a CA bundle instead of disabling it.",
        check=_check_tls_verification_disabled,
    ),
    Rule(
        rule_id="SEC011",
        title="Hardcoded Secret / API Key",
        category=CATEGORY_SECURITY,
        severity=HIGH,
        description="A secret-like name (api_key, secret, token...) is assigned a string "
        "literal, or a literal matches a known service key format.",
        recommendation="Move secrets to environment variables or a secret manager and rotate "
        "anything committed.",
        check=_check_hardcoded_secret,
    ),
    Rule(
        rule_id="SEC012",
        title="Debug Mode Enabled",
        category=CATEGORY_SECURITY,
        severity=LOW,
        description="debug=True in a server/web call exposes tracebacks and interactive "
        "debuggers to attackers.",
        recommendation="Disable debug in production builds; drive it from configuration.",
        check=_check_debug_mode,
    ),
    Rule(
        rule_id="SEC013",
        title="Dynamic Path Construction",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="A filesystem path is built with string interpolation; crafted input can "
        "escape the intended directory (path traversal).",
        recommendation="Canonicalize with os.path.realpath and verify the result stays inside "
        "the expected base directory.",
        check=_check_path_traversal,
    ),
    Rule(
        rule_id="SEC014",
        title="Insecure Temporary File",
        category=CATEGORY_SECURITY,
        severity=MEDIUM,
        description="mktemp/tempnam create predictable temp paths that other users can hijack "
        "(race condition).",
        recommendation="Use tempfile.mkstemp/NamedTemporaryFile which create the file securely.",
        check=_check_insecure_temp_file,
    ),
    Rule(
        rule_id="SEC015",
        title="Assert Used as Control Flow",
        category=CATEGORY_SECURITY,
        severity=LOW,
        description="assert disappears under python -O, silently disabling any check it guards.",
        recommendation="Use explicit `if not cond: raise ...` for runtime validation.",
        check=_check_assert,
    ),
    Rule(
        rule_id="SEC016",
        title="Bind to All Interfaces",
        category=CATEGORY_SECURITY,
        severity=LOW,
        description="A server binds to 0.0.0.0/::, exposing the service on every network "
        "interface.",
        recommendation="Bind to the specific interface required, or put it behind a controlled "
        "proxy.",
        check=_check_bind_all_interfaces,
    ),
]
