# Changelog

All notable changes to SENTINEL are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] — 2026-01-07

Second language family: **JavaScript and TypeScript**, plus the official brand
mark. Still no AI.

### Added

- **JavaScript / TypeScript analyzer** (`backend/analyzers/javascript/`) built
  on tree-sitter with the JavaScript, TypeScript and TSX grammars. JSX and TSX
  parse correctly; the analyzed code is never executed (tree-sitter is a
  parser with no evaluation facility, and no Node.js runtime is involved).
- **38 new rules** (70 total):
  - 17 security rules (`JS-SEC001`–`JS-SEC017`) — hardcoded passwords and
    secrets (incl. JWT shapes), `eval`, implied eval (`new Function`,
    string timers), SQL injection, command injection, XSS sinks
    (`innerHTML`/`document.write`/`insertAdjacentHTML`),
    `dangerouslySetInnerHTML`, weak hashes, `Math.random()` for secrets,
    disabled TLS verification, dynamic paths, dynamic `require`/`import`,
    `vm` execution, wildcard `postMessage`, credentials in web storage,
    executable URL literals.
  - 13 code-quality rules (`JS-QUA001`–`JS-QUA013`) — unused variables and
    imports, unreachable code, excessive nesting, long functions and files,
    poor naming, empty `catch`, loose equality, `var`, leftover `console`,
    `debugger`, TODO markers.
  - 2 TypeScript-only rules (`TS-QUA001`–`TS-QUA002`) — explicit `any` and
    `@ts-ignore`/`@ts-nocheck`/`@ts-expect-error` suppressions.
  - 2 complexity rules and 4 maintainability rules (`JS-CPL*`, `JS-MNT*`),
    including a too-many-parameters check.
- **`GET /api/languages`** — the engine's language registry, with extensions.
  The frontend language selector and upload validation are derived from it
  rather than hardcoded.
- **Upload routing by extension** — `.py`, `.pyi`, `.js`, `.jsx`, `.mjs`,
  `.cjs`, `.ts`, `.tsx`, `.mts`, `.cts`. The extension, not a client-supplied
  field, selects the analyzer.
- **Frontend multi-language support** — language selector, per-language demo
  snippets (vulnerable Express API, unsafe React component, clean TypeScript
  module), CodeMirror syntax modes for JS/TS/JSX/TSX, and a language filter
  plus language badge on the Rules page.
- **Brand mark** — the official SENTINEL logo in the header (theme-aware) and
  as the favicon set, generated reproducibly by `scripts/build_logo_assets.py`.
- **56 new tests** (108 total), including `tests/test_engine_javascript.py`
  which covers the JS/TS engine independently of the UI.

### Changed

- Report assembly, severity counting and scoring extracted to
  `backend/analyzers/report.py` and shared by every analyzer (previously
  inline in the Python analyzer). Scoring behaviour is unchanged.
- `analyzers/engine.py` now owns a language registry; adding a language is a
  single map entry.
- Upload rejection message now lists every supported extension instead of
  naming Python only.

### Fixed

- JS/TS function and class counts no longer double-count: the grammar emits
  the bare `function`/`class` keyword as a node, so metrics now require a
  named node with children.
- The unused-variable rule no longer treats locals inside an *exported*
  function as exported, which had suppressed valid findings.

### Dependencies

- Added `tree-sitter`, `tree-sitter-javascript`, `tree-sitter-typescript`
  (backend) and `@codemirror/lang-javascript` (frontend). No AI service, no
  analysis API, no Node.js runtime on the backend.

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
