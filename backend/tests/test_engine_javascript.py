"""Engine tests for the JavaScript / TypeScript analyzer (UI- and HTTP-independent)."""

import pytest

from analyzers.engine import (
    EmptySourceError,
    UnsupportedLanguageError,
    all_rules,
    analyze_code,
    language_for_file,
    supported_languages,
)
from models.analysis import Finding

CLEAN_JS = """/** Inventory helpers. */
export function totalValue(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}
"""

CLEAN_TS = """/** Typed arithmetic. */
export function add(first: number, second: number): number {
  return first + second;
}
"""


def run(code: str, name: str = "sample.js", language: str = "javascript"):
    return analyze_code(code, name, language)


def rule_ids(report) -> set[str]:
    return {f.rule_id for f in report.findings}


def find(report, rule_id: str) -> Finding:
    matches = [f for f in report.findings if f.rule_id == rule_id]
    assert matches, f"{rule_id} not detected; got {sorted(rule_ids(report))}"
    return matches[0]


# --- registry / routing ------------------------------------------------------


def test_languages_registered():
    ids = {info.id for info in supported_languages()}
    assert ids == {"python", "javascript", "typescript"}


@pytest.mark.parametrize(
    ("file_name", "expected"),
    [
        ("a.js", "javascript"),
        ("a.jsx", "javascript"),
        ("a.mjs", "javascript"),
        ("a.ts", "typescript"),
        ("a.tsx", "typescript"),
        ("a.py", "python"),
        ("a.rb", None),
        ("a.txt", None),
        ("", None),
    ],
)
def test_language_detection_by_extension(file_name, expected):
    assert language_for_file(file_name) == expected


def test_rule_ids_unique_across_languages():
    ids = [rule.rule_id for rule in all_rules()]
    assert len(ids) == len(set(ids))


def test_javascript_rules_registered():
    js_rules = [r for r in all_rules() if r.rule_id.startswith(("JS-", "TS-"))]
    assert len(js_rules) >= 30
    for rule in js_rules:
        assert rule.language in {"javascript", "typescript"}
        assert rule.description and rule.recommendation


# --- security ----------------------------------------------------------------


def test_detects_hardcoded_password_declaration():
    report = run('const dbPassword = "Pr0duction!Pass";\nexport default dbPassword;\n')
    finding = find(report, "JS-SEC001")
    assert finding.severity == "HIGH"
    assert finding.line == 1


def test_detects_password_compared_to_literal():
    report = run('export function check(password) {\n  return password === "letmein2024";\n}\n')
    assert "JS-SEC001" in rule_ids(report)


def test_ignores_env_and_placeholder_credentials():
    report = run(
        'const password = process.env.DB_PASSWORD;\nconst token = "changeme";\n'
        "export { password, token };\n"
    )
    assert "JS-SEC001" not in rule_ids(report)
    assert "JS-SEC004" not in rule_ids(report)


def test_detects_hardcoded_api_key_and_jwt():
    assert "JS-SEC004" in rule_ids(run('export const apiKey = "ak_live_8f2n9d0a7s6f5g4h";\n'))
    jwt = (
        'export const t = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.'
        'dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk";\n'
    )
    assert "JS-SEC004" in rule_ids(run(jwt))


def test_detects_eval():
    finding = find(run("export function r(src) {\n  return eval(src);\n}\n"), "JS-SEC002")
    assert finding.severity == "CRITICAL"
    assert finding.line == 2


def test_detects_implied_eval():
    assert "JS-SEC003" in rule_ids(run("export const f = new Function('a', 'return a');\n"))
    assert "JS-SEC003" in rule_ids(run('setTimeout("doThing()", 10);\n'))
    # A real function reference is fine.
    assert "JS-SEC003" not in rule_ids(run("setTimeout(() => doThing(), 10);\n"))


def test_detects_sql_injection_and_ignores_parameterized():
    vulnerable = "export function get(db, id) {\n  return db.query(`SELECT * FROM t WHERE id = ${id}`);\n}\n"
    assert "JS-SEC005" in rule_ids(run(vulnerable))
    safe = 'export function get(db, id) {\n  return db.query("SELECT * FROM t WHERE id = ?", [id]);\n}\n'
    assert "JS-SEC005" not in rule_ids(run(safe))


def test_detects_command_injection():
    report = run(
        'import cp from "child_process";\n'
        "export function ping(host) {\n"
        '  cp.exec("ping -c 1 " + host);\n'
        "}\n"
    )
    finding = find(report, "JS-SEC006")
    assert finding.severity == "HIGH"


def test_detects_xss_sinks():
    report = run("export function render(el, input) {\n  el.innerHTML = input;\n}\n")
    assert "JS-SEC007" in rule_ids(report)
    # A static string is not a sink.
    assert "JS-SEC007" not in rule_ids(run('export function r(el) {\n  el.innerHTML = "<b>hi</b>";\n}\n'))


def test_detects_dangerously_set_inner_html_in_tsx():
    report = run(
        "export const V = () => <div dangerouslySetInnerHTML={{ __html: window.name }} />;\n",
        "V.tsx",
        "typescript",
    )
    assert "JS-SEC008" in rule_ids(report)


def test_detects_weak_hash_and_allows_sha256():
    weak = 'import crypto from "crypto";\nexport const h = (v) => crypto.createHash("md5").update(v);\n'
    assert "JS-SEC009" in rule_ids(run(weak))
    strong = 'import crypto from "crypto";\nexport const h = (v) => crypto.createHash("sha256").update(v);\n'
    assert "JS-SEC009" not in rule_ids(run(strong))


def test_detects_insecure_randomness():
    report = run("export function make() {\n  const sessionToken = Math.random();\n  return sessionToken;\n}\n")
    assert "JS-SEC010" in rule_ids(report)
    # Non-security values may use Math.random freely.
    assert "JS-SEC010" not in rule_ids(
        run("export function jitter() {\n  const delay = Math.random();\n  return delay;\n}\n")
    )


def test_detects_tls_verification_disabled():
    report = run(
        'import https from "https";\n'
        "export const agent = new https.Agent({ rejectUnauthorized: false });\n"
    )
    assert "JS-SEC011" in rule_ids(report)


def test_detects_path_traversal_and_dynamic_require():
    report = run(
        'import fs from "fs";\n'
        "export function read(name) {\n"
        "  return fs.readFileSync(`/data/${name}`);\n"
        "}\n"
    )
    assert "JS-SEC012" in rule_ids(report)
    assert "JS-SEC013" in rule_ids(run("export const load = (n) => require(`./plugins/${n}`);\n"))


def test_detects_vm_execution_and_postmessage_wildcard():
    assert "JS-SEC014" in rule_ids(
        run('import vm from "vm";\nexport const r = (s) => vm.runInNewContext(s);\n')
    )
    assert "JS-SEC015" in rule_ids(run('window.parent.postMessage(payload, "*");\n'))


def test_detects_credentials_in_web_storage():
    report = run('export function save(t) {\n  localStorage.setItem("authToken", t);\n}\n')
    assert "JS-SEC016" in rule_ids(report)
    assert "JS-SEC016" not in rule_ids(
        run('export function save(v) {\n  localStorage.setItem("theme", v);\n}\n')
    )


# --- quality -----------------------------------------------------------------


def test_detects_unused_variable_and_import():
    assert "JS-QUA001" in rule_ids(run("export function f() {\n  const unused = 5;\n  return 1;\n}\n"))
    assert "JS-QUA001" not in rule_ids(
        run("export function f() {\n  const total = 5;\n  return total;\n}\n")
    )
    assert "JS-QUA002" in rule_ids(run('import lodash from "lodash";\nexport const x = 1;\n'))
    assert "JS-QUA002" not in rule_ids(
        run('import lodash from "lodash";\nexport const x = lodash.now();\n')
    )


def test_underscore_prefixed_variable_is_allowed():
    assert "JS-QUA001" not in rule_ids(run("export function f() {\n  const _spare = 5;\n  return 1;\n}\n"))


def test_detects_unreachable_code():
    assert "JS-QUA003" in rule_ids(
        run('export function f() {\n  return 1;\n  console.log("nope");\n}\n')
    )


def test_detects_excessive_nesting():
    code = (
        "export function deep(rows) {\n"
        "  for (const a of rows) {\n"
        "    if (a) {\n"
        "      for (const b of a) {\n"
        "        if (b) {\n"
        "          while (b.next) {\n"
        "            b.step();\n"
        "          }\n"
        "        }\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "  return rows;\n"
        "}\n"
    )
    assert "JS-QUA004" in rule_ids(run(code))


def test_detects_empty_catch_loose_equality_var_and_debugger():
    code = (
        "export function f(a) {\n"
        "  try {\n"
        "    risky();\n"
        "  } catch (e) {}\n"
        "  var legacy = 1;\n"
        "  debugger;\n"
        "  return a == legacy;\n"
        "}\n"
    )
    ids = rule_ids(run(code))
    assert {"JS-QUA008", "JS-QUA009", "JS-QUA010", "JS-QUA012"} <= ids


def test_nullish_loose_equality_is_allowed():
    assert "JS-QUA009" not in rule_ids(run("export const f = (a) => a == null;\n"))


def test_detects_console_and_todo_as_info():
    report = run('// TODO: finish this\nexport function f() {\n  console.log("x");\n}\n')
    assert find(report, "JS-QUA011").severity == "INFO"
    assert find(report, "JS-QUA013").severity == "INFO"


# --- TypeScript-only rules ---------------------------------------------------


def test_typescript_rules_only_apply_to_typescript():
    ts = run("export function parse(input: any): string {\n  return input.trim();\n}\n", "a.ts", "typescript")
    assert "TS-QUA001" in rule_ids(ts)

    suppressed = run("// @ts-ignore\nexport const x: number = 1;\n", "a.ts", "typescript")
    assert "TS-QUA002" in rule_ids(suppressed)

    # The JS analyzer must not carry TypeScript-only rules at all.
    js_analyzer_rules = {
        rule.rule_id
        for rule in analyze_code.__globals__["get_analyzer"]("javascript").rules
    }
    assert not any(rule_id.startswith("TS-") for rule_id in js_analyzer_rules)


# --- complexity --------------------------------------------------------------


def test_complexity_metrics_counted():
    code = (
        "export function grade(score) {\n"
        '  if (score > 90) return "A";\n'
        '  else if (score > 80) return "B";\n'
        '  else if (score > 70) return "C";\n'
        '  return "F";\n'
        "}\n"
    )
    report = run(code)
    assert report.metrics.function_count == 1
    assert report.metrics.max_complexity == 4  # 1 + three if/else-if branches


def test_function_and_class_counts_are_not_double_counted():
    code = (
        "function a() { return 1; }\n"
        "const b = () => 2;\n"
        "const c = function () { return 3; };\n"
        "class K { m() { return 4; } }\n"
        "export { a, b, c, K };\n"
    )
    report = run(code)
    assert report.metrics.function_count == 4
    assert report.metrics.class_count == 1


def test_short_circuit_operators_add_complexity():
    report = run("export const f = (a, b, c) => (a && b) || c;\n")
    assert report.metrics.max_complexity == 3  # 1 + && + ||


def test_high_complexity_escalates_severity():
    branches = "".join(f"  if (v === {i}) return {i};\n" for i in range(1, 25))
    report = run(f"export function dispatch(v) {{\n{branches}  return 0;\n}}\n")
    assert find(report, "JS-CPL001").severity == "CRITICAL"


def test_nesting_depth_metric():
    code = "export function f(rows) {\n  for (const r of rows) {\n    if (r) return r;\n  }\n  return null;\n}\n"
    assert run(code).metrics.max_nesting_depth == 2


# --- maintainability ---------------------------------------------------------


def test_too_many_parameters():
    report = run("export function wide(a, b, c, d, e, f, g) {\n  return [a, b, c, d, e, f, g];\n}\n")
    assert "JS-MNT004" in rule_ids(report)
    assert "JS-MNT004" not in rule_ids(run("export function narrow(a, b) {\n  return a + b;\n}\n"))


def test_jsdoc_suppresses_undocumented_finding():
    body = "".join(f"  const v{i} = {i};\n" for i in range(25))
    undocumented = f"export function big() {{\n{body}  return 0;\n}}\n"
    assert "JS-MNT003" in rule_ids(run(undocumented))
    documented = f"/** Does the thing. */\nexport function big() {{\n{body}  return 0;\n}}\n"
    assert "JS-MNT003" not in rule_ids(run(documented))


# --- edge cases --------------------------------------------------------------


def test_empty_source_raises_for_js():
    with pytest.raises(EmptySourceError):
        run("")
    with pytest.raises(EmptySourceError):
        run("   \n\n ")


def test_invalid_javascript_reports_parse_error_without_scores():
    report = run("function broken( {\n")
    assert report.parse_error is not None
    assert report.parse_error.line >= 1
    assert report.scores is None
    assert report.overall_score is None
    assert report.findings == []


def test_invalid_typescript_reports_parse_error():
    report = run("export function f(a: : number) {}\n", "a.ts", "typescript")
    assert report.parse_error is not None
    assert report.scores is None


def test_unsupported_language_raises():
    with pytest.raises(UnsupportedLanguageError):
        analyze_code("package main", "main.go", "go")


def test_clean_sources_score_well():
    js = run(CLEAN_JS, "inventory.js")
    assert js.counts.total == 0
    assert js.overall_score == 100

    ts = run(CLEAN_TS, "add.ts", "typescript")
    assert ts.counts.total == 0
    assert ts.overall_score == 100


def test_analysis_is_deterministic():
    code = 'export function f(p) {\n  const password = "abc12345";\n  return eval(p) + password;\n}\n'
    first, second = run(code), run(code)
    assert first.overall_score == second.overall_score
    assert [f.rule_id for f in first.findings] == [f.rule_id for f in second.findings]


def test_disabled_rule_is_skipped_for_js():
    code = "export const r = (s) => eval(s);\n"
    assert "JS-SEC002" in rule_ids(run(code))
    disabled = analyze_code(code, "a.js", "javascript", ["JS-SEC002"])
    assert "JS-SEC002" not in rule_ids(disabled)


def test_findings_carry_file_language_and_snippet():
    report = run("export const r = (s) => eval(s);\n", "target.js")
    finding = find(report, "JS-SEC002")
    assert finding.file == "target.js"
    assert "eval" in (finding.code_snippet or "")
    assert report.language == "javascript"


def test_jsx_in_plain_js_parses():
    report = run("export const A = () => <div className='x'>hi</div>;\n", "A.jsx")
    assert report.parse_error is None
    assert report.overall_score is not None


def test_severity_classification_matches_rule_defaults():
    report = run(
        'export function f(s) {\n  const password = "abc12345";\n  return eval(s) + password;\n}\n'
    )
    severities = {f.rule_id: f.severity for f in report.findings}
    assert severities["JS-SEC002"] == "CRITICAL"
    assert severities["JS-SEC001"] == "HIGH"
