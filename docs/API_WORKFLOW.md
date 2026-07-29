# API Workflow

The OpenAPI document is available at `docs/openapi.json` and `/docs` when the service runs.

## Primary flow

```text
POST /api/v1/projects
POST /api/v1/projects/{project_id}/historical-themes    # optional, repeatable
POST /api/v1/projects/{project_id}/datasets             # multipart CSV
POST /api/v1/datasets/{dataset_id}/analysis-runs
GET  /api/v1/analysis-runs/{run_id}/theme-cards
GET  /api/v1/themes/{theme_id}
POST /api/v1/themes/{theme_id}/approve
POST /api/v1/analysis-runs/{run_id}/reports
GET  /api/v1/reports/{report_id}
```

## Historical product memory

```text
GET    /api/v1/projects/{project_id}/historical-themes
POST   /api/v1/projects/{project_id}/historical-themes
PATCH  /api/v1/projects/{project_id}/historical-themes/{history_id}
DELETE /api/v1/projects/{project_id}/historical-themes/{history_id}
```

A new analysis run performs the latest historical comparison. Historical records do not enter current evidence counts.

## Review actions

```text
PATCH /api/v1/themes/{theme_id}/rename
PATCH /api/v1/themes/{theme_id}
POST  /api/v1/themes/{theme_id}/approve
POST  /api/v1/themes/{theme_id}/reject
POST  /api/v1/themes/merge
POST  /api/v1/themes/{theme_id}/split
GET   /api/v1/themes/{theme_id}/history
```

Merge and split use database transactions and preserve source memberships.

## Provider readiness

```text
POST /api/v1/providers/self-test
```

The endpoint performs a minimal live inference for GitHub Models, OpenAI or Ollama. It returns operational status without returning any secret.

## Observability

```text
GET /api/v1/health
GET /api/v1/analysis-runs/{run_id}/summary
GET /api/v1/analysis-runs/{run_id}/logs
```

Every HTTP response includes `X-Request-Id`. Workflow logs use the same request/run context where applicable.
