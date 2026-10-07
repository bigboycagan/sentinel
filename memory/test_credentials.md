# Test credentials — SENTINEL

**There are no credentials. SENTINEL v1 has no authentication by design.**

- No accounts, no login, no PIN, no gated area. Every page (`/`, `/dashboard`,
  `/analyzer`, `/history`, `/rules`, `/settings`) is reachable directly.
- History is scoped to an anonymous `httpOnly` cookie `sentinel_sid` (uuid4),
  set automatically by the backend on the first `/api/history` request. A fresh
  browser context simply starts with an empty history — that is the correct
  empty state, not an auth failure.
- To exercise history in a test: POST `/api/history` (or click **Save to
  history** in the Analyzer after analyzing) while preserving cookies, then
  read `/api/history` with the same cookie jar.

Authentication is item 13 on the spec's MVP priority list and is intentionally
out of scope for v1 (see `memory/SPEC.md` → "Deliberate deviations").
