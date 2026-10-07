# SENTINEL

> **Know your code before it becomes a problem.**

SENTINEL is a **privacy-first static code analysis and security platform**. It
analyzes source code locally, on its own backend, using real static-analysis
techniques — AST parsing, token analysis, complexity metrics and a custom rule
engine.

**Supported languages:** Python, JavaScript (incl. JSX) and TypeScript
(incl. TSX) — **70 built-in rules** in total.

> **AI is intentionally not included in v1.**
>
> There is no OpenAI, Gemini, Claude, Ollama or local LLM anywhere in the
> pipeline, and no external code-analysis API. Every finding is produced by
> deterministic code you can read in this repository.

**Your source code is analyzed by SENTINEL without sending it to an external AI
service.**

---

## Features

- **Security analysis** — hardcoded passwords and API keys, `eval`/`exec` and
  implied eval, unsafe `subprocess`/shell and command injection, unsafe
  deserialization (pickle/yaml), SQL injection patterns, XSS sinks
  (`innerHTML`, `document.write`, `dangerouslySetInnerHTML`), weak hashes,
  insecure randomness, disabled TLS verification, path traversal, dynamic
  module loading, `vm` execution, wildcard `postMessage`, credentials in web
  storage, insecure temp files and more.
- **Code quality** — unused variables and imports, unreachable code, excessive
  nesting, oversized functions and files, mutable default arguments, bare
  `except` / empty `catch`, wildcard imports, loose equality, `var` usage,
  `debugger` statements, weak naming, unresolved TODO markers, plus TypeScript
  checks for explicit `any` and `@ts-ignore` suppressions.
- **Complexity** — cyclomatic complexity per function, average/maximum
  complexity, maximum nesting depth, function/class counts, line composition.
- **Maintainability** — a radon-derived maintainability index computed from
  Halstead volume, complexity and SLOC, plus documentation indicators.
- **Deterministic scoring** — 0–100 per category plus a weighted overall score.
  The same file always produces the same score.
- **Results dashboard** — score ring, category bars, severity counts, severity
  bar chart and category radar, measured metrics.
- **Issue explorer** — filter by severity/category/rule, search, sort, and open
  any finding for the explanation, exact location, offending line and fix.
- **Code editor** — CodeMirror 6 with Python/JavaScript/TypeScript syntax
  highlighting, line numbers, a dark theme, and per-line severity stripes for
  every finding.
- **File upload** — `.py`, `.pyi`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`,
  `.tsx`, `.mts`, `.cts`, with graceful rejection, size limits, and
  file name/size/language/status display. The extension selects the analyzer.
- **History** — optionally save an analysis; the **report is stored, never your
  source code**. Delete one entry or clear everything.
- **Rules browser** — the full catalog, served from the engine's own registry,
  filterable by severity, category and language.
- **Settings** — theme, maximum file size, and per-rule enable/disable.

## Architecture

```
          ┌─────────────────────────────┐
          │  React 19 + TS frontend     │   relative /api calls only
          │  CodeMirror 6 · TanStack Q  │
          └──────────────┬──────────────┘
                         │  HTTP (same origin)
          ┌──────────────▼──────────────┐
          │  FastAPI  (routers/)        │
          │  validation · rate limit    │
          └──────────────┬──────────────┘
                         │
          ┌──────────────▼──────────────┐
          │  SENTINEL engine            │
          │  analyzers/engine.py        │
          │  language registry          │
          └──────────────┬──────────────┘
             ┌───────────┴───────────┐
             │                       │
   analyzers/python/        analyzers/javascript/
   (ast + tokenize)         (tree-sitter JS/TS/TSX)
             │                       │
   parser · metrics · rules/   parser · metrics · rules/
   (never executes code)       (never executes code)
             │                       │
             └───────────┬───────────┘
                         │
              analyzers/report.py   (shared assembly)
                         │
                   scoring.py  →  AnalysisResult
                         │
                         ▼
            Optional Intelligence Layer
         (analyzers/intelligence.py — NOT in v1)
```

The analysis pipeline is one function — `analyze_code(...) -> AnalysisReport`.
That return value is the seam a future AI layer would consume:

```
AnalysisResult → AI Provider → Explanation / Remediation
```

`analyzers/intelligence.py` declares the `Explainer` Protocol for that future
layer. **Nothing in v1 imports or calls it**, and the core application remains
fully functional without it.

### Adding a language

Each language is a package under `analyzers/<language>/` exposing an analyzer
class with `language`, `extensions` and `analyze(...)`. Register it in
`_ANALYZERS` in `analyzers/engine.py` — and that is the only wiring required.
The rules catalog, upload validation, the `/api/languages` endpoint and the
frontend language selector are all derived from that map, and report assembly
plus scoring are shared via `analyzers/report.py`.

The JavaScript package is the worked example of a second language: it reuses
the shared `Rule`/`RuleHit` contract and serves both JavaScript and TypeScript
from one analyzer, with TypeScript-only rules declared as
`language="typescript"`.

### Adding a rule

Append one `Rule(...)` to the relevant list in
`analyzers/<language>/rules/{security,quality,complexity,maintainability}.py`:

```python
Rule(
    rule_id="SEC017",
    title="My New Check",
    category=CATEGORY_SECURITY,
    severity=HIGH,
    description="What it detects and why it matters.",
    recommendation="How to fix it.",
    check=_my_check_function,   # (ctx) -> Iterable[RuleHit]
)
```

The rule immediately appears in analysis runs, in `GET /api/rules`, in the
Rules page and in Settings' toggles. No analyzer rewrite is required.

### Scoring algorithm

Fully documented in `backend/analyzers/scoring.py`:

1. Each finding's severity maps to a weight —
   `CRITICAL 25, HIGH 15, MEDIUM 7, LOW 2, INFO 0.5`.
2. Within a category, weights are sorted descending and the *i*-th finding
   contributes `weight * 0.85 ** i` (a diminishing penalty, so one bad file
   does not flatten the score into meaninglessness).
3. `score = max(0, round(100 - penalty))`.
4. Overall = weighted mean — **Security 35%, Code Quality 25%, Complexity 20%,
   Maintainability 20%**.

A file that fails to parse gets **no scores at all** (`null`) rather than a
fabricated zero.

## Technology stack

| Layer | Choice |
|---|---|
| Frontend | React 19, TypeScript (strict), Vite, Tailwind CSS v4, shadcn/ui, TanStack Query, CodeMirror 6, Recharts |
| Backend | Python 3.11, FastAPI, Pydantic v2, uvicorn |
| Analysis (Python) | Python `ast` + `tokenize`, custom metrics + custom rule engine |
| Analysis (JS/TS) | `tree-sitter` with the JavaScript/TypeScript/TSX grammars — a pure parsing library with no evaluation facility |
| Storage | SQLite (history + settings) — structured for a later PostgreSQL swap |
| Tests | pytest (engine + API), Playwright (e2e scaffold) |

Third-party linters are **not required**: SENTINEL has its own rule engine and
analysis layer. `analyzers/engine.py` is the adapter point if you later want to
fold in Ruff/Bandit/Radon output alongside SENTINEL's native rules.

## Installation

```bash
git clone <your-fork-url> sentinel && cd sentinel
cp backend/.env.example backend/.env     # then edit if needed
```

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Frontend

```bash
cd frontend
yarn install
yarn dev            # http://localhost:3000, proxies /api → :8001
```

## Local development

Every backend route is registered on one `APIRouter(prefix="/api")`; the Vite
dev server proxies `/api/*` to port 8001, so frontend code only ever calls
relative paths (`/api/analyze`). The same code works behind a single origin in
production.

### API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/analyze` | Analyze pasted source (JSON) |
| `POST` | `/api/analyze/upload` | Analyze an uploaded file (multipart); the extension selects the analyzer |
| `GET` | `/api/languages` | Languages the engine supports, with their extensions |
| `GET` | `/api/rules` | The full rule catalog |
| `GET` | `/api/history` | Saved analyses for this session |
| `POST` | `/api/history` | Analyze and save a report |
| `GET` | `/api/history/{id}` | One saved report |
| `DELETE` | `/api/history/{id}` | Delete one saved analysis |
| `DELETE` | `/api/history` | Clear this session's history |
| `GET` | `/api/settings` | Current analysis settings |
| `PUT` | `/api/settings` | Update size limit / disabled rules |

## Running tests

```bash
cd backend && pytest                  # engine + API suites
cd frontend && yarn typecheck         # TypeScript (strict)
cd frontend && yarn lint              # oxlint
```

The engine suites test the analysis engine **independently of the UI and of
HTTP**:

- `backend/tests/test_engine.py` — Python: hardcoded passwords, `eval`,
  `exec`, unsafe deserialization, SQL injection, shell usage, weak hashes,
  insecure randomness; complexity calculation; empty source; invalid Python;
  safe Python; the scoring system and severity escalation.
- `backend/tests/test_engine_javascript.py` — JavaScript/TypeScript: the same
  security classes plus XSS sinks, implied eval, command injection, web-storage
  credentials; quality rules; complexity and nesting metrics; TS-only rules;
  JSX/TSX parsing; invalid sources; clean sources; determinism.
- `backend/tests/test_api.py` — the HTTP surface for every language.

## Security considerations

Uploaded source is treated as **untrusted input**:

- **Never executed.** `ast.parse` (Python) and `tree-sitter` (JS/TS) build
  syntax trees; nothing is `eval`'d, `exec`'d, imported or run. tree-sitter is
  a parser with no evaluation facility, and no Node.js runtime is involved. No
  shell is invoked on user content.
- **No `eval`/`exec` on user input** anywhere in SENTINEL itself.
- **File type validation** — only registered extensions are accepted, rejected
  on both client and server; the extension, not a client-supplied field,
  selects the analyzer.
- **File size limits** — enforced server-side and clamped (10 KB–10 MB).
- **Safe parsing** — `RecursionError`/`MemoryError`/`ValueError` from hostile
  input become structured parse errors, not crashes.
- **Input validation** — Pydantic v2 models on every request body; unknown rule
  IDs are rejected; file names are sanitized (`os.path.basename` + whitelist).
- **Rate limiting** — sliding-window limiter on every analysis endpoint.
- **Error handling** — users see polished messages; raw stack traces are never
  returned to the client.

## Privacy model

- Analysis runs entirely on SENTINEL's own backend. **No outbound requests** are
  made with your code.
- No AI service, no LLM, no third-party code-analysis API.
- **Source code is not persisted.** Analysis is request-scoped; if you save an
  analysis, only the structured report (scores, counts, findings) is stored.
- History is scoped to an anonymous `httpOnly` session cookie — no accounts, no
  profiles, no tracking.
- No analytics or telemetry.

## Roadmap

**v1** — Python analyzer, AST rule engine, security/quality/complexity/
maintainability rules, deterministic scoring, dashboard, editor, upload, issue
explorer, rule browser, history, settings.

**v2 (in progress)** — ✅ JavaScript and TypeScript analyzers; next: Java, C#,
Go, more security rules, GitHub repository scanning, pull request analysis.

**v3** — optional **local** AI integration (opt-in, off by default).

**v4** — optional AI-assisted remediation.

### Future AI integration

AI is deliberately excluded from v1 so the product is useful, auditable and
private without it. When it arrives it will be **additive**: an `Explainer`
implementation that post-processes an `AnalysisReport` behind an explicit
opt-in flag. The static engine, the scoring and the rules will not change, and
SENTINEL will keep working with the layer switched off.

## License

MIT — see [LICENSE](LICENSE).
