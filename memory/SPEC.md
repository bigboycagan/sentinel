# SENTINEL — living spec

## What the app does

SENTINEL is a privacy-first **static code analysis and security platform** for
Python source. A user pastes code (or uploads a `.py` file), clicks Analyze,
and gets a deterministic report: four category scores, an overall score,
severity counts, measured metrics, and a filterable list of findings each with
an exact location and remediation note.

**No AI anywhere.** Analysis is Python `ast` + `tokenize` + a custom rule
engine running on this backend. No LLM, no external AI API, no external
code-analysis API, no outbound requests with user code. Analyzed code is
**parsed, never executed**.

## Data model

SQLite at `backend/data/sentinel.db` (path from `SENTINEL_DB_PATH`).

### `analyses`
`id` (uuid4 PK), `sid` (session cookie), `created_at` (ISO UTC), `file_name`,
`language`, `overall_score`, `security_score`, `total_issues`,
`critical_issues`, `high_issues`, `medium_issues`, `low_issues`,
`info_issues`, `report` (JSON of the full `AnalysisReport`).
Index: `(sid, created_at DESC)`.

**Source code is never stored** — only the structured report.

### `app_settings`
Single row `key='global'` holding JSON: `max_file_size_bytes` (default
1,000,000; clamped 10 KB–10 MB) and `disabled_rules` (list of rule IDs).

## Engine structure

```
backend/analyzers/
  engine.py            analyze_code() + language registry (_ANALYZERS)
  base.py              Rule, RuleHit, severities, categories
  scoring.py           deterministic scoring (documented formulas)
  intelligence.py      future AI seam — UNUSED in v1
  python/
    analyzer.py        PythonAnalyzer: parse → metrics → rules → score
    parser.py          safe ast.parse (never executes)
    metrics.py         complexity, nesting, Halstead, maintainability index
    context.py         RuleContext passed to each check
    rules/{security,quality,complexity,maintainability}.py
```

**32 rules**: SEC001–SEC016 (Security), QUA001–QUA011 (Code Quality),
CPL001–CPL002 (Complexity), MNT001–MNT003 (Maintainability).

### Scoring (deterministic, in `scoring.py`)

Severity weights CRITICAL 25 / HIGH 15 / MEDIUM 7 / LOW 2 / INFO 0.5. Within a
category, weights sort descending and the *i*-th contributes
`weight * 0.85**i`; `score = max(0, round(100 - penalty))`. Overall = weighted
mean: Security 35%, Quality 25%, Complexity 20%, Maintainability 20%.
A file that fails to parse gets `scores: null` / `overall_score: null` — never
a fabricated zero.

## API (all on `api_router`, prefix `/api`)

| Method | Path | Notes |
|---|---|---|
| POST | `/analyze` | `{code, file_name, language}` → `AnalysisReport`. 400 empty/unsupported language, 413 too large, 429 rate limited |
| POST | `/analyze/upload` | multipart `file` (+ `language`); 400 non-`.py` or non-UTF-8 |
| GET | `/rules` | `RuleMeta[]` from the engine registry (32) |
| GET | `/history` | `HistorySummary[]` for this session |
| POST | `/history` | re-analyzes server-side, then saves → `HistorySummary` |
| GET | `/history/{id}` | full `AnalysisReport`; 404 if not this session's |
| DELETE | `/history/{id}` | 404 if unknown |
| DELETE | `/history` | `{deleted: n}` |
| GET / PUT | `/settings` | `AppSettings`; PUT 400 on unknown rule ID |

Rate limit: 30 analyses/minute/IP (`ANALYSIS_RATE_LIMIT_PER_MIN`).

## Key flows

1. **Analyze** — `/analyzer`: pick a sample or paste/upload → **Analyze** →
   score ring + category bars + severity counts + bar chart + radar + metrics,
   plus the issue explorer. Editor lines gain severity stripes.
2. **Inspect a finding** — click any issue row → right sheet with explanation,
   `file:line:column`, the offending line, recommendation, rule ID, severity.
3. **Save & review** — **Save to history** → appears on `/history` and feeds
   the `/dashboard` aggregates. Delete one or clear all.
4. **Browse rules** — `/rules`: all 32 rules, filter by severity/category,
   search by ID/name/description.
5. **Configure** — `/settings`: theme (dark default), max file size, per-rule
   toggles (disabled rules are skipped on the next analysis).

## Auth / roles

**None.** No accounts by design (v1 MVP priority). History is scoped to an
anonymous `httpOnly` cookie `sentinel_sid` (uuid4, 1 year), set automatically
on first `/api/history` call. There is no login, no PIN and no gated area —
every page is reachable without credentials.

## Seed data

None required. The analyzer ships three real demo snippets in
`frontend/src/lib/samples.ts` (Vulnerable Flask API — loaded by default,
Complex Algorithm, Clean Python Module) which the engine genuinely analyzes.
History starts empty for every new browser session.

## Error states (exact copy)

- Empty code → "Please provide source code to analyze."
- Invalid Python → "Unable to parse this source file. Check the syntax and try again."
- Wrong file type → "Unsupported file type. SENTINEL currently supports Python files."
- Server error → "Something went wrong while analyzing the code."

No raw stack traces ever reach the client.

## Deliberate deviations from the spec

- **MongoDB is unused.** The template ships a motor handle; SENTINEL stores
  everything in SQLite per spec §14. `MONGO_URL`/`DB_NAME` remain in `.env`
  only for template compatibility.
- **Ruff/Bandit/Radon are not runtime dependencies.** Spec §3 allows them
  "where appropriate" but also requires SENTINEL's own rule engine; v1 uses
  only the native engine (radon's MI *formula* is reimplemented in
  `metrics.py`). `engine.py` is the documented adapter point for them.
- **CodeMirror 6 instead of Monaco** — chosen by the user; same required
  features (highlighting, line numbers, dark theme, issue indicators).
- **No authentication** — spec §26 ranks it 13th; v1 stops before it.
