# Engine Architecture

## Deployment shape

The product is packaged as one FastAPI service:

```text
Browser reviewer UI
        │
        ▼
FastAPI API + static UI delivery
        │
        ├── CSV validation and privacy preprocessing
        ├── deterministic clustering and metrics
        ├── pluggable LLM synthesis provider
        ├── human review operations
        └── immutable reports and structured logs
        │
        ▼
SQLite locally / PostgreSQL in production
```

## Responsibility boundary

### Deterministic code owns

- row validation
- duplicate flags
- feedback membership
- counts and percentages
- source and user-type distributions
- frequency over time
- rating summaries
- merge and split transactions
- report snapshots

### LLM provider may propose

- theme title
- grounded summary
- user problem statement
- representative evidence IDs from a supplied cluster
- uncertainty language

Every returned evidence ID is validated against the persisted cluster before storage.

## Provider order

When `SYNTHESIS_PROVIDER=auto`:

1. GitHub Models when `GITHUB_TOKEN` is configured
2. OpenAI when `OPENAI_API_KEY` is configured
3. Ollama when `OLLAMA_ENABLED=true`
4. deterministic heuristic fallback

Explicit provider modes do not silently hide configuration failures.

Embeddings default to deterministic TF-IDF. OpenAI and Ollama dense embeddings can be selected explicitly.

## Reviewer UI

The UI uses semantic HTML, CSS and browser JavaScript with no package build step. It calls the same-origin `/api/v1` routes and is mounted at `/app`; `/` serves the product entry page.

The interface contains:

- overview dashboard
- dataset validation history
- theme review and evidence workspace
- merge and split selection flows
- approval and rejection controls
- immutable report inspection
- structured workflow activity

## Security posture

- model credentials are read only by the backend
- feedback is treated as untrusted prompt data
- basic PII masking occurs before model calls
- ownership checks are applied to projects, datasets, runs, themes and reports
- current demo identity uses `X-User-Id`; production should replace it with a verified session/JWT
