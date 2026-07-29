# Signalboard v2.0.0 — Release Status

## Complete

- integrated FastAPI backend and premium responsive reviewer UI
- PostgreSQL/SQLite persistence
- deterministic ingestion, analytics and evidence validation
- GitHub Models, OpenAI, Ollama and heuristic provider adapters
- safe live-provider self-test
- historical product-memory CRUD and comparison rerun
- rename, edit, merge, split, approve and reject
- immutable reviewed reports and workflow logs
- keyboard-accessible modals and interactive states
- mapped public sample and deterministic release verifier
- Docker, Render Blueprint, health checks and startup retry
- README hero, animated product GIF and real interface screenshots
- 20 automated tests with more than 80% statement coverage

## Operator checks before submission

1. Deploy the latest `main` commit.
2. Confirm `/api/v1/health` reports database connected and version 2.0.0.
3. Run **Provider settings → Run live provider check** with the private token configured.
4. Run the included sample, inspect evidence, approve a theme and save a report.
5. Refresh the page and confirm persistence.
6. Open the public URL in an incognito window.

## Intentional limitations

- free Render cold starts cannot be removed by application code
- live provider verification requires the operator's secret
- synchronous analysis should move to a queue for materially larger workloads
- demo user header should be replaced by production authentication for multi-tenant use
