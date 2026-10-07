# Contributing to SENTINEL

Thanks for helping make SENTINEL better. The project has one hard rule:

> **No AI, no external analysis APIs, no network calls with user code.**
> Every finding must come from deterministic static analysis.

## Getting set up

```bash
cp backend/.env.example backend/.env
cd backend && pip install -r requirements.txt
cd ../frontend && yarn install
```

Run the two dev servers (see [README.md](README.md#local-development)).

## Before opening a pull request

```bash
cd backend  && pytest
cd frontend && yarn typecheck && yarn lint
```

## Adding a rule

1. Write the check in the matching module under
   `backend/analyzers/python/rules/`. It takes a `RuleContext` and yields
   `RuleHit`s.
2. Append one `Rule(...)` to that module's list with a **new unique ID**
   (`SEC***` security, `QUA***` quality, `CPL***` complexity, `MNT***`
   maintainability).
3. Add a test in `backend/tests/test_engine.py` covering both a **positive**
   case (the rule fires) and a **negative** case (safe code is not flagged).

Rule requirements:

- Unique rule ID, category, severity, description, detection logic, recommendation.
- Deterministic — the same input must always produce the same output.
- No subprocesses, no network, no execution of the analyzed code.
- Prefer AST matching over regex on raw source; keep false positives low (skip
  obvious placeholders, env lookups, and `_`-prefixed throwaways).

## Adding a language

Create `backend/analyzers/<language>/` with an analyzer class exposing
`language`, `extensions` and `analyze(code, file_name, disabled_rules)`, then
register it in `_ANALYZERS` in `backend/analyzers/engine.py`. Mirror the
Python package layout (`parser.py`, `metrics.py`, `rules/`).

## Frontend conventions

- Call relative `/api` paths through `src/lib/api.ts` — never an absolute URL.
- Read and write through TanStack Query; invalidate affected keys after mutations.
- Every Pydantic model has a hand-written TS interface in `src/lib/types.ts`;
  update both in the same commit.
- Every interactive element needs a kebab-case `data-testid`.
- No page may be gated entirely on a fetch — degrade to a partial page.

## Code style

- Python: type hints, `async def` handlers, `await` every I/O call.
- TypeScript: `strict` stays on; use `import type` for types.
- Keep modules focused; prefer small functions over clever ones.
