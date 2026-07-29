# Render Deployment Guide

## What the Blueprint creates

- one Docker-based FastAPI web service
- one PostgreSQL database
- a database connection injected as `DATABASE_URL`
- a required secret placeholder for `GITHUB_TOKEN`
- the included health check at `/api/v1/health`

Both resources use Render's free plan in `render.yaml`.

## Before deployment

1. Create a GitHub repository.
2. Place all files from the release ZIP at the repository root. `render.yaml` and `Dockerfile` must remain at the root.
3. Push the repository.
4. Create a fine-grained GitHub personal access token with only the `models:read` permission. No repository-content permission is required for model inference.

Never place the token in `.env`, source code, commit history, screenshots or README files.

## Blueprint deployment

1. Open the Render Dashboard.
2. Select **New → Blueprint**.
3. Connect the GitHub repository.
4. Confirm that Render detects `render.yaml`.
5. Enter the `GITHUB_TOKEN` value when prompted for the `sync: false` secret.
6. Deploy the Blueprint.

The Docker image installs the Python package, includes the static UI and starts through the `feedback-engine` entrypoint. The entrypoint binds to `0.0.0.0` and reads Render's `$PORT` value.

## Deployment validation

After the service is live:

1. Open `https://<service>.onrender.com/api/v1/health`.
2. Confirm:

```json
{
  "status": "ok",
  "database": "connected",
  "ai_configured": true,
  "version": "1.0.0"
}
```

3. Open the product root URL.
4. Choose **Run real sample**.
5. Wait for the review dashboard.
6. Open a theme and verify original evidence.
7. Approve one theme.
8. Save a reviewed report.
9. Refresh the page and confirm the report persists.

## Troubleshooting

### Health check shows `ai_configured: false`

The GitHub token was not configured. Add `GITHUB_TOKEN` in the Render service's environment settings and redeploy.

### Analysis returns a provider error

- confirm the token has `models:read`
- confirm the selected model still exists in GitHub Models
- check GitHub Models rate limits
- set `SYNTHESIS_PROVIDER=auto` so transient provider failures can fall back safely

### Database connection fails

Confirm the web service's `DATABASE_URL` references the Blueprint database. The application converts Render's PostgreSQL URL to the psycopg 3 SQLAlchemy driver automatically.

### Initial page takes time to open

A free Render web service sleeps after inactivity and can take about a minute to wake.

## Free-tier limits

Render's free web-service filesystem is ephemeral; this project therefore uses PostgreSQL for persistent application data. Free Render PostgreSQL expires 30 days after creation. Upgrade or migrate the database if the application must remain available longer.
