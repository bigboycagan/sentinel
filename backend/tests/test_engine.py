"""Engine tests — the analysis engine is tested independently of the UI and HTTP."""

import pytest

from analyzers.engine import (
    EmptySourceError,
    UnsupportedLanguageError,
    all_rules,
    analyze_code,
)
from analyzers.scoring import category_score, overall_score
from models.analysis import Finding, ScoreBreakdown

CLEAN_SOURCE = '''"""A clean, safe module."""


def add(first: int, second: int) -> int:
    """Return the sum of two integers."""
    return first + second
'''


def run(code: str, name: str = "sample.py"):
    return analyze_code(code, name, "python")


def rule_ids(report) -> set[str]:
    return {f.rule_id for f in report.findings}


def find(report, rule_id: str) -> Finding:
    matches = [f for f in report.findings if f.rule_id == rule_id]
    assert matches, f"{rule_id} not detected; got {sorted(rule_ids(report))}"
    return matches[0]


# --- security detection ------------------------------------------------------


def test_detects_hardcoded_password():
    report = run('def login():\n    password = "SuperSecret123"\n    return password\n')
    finding = find(report, "SEC001")
    assert finding.severity == "HIGH"
    assert finding.category == "Security"
    assert finding.line == 2
    assert finding.recommendation


def test_detects_password_compared_to_literal():
    report = run('def check(password):\n    return password == "hunter2"\n')
    assert "SEC001" in rule_ids(report)


def test_ignores_placeholder_password():
    report = run('password = ""\nother = "changeme"\n')
    assert "SEC001" not in rule_ids(report)


def test_detects_hardcoded_api_key_and_key_prefix():
    report = run('api_key = "ak_live_9381saf9j2f9j2"\n')
    assert "SEC011" in rule_ids(report)
    prefixed = run('value = "sk-abcdefghijklmnopqrstuvwx"\n')
    assert "SEC011" in rule_ids(prefixed)


def test_detects_eval():
    report = run("def run(data):\n    return eval(data)\n")
    finding = find(report, "SEC002")
    assert finding.severity == "CRITICAL"
    assert finding.line == 2


def test_detects_exec():
    report = run("def run(data):\n    exec(data)\n")
    finding = find(report, "SEC003")
    assert finding.severity == "CRITICAL"


def test_detects_unsafe_deserialization():
    assert "SEC004" in rule_ids(run("import pickle\n\n\ndef load(b):\n    return pickle.loads(b)\n"))
    assert "SEC004" in rule_ids(run("import yaml\n\n\ndef load(t):\n    return yaml.load(t)\n"))


def test_safe_yaml_load_is_not_flagged():
    code = "import yaml\n\n\ndef load(text):\n    return yaml.safe_load(text)\n"
    assert "SEC004" not in rule_ids(run(code))


def test_detects_sql_injection_pattern():
    code = (
        "def fetch(cursor, user_id):\n"
        '    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")\n'
    )
    assert "SEC005" in rule_ids(run(code))


def test_parameterized_query_is_not_flagged():
    code = (
        "def fetch(cursor, user_id):\n"
        '    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))\n'
    )
    assert "SEC005" not in rule_ids(run(code))


def test_detects_shell_true_and_os_system():
    code = (
        "import os\n"
        "import subprocess\n\n\n"
        "def run(cmd):\n"
        "    subprocess.run(cmd, shell=True)\n"
        "    os.system(cmd)\n"
    )
    ids = rule_ids(run(code))
    assert "SEC006" in ids
    assert "SEC007" in ids


def test_detects_weak_hash_and_secure_hash_is_clean():
    assert "SEC008" in rule_ids(run("import hashlib\n\n\ndef h(b):\n    return hashlib.md5(b)\n"))
    clean = run("import hashlib\n\n\ndef h(b):\n    return hashlib.sha256(b)\n")
    assert "SEC008" not in rule_ids(clean)


def test_detects_insecure_randomness():
    code = "import random\n\n\ndef make():\n    session_token = random.random()\n    return session_token\n"
    assert "SEC009" in rule_ids(run(code))


def test_detects_tls_verification_disabled():
    code = "import requests\n\n\ndef get(url):\n    return requests.get(url, verify=False)\n"
    assert "SEC010" in rule_ids(run(code))


# --- quality detection -------------------------------------------------------


def test_detects_unused_variable_and_respects_underscore():
    assert "QUA001" in rule_ids(run("def f():\n    unused = 5\n    return 1\n"))
    assert "QUA001" not in rule_ids(run("def f():\n    _unused = 5\n    return 1\n"))


def test_used_variable_is_not_flagged():
    assert "QUA001" not in rule_ids(run("def f():\n    total = 5\n    return total\n"))


def test_detects_unused_import():
    assert "QUA002" in rule_ids(run("import os\n\n\ndef f():\n    return 1\n"))
    assert "QUA002" not in rule_ids(run("import os\n\n\ndef f():\n    return os.getcwd()\n"))


def test_detects_unreachable_code():
    assert "QUA003" in rule_ids(run("def f():\n    return 1\n    print('nope')\n"))


def test_detects_mutable_default_and_bare_except():
    assert "QUA009" in rule_ids(run("def f(items=[]):\n    return items\n"))
    assert "QUA008" in rule_ids(run("def f():\n    try:\n        pass\n    except:\n        pass\n"))


def test_detects_excessive_nesting():
    code = (
        "def deep(data):\n"
        "    for a in data:\n"
        "        if a:\n"
        "            for b in a:\n"
        "                if b:\n"
        "                    while b:\n"
        "                        b -= 1\n"
        "    return data\n"
    )
    assert "QUA004" in rule_ids(run(code))


# --- complexity --------------------------------------------------------------


def test_complexity_metrics_counted():
    code = (
        "def grade(score):\n"
        "    if score > 90:\n"
        "        return 'A'\n"
        "    elif score > 80:\n"
        "        return 'B'\n"
        "    elif score > 70:\n"
        "        return 'C'\n"
        "    return 'F'\n"
    )
    report = run(code)
    assert report.metrics.function_count == 1
    assert report.metrics.max_complexity == 4  # 1 + three if/elif branches
    assert report.metrics.total_lines == 8


def test_simple_function_has_complexity_one():
    report = run(CLEAN_SOURCE)
    assert report.metrics.max_complexity == 1
    assert report.metrics.class_count == 0


def test_high_complexity_rule_escalates_severity():
    branches = "".join(f"    if value == {i}:\n        return {i}\n" for i in range(1, 25))
    report = run(f"def dispatch(value):\n{branches}    return 0\n")
    finding = find(report, "CPL001")
    assert finding.severity == "CRITICAL"
    assert report.metrics.max_complexity > 20


def test_nesting_depth_metric():
    code = "def f(items):\n    for i in items:\n        if i:\n            return i\n    return None\n"
    assert run(code).metrics.max_nesting_depth == 2


# --- edge cases --------------------------------------------------------------


def test_empty_source_raises():
    with pytest.raises(EmptySourceError):
        run("")
    with pytest.raises(EmptySourceError):
        run("   \n\n  ")


def test_invalid_python_returns_parse_error_without_scores():
    report = run("def broken(:\n    pass\n")
    assert report.parse_error is not None
    assert report.parse_error.line >= 1
    assert report.scores is None
    assert report.overall_score is None
    assert report.findings == []


def test_unsupported_language_raises():
    with pytest.raises(UnsupportedLanguageError):
        analyze_code("int main(){}", "a.c", "c")


def test_safe_code_scores_perfectly():
    report = run(CLEAN_SOURCE)
    assert report.counts.total == 0
    assert report.overall_score == 100
    assert report.scores.security == 100


def test_analysis_is_deterministic():
    code = 'def f(p):\n    password = "abc12345"\n    return eval(p)\n'
    first, second = run(code), run(code)
    assert first.overall_score == second.overall_score
    assert [f.rule_id for f in first.findings] == [f.rule_id for f in second.findings]


def test_disabled_rule_is_skipped():
    code = "def f(d):\n    return eval(d)\n"
    assert "SEC002" in rule_ids(run(code))
    disabled = analyze_code(code, "a.py", "python", ["SEC002"])
    assert "SEC002" not in rule_ids(disabled)


def test_findings_carry_file_and_snippet():
    report = run("def f(d):\n    return eval(d)\n", "target.py")
    finding = find(report, "SEC002")
    assert finding.file == "target.py"
    assert "eval" in (finding.code_snippet or "")


# --- scoring -----------------------------------------------------------------


def _finding(severity: str, category: str = "Security") -> Finding:
    return Finding(
        rule_id="X",
        severity=severity,
        category=category,
        title="t",
        message="m",
        file="f.py",
        line=1,
        column=1,
        recommendation="r",
    )


def test_category_score_no_findings_is_100():
    assert category_score([]) == 100


def test_category_score_penalizes_by_severity():
    assert category_score([_finding("CRITICAL")]) == 75
    assert category_score([_finding("HIGH")]) == 85
    assert category_score([_finding("MEDIUM")]) == 93
    assert category_score([_finding("LOW")]) == 98


def test_severity_ordering_is_monotonic():
    scores = [
        category_score([_finding(sev)])
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
    ]
    assert scores == sorted(scores), "a worse severity must never score higher"


def test_score_penalty_diminishes_and_floors_at_zero():
    one = category_score([_finding("CRITICAL")])
    two = category_score([_finding("CRITICAL")] * 2)
    assert two < one
    assert 100 - two < 2 * (100 - one)  # diminishing, not linear
    assert category_score([_finding("CRITICAL")] * 40) == 0


def test_overall_score_weights_security_heaviest():
    weak_security = overall_score(
        ScoreBreakdown(security=0, quality=100, complexity=100, maintainability=100)
    )
    weak_quality = overall_score(
        ScoreBreakdown(security=100, quality=0, complexity=100, maintainability=100)
    )
    assert weak_security < weak_quality
    assert overall_score(
        ScoreBreakdown(security=100, quality=100, complexity=100, maintainability=100)
    ) == 100


# --- rule registry -----------------------------------------------------------


def test_rule_registry_is_well_formed():
    rules = all_rules()
    assert len(rules) >= 15
    ids = [r.rule_id for r in rules]
    assert len(ids) == len(set(ids)), "rule ids must be unique"
    for rule in rules:
        assert rule.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
        assert rule.category in {"Security", "Code Quality", "Complexity", "Maintainability"}
        assert rule.description and rule.recommendation


def test_every_category_has_rules():
    categories = {rule.category for rule in all_rules()}
    assert categories == {"Security", "Code Quality", "Complexity", "Maintainability"}
