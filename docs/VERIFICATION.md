# Verification Record — v2.0.0

## Automated suite

```bash
PYTHONPATH=src pytest --cov=feedback_intelligence_engine --cov-report=term-missing --cov-fail-under=80
```

Release result:

```text
20 tests passed
83%+ statement coverage
```

Covered behaviour:

- CSV aliases, required fields, invalid rows and duplicate warnings
- PII masking and evidence-ID grounding
- deterministic counts and distributions
- strict GitHub Models/OpenAI structured-output contracts
- provider self-test response boundaries
- historical product-memory create/update/delete
- merge and split membership preservation
- approve, reject, rename and audit history
- immutable report snapshots
- upload-to-report API workflow
- static UI delivery and complete visible-action dispatch audit
- Playwright modal, keyboard, historical-memory and primary review workflows
- package version, `$PORT`, health and Blueprint contracts

## Real-data release verification

```bash
PYTHONPATH=src python scripts/verify_release.py
```

Expected deterministic baseline:

```text
version:             2.0.0
accepted rows:       250
invalid rows:        0
duplicate warnings:  8
candidate themes:    39
evidence coverage:   100%
report version:      1
status:              passed
```

The release verifier creates a clean database, imports the mapped CFPB sample, runs synthesis, inspects cited evidence, approves a theme, saves an immutable report and reads the snapshot back.

## Browser verification

Playwright runs the actual bundled HTML/CSS/JavaScript in Chromium and routes requests to deterministic API fixtures. This is necessary because direct loopback browser navigation is restricted in the build environment; backend routes are independently exercised through FastAPI TestClient.

Verified clicks and keyboard behaviour:

- X, Done and Cancel close modals
- backdrop close and `Escape`
- focus restoration and focus containment
- provider self-test result rendering
- historical note add, edit and delete confirmation
- rename, approve, split and merge
- report snapshot creation
- keyboard import shortcut
- no page errors or browser console errors

## UI media verification

```bash
python scripts/capture_product_media.py
```

This captures the actual preview-mode product and creates:

- `docs/premium-overview.png`
- `docs/premium-themes.png`
- `docs/premium-history.png`
- `docs/premium-provider.png`
- `docs/signalboard-demo.gif`

## Provider verification boundary

A true hosted inference requires an operator-owned secret. No public or borrowed credential was used. Automated tests verify the GitHub Models bearer-token/header/schema contract and that secrets never enter the browser payload.

After deployment, use **Provider settings → Run live provider check**. A successful result must report:

- provider and model
- `llm_operational: true`
- measured latency
- a request ID

The deterministic fallback is intentionally reported as `degraded`, not falsely described as a live LLM.

## Render reliability boundary

The application includes:

- database startup retry during initial provisioning
- a Docker health check
- Render `/api/v1/health` monitoring
- `$PORT` binding
- persistent PostgreSQL rather than the ephemeral service filesystem

Render's free service can still sleep after inactivity. Code cannot eliminate that platform cold start; open the application before a scheduled review and confirm the health endpoint returns successfully.
