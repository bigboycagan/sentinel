# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for a security vulnerability.

Report it privately through the repository's
[GitHub Security Advisories](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
("Report a vulnerability"). Include:

- a description of the issue and its impact,
- the steps or a minimal source file that reproduces it,
- the affected version or commit.

You can expect an acknowledgement within 72 hours and a status update within
seven days.

## Supported versions

| Version | Supported |
|---|---|
| `1.x` | ✅ |
| `< 1.0` | ❌ |

## SENTINEL's threat model

SENTINEL treats every submitted file as **untrusted input**. The guarantees the
implementation is expected to uphold:

| Guarantee | Where it is enforced |
|---|---|
| Analyzed code is **never executed** — parsed to an AST only | `backend/analyzers/python/parser.py` |
| No `eval`/`exec`/`compile` on user input | entire `backend/analyzers/` tree |
| No shell invoked on user content | no `subprocess` use in the analysis path |
| File type validation (`.py` only) | `backend/routers/analysis.py`, `frontend/src/components/analyzer/FileUpload.tsx` |
| Server-side file size limits, clamped 10 KB–10 MB | `backend/routers/analysis.py`, `backend/lib/store.py` |
| Hostile input (nesting bombs, null bytes) degrades to a parse error | `backend/analyzers/python/parser.py` |
| Request body validation | Pydantic v2 models in `backend/models/` |
| File name sanitization | `sanitize_file_name` in `backend/routers/analysis.py` |
| Rate limiting per client | `backend/lib/rate_limit.py` |
| No raw stack traces returned to clients | `HTTPException` details only |
| Parameterized SQL for all storage queries | `backend/lib/store.py` |

A bypass of any row above — in particular **anything that causes analyzed code
to execute** — is a security vulnerability and should be reported privately.

## Privacy guarantees

- Source code is **never sent to a third party**: no AI provider, no LLM, no
  external code-analysis API, no telemetry.
- Source code is **not persisted**. Saving an analysis stores only the
  structured report (scores, counts, findings).
- History is scoped to an anonymous `httpOnly` session cookie.

## Secrets

Never commit real credentials. Configuration lives in `backend/.env` (ignored
by git); `backend/.env.example` documents the variables with placeholder
values only.
