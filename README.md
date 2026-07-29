# Signalboard — Feedback Intelligence

Signalboard is a deployable full-stack application for evidence-grounded product-feedback synthesis. It accepts structured CSV feedback, validates and persists every usable row, discovers related feedback, produces reviewable theme drafts, calculates all counts deterministically, supports human review actions, and saves immutable synthesis reports.

The FastAPI backend and responsive reviewer interface are delivered as one service and one repository.

## What is implemented

- CSV upload with required-field validation, common header aliases, invalid-row isolation and exact-duplicate warnings
- original, normalised and PII-masked feedback storage
- metadata-aware TF-IDF clustering with oversized-cluster protection
- GitHub Models structured-JSON synthesis with a legitimate server-side token
- optional OpenAI and local Ollama providers
- credential-free deterministic mode for testing and recovery
- evidence-ID grounding: unknown model IDs are removed before persistence
- repeated, mixed, isolated and uncertain pattern handling
- historical-theme comparison
- deterministic theme counts, source distribution, user-type distribution, product-area distribution, ratings and time frequency
- rename, edit, merge, split, approve and reject workflows
- reviewer action history and structured workflow logs
- immutable versioned reports containing metrics and original supporting feedback
- responsive UI, loading/empty/error/success states and real public sample data
- Docker, Render Blueprint, PostgreSQL support, CI and release verification

## Product safeguards

- The LLM never owns counts, percentages or roadmap priority.
- Every conclusion is tied to persisted feedback IDs.
- Feedback is treated as untrusted content, not as model instructions.
- PII-like values are masked before external model calls.
- Important AI actions require human review.
- Merge and split operations preserve source memberships transactionally.
- Saved reports are snapshots and do not change after later edits.
- Provider tokens remain in backend environment variables and are never sent to the browser.

## Repository layout

```text
.
├── src/feedback_intelligence_engine/   # API, persistence, AI workflow and bundled UI
├── tests/                              # unit, integration and deployment-contract tests
├── scripts/                            # real-data and release verification scripts
├── data/                               # 250-row public CFPB sample and smoke summary
├── docs/                               # architecture, API and deployment documentation
├── Dockerfile
├── render.yaml
├── pyproject.toml
├── requirements.txt
├── AGENT_USAGE.md
└── .env.example
```

## Run locally

Python 3.12 or 3.13 is supported.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
cp .env.example .env
uvicorn feedback_intelligence_engine.main:app --reload
```

Open:

- Product: `http://localhost:8000/`
- API documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`

For a completely offline run:

```env
SYNTHESIS_PROVIDER=heuristic
EMBEDDING_PROVIDER=tfidf
```

## Recommended free hosted AI path

GitHub Models provides included, rate-limited usage for prototyping. Create your own fine-grained personal access token with only the `models:read` permission.

```env
GITHUB_TOKEN=your_private_token
GITHUB_MODEL=openai/gpt-4.1-mini
GITHUB_API_VERSION=2026-03-10
SYNTHESIS_PROVIDER=auto
EMBEDDING_PROVIDER=tfidf
```

`auto` tries configured hosted/local providers and uses the deterministic fallback only when a provider is unavailable. Do not use tokens copied from public repositories and do not commit your token.

## Deploy directly to Render

This repository contains a root-level `render.yaml` and Dockerfile. The Blueprint creates one free web service and one free PostgreSQL database.

1. Unzip the release and push the files at the ZIP root to a new GitHub repository.
2. Create a fine-grained GitHub token with only `models:read`.
3. In Render, choose **New → Blueprint** and connect the repository.
4. During Blueprint creation, provide the requested `GITHUB_TOKEN` secret.
5. Deploy and open the generated `onrender.com` URL.
6. Verify `/api/v1/health`, then select **Run real sample** in the UI.

The application reads Render's `$PORT` automatically and stores application data in PostgreSQL rather than the ephemeral web-service filesystem.

Render's free web service sleeps after inactivity, and free Render PostgreSQL expires after 30 days. These free tiers are appropriate for the assignment review window, not indefinite production hosting. Detailed steps are in [`docs/DEPLOY_RENDER.md`](docs/DEPLOY_RENDER.md).

## Real-data release verification

The included sample contains 250 public CFPB complaint narratives mapped to the application schema.

```bash
PYTHONPATH=src python scripts/verify_release.py
```

Verified baseline for v1.0.0:

```text
accepted rows:       250
invalid rows:        0
duplicate warnings:  8
candidate themes:    39
evidence coverage:   100%
report creation:     passed
```

The narratives are consumer-submitted and are not independently verified. Review `data/README.md` before reuse.

## Tests

```bash
PYTHONPATH=src pytest --cov=feedback_intelligence_engine --cov-report=term --cov-fail-under=80
```

Release baseline:

```text
14 tests passed
83.47% statement coverage
```

Coverage includes ingestion, evidence grounding, strict GitHub Models JSON schema, provider failure behaviour, review actions, immutable reports, UI asset delivery, `$PORT` handling and the complete API workflow.

## Required CSV fields

```text
feedback_text
source
user_type
product_area
date
rating          # optional
```

Common aliases such as `comment`, `channel`, `segment`, `module`, `submitted_at` and `stars` are detected automatically.

## Known limitations

- Analysis runs synchronously. A queue-backed worker is recommended for much larger datasets or slow self-hosted models.
- TF-IDF is optimised for English. Multilingual production deployments should use a multilingual embedding model.
- The assignment UI uses a demo `X-User-Id` boundary. Replace it with verified session/JWT authentication before multi-tenant production use.
- Free GitHub Models usage is rate-limited and model availability can change; the model ID is configurable.
- Free Render PostgreSQL expires after 30 days.

See [`docs/VERIFICATION.md`](docs/VERIFICATION.md) for the exact checks completed and anything that could not be verified without operator credentials.
