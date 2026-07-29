# Verification Record — v1.0.0

## Automated test suite

Command:

```bash
PYTHONPATH=src pytest --cov=feedback_intelligence_engine --cov-report=term-missing --cov-fail-under=80
```

Result:

```text
14 passed
83.47% statement coverage
```

Covered behaviour includes:

- CSV aliases, required-field validation and invalid-row isolation
- duplicate detection
- evidence-ID grounding
- strict GitHub Models JSON-schema request contract
- OpenAI batching contract
- explicit provider credential failures
- merge and split membership preservation
- approval, rejection and audit history
- immutable report snapshots
- full upload-to-report API flow
- static UI and sample delivery
- package-version health reporting
- Render `$PORT` handling and Blueprint contract

## Real-data release verification

Command:

```bash
PYTHONPATH=src python scripts/verify_release.py
```

Result:

```text
version:             1.0.0
sample rows:         250
duplicate warnings:  8
themes:              39
coverage:            100%
workflow events:     4
report version:      1
status:              passed
```

This verification created a clean database, loaded the bundled CFPB sample, ran clustering and deterministic synthesis, checked source evidence, approved a theme, created an immutable report and read that report back.

## Browser integration verification

Chromium was run against the actual FastAPI service and a clean SQLite database. Browser network calls were routed to the live local API because direct loopback navigation is restricted in the execution environment.

Verified:

- empty-state product loads
- bundled 250-row sample imports from the UI
- analysis reaches the review dashboard
- deterministic metrics render
- theme evidence loads
- approving a theme persists
- saving a report persists
- rebuilding the page retains the report
- no JavaScript console errors
- no browser page errors

Release screenshots:

- `docs/release-dashboard.png`
- `docs/release-report.png`

## Package and startup verification

- built `feedback_intelligence_engine-1.0.0-py3-none-any.whl`
- installed the wheel into an isolated target directory
- confirmed bundled `index.html` and sample CSV are present in package data
- started the packaged entrypoint with `PORT=8130`
- confirmed the server bound to `0.0.0.0:8130`
- confirmed the health endpoint and product root returned successfully

## External provider verification boundary

No live external LLM call was made because no operator-owned credential was supplied. The following are verified with mocked provider contracts:

- GitHub Models endpoint, server-side bearer token, current API-version header and strict JSON schema
- OpenAI structured-output parsing and batching

The Render deployment still requires the operator to provide a legitimate GitHub Models token. This limitation is intentional; public or borrowed API credentials are not used.
