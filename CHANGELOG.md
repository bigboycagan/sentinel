# Changelog

All notable changes to SENTINEL are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-01-01

The first release: a working Python static-analysis engine with a full
dashboard. **AI is intentionally not included.**

### Added

- **Analysis engine** — deterministic Python analysis built on `ast` and
  `tokenize`, with a modular rule engine and zero code execution.
- **32 built-in rules** across four categories:
  - 16 security rules (`SEC001`–`SEC016`) — hardcoded passwords and secrets,
    `eval`/`exec`, unsafe deserialization, SQL injection patterns,
    `shell=True`, `os.system`, weak hashes, insecure randomness, disabled TLS
    verification, debug mode, dynamic paths, insecure temp files, `assert` as
    control flow, binding to all interfaces.
  - 11 code-quality rules (`QUA001`–`QUA011`) — unused variables and imports,
    unreachable code, excessive nesting, long functions and files, poor
    naming, bare `except`, mutable defaults, wildcard imports, TODO markers.
  - 2 complexity rules (`CPL001`–`CPL002`) — per-function and average
    cyclomatic complexity, with severity escalation.
  - 3 maintainability rules (`MNT001`–`MNT003`) — maintainability index and
    documentation coverage.
- **Metrics** — cyclomatic complexity, max nesting depth, function/class
  counts, line composition, average function length, Halstead volume and a
  radon-derived maintainability index.
- **Deterministic scoring** — 0–100 per category with a diminishing severity
  penalty, plus a weighted overall score (Security 35%, Code Quality 25%,
  Complexity 20%, Maintainability 20%). Documented in `analyzers/scoring.py`.
- **API** — `POST /api/analyze`, `POST /api/analyze/upload`, `GET /api/rules`,
  full `/api/history` CRUD, and `GET`/`PUT /api/settings`.
- **Frontend** — landing page, dashboard, analyzer, history, rules catalog and
  settings, in a dark developer/security theme.
- **Code editor** — CodeMirror 6 with Python highlighting, line numbers and
  per-line severity stripes for findings.
- **File upload** — `.py` validation, size limits, and file metadata/status.
- **Issue explorer** — severity/category/rule filters, search, sorting, and a
  detail panel with explanation, location, offending line and remediation.
- **History** — opt-in saving; stores the report only, never source code.
- **Settings** — theme, maximum file size, and per-rule enable/disable.
- **Storage** — SQLite for history and settings, structured for a later
  PostgreSQL swap.
- **Security hardening** — untrusted-input handling, safe parsing, file type
  and size validation, file name sanitization, rate limiting, and polished
  error states with no stack traces.
- **Tests** — 51 pytest specs covering the engine independently of the UI plus
  the HTTP API.
- **Documentation** — README, CONTRIBUTING, SECURITY, `.env.example`, MIT
  license and CI workflows.
- **Future-proof AI seam** — `analyzers/intelligence.py` declares the
  `Explainer` protocol a later optional layer would implement. Unused in v1.

### Deliberately excluded

- Any AI model, LLM or external AI API.
- Any external code-analysis API.
- Any execution of analyzed source code.

## [Unreleased]

See the [roadmap](README.md#roadmap): more languages and GitHub scanning (v2),
optional local AI (v3), AI-assisted remediation (v4).
