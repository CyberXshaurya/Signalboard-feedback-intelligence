# Engine Architecture

## Design goal

Signalboard converts structured feedback into evidence-grounded theme drafts while keeping measurement, review decisions and report publication outside model control.

## Main components

### Ingestion

- parses CSV headers and common aliases
- validates each required field
- preserves original text and creates normalised/masked copies
- records invalid rows and exact-duplicate warnings
- enforces row and upload-size limits

### Similarity and clustering

- TF-IDF is the deterministic zero-cost default
- optional dense embeddings are provider-adapted
- product-area metadata influences candidate grouping without inventing labels
- large candidate groups are split under a hard safety cap
- isolated comments are preserved rather than forced into themes

### Structured synthesis

Provider adapters accept candidate clusters and return typed theme drafts. GitHub Models and OpenAI use strict structured output; Ollama uses local JSON output; a deterministic heuristic keeps tests and recovery independent from external services.

The persistence layer validates every returned evidence ID against the candidate cluster. Unknown IDs cannot become citations.

### Deterministic analytics

All feedback counts, source/user/product distributions, rating summaries and time frequencies are calculated from `theme_feedback` memberships. They are never accepted from the model.

### Product memory

Historical themes and product notes are separately persisted. They provide retrieval/comparison context but never become current feedback memberships. Reviewers can add, edit, delete and rerun comparison.

### Human review

Theme review actions are transactional and audited:

- rename and edit copy
- merge themes while deduplicating memberships
- split selected evidence into a new theme
- approve or reject

### Reports

A saved report stores immutable theme, metric, evidence and historical-comparison snapshots. Later theme edits cannot mutate an earlier report.

### Provider readiness

`POST /api/v1/providers/self-test` performs a minimal live inference against the configured provider. The response includes provider, model, latency and request ID but never credentials. Deterministic fallback is reported as degraded rather than a live LLM.

## Deployment shape

```text
Browser UI
   │
   ▼
FastAPI service ───── Provider APIs / Ollama
   │
   ▼
PostgreSQL
```

The UI is bundled as package data and served by the API service. Render uses a Docker health check, `/api/v1/health`, database startup retry and `$PORT` binding.

## Current scalability boundary

Analysis is synchronous and appropriate for the assessment dataset and moderate CSV uploads. A production-scale next step is a queue-backed worker with resumable stages and object storage for original imports.
