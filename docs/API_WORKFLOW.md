# API Workflow

## 1. Health and provider readiness

```http
GET /api/v1/health
```

Returns database status, selected synthesis/embedding mode and configured provider names. It never returns credentials.

## 2. Project and historical context

```http
POST /api/v1/projects
GET  /api/v1/projects
POST /api/v1/projects/{project_id}/historical-themes
GET  /api/v1/projects/{project_id}/historical-themes
```

## 3. Dataset ingestion

```http
POST /api/v1/projects/{project_id}/datasets
GET  /api/v1/projects/{project_id}/datasets
GET  /api/v1/datasets/{dataset_id}
```

Upload uses multipart form data with `file`. Optional `column_mapping_json` can override inferred aliases.

## 4. Analysis

```http
POST /api/v1/datasets/{dataset_id}/analysis-runs
GET  /api/v1/datasets/{dataset_id}/analysis-runs
GET  /api/v1/analysis-runs/{run_id}
GET  /api/v1/analysis-runs/{run_id}/summary
GET  /api/v1/analysis-runs/{run_id}/theme-cards
GET  /api/v1/analysis-runs/{run_id}/logs
```

`theme-cards` returns each non-merged theme with deterministic metrics for efficient dashboard rendering.

## 5. Theme review

```http
GET   /api/v1/themes/{theme_id}
PATCH /api/v1/themes/{theme_id}/rename
PATCH /api/v1/themes/{theme_id}
POST  /api/v1/themes/merge
POST  /api/v1/themes/{theme_id}/split
POST  /api/v1/themes/{theme_id}/approve
POST  /api/v1/themes/{theme_id}/reject
GET   /api/v1/themes/{theme_id}/history
```

All review operations preserve an audit record. Merge and split are transactional.

## 6. Reports

```http
POST /api/v1/analysis-runs/{run_id}/reports
GET  /api/v1/projects/{project_id}/reports
GET  /api/v1/reports/{report_id}
```

Reports snapshot approved theme copy, metrics, evidence and historical comparison.

## Error shape

```json
{
  "error": {
    "code": "HTTP_422",
    "message": "Request could not be completed.",
    "details": {},
    "request_id": "..."
  }
}
```
