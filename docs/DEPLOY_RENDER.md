# Render Deployment Guide

## Existing connected repository — recommended update path

Do not delete the Render Blueprint or PostgreSQL database. Replacing the repository contents is enough.

1. Download and extract the final ZIP.
2. In the GitHub repository, replace the old source files with the ZIP-root files.
3. Verify the repository root contains `Dockerfile`, `render.yaml`, `.env.example`, `.gitignore`, `src/`, `tests/` and `README.md`.
4. Commit to `main`.
5. Render should auto-deploy because the Blueprint uses `autoDeployTrigger: commit`.
6. If it does not start, open the web service and choose **Manual Deploy → Deploy latest commit**.
7. Keep the existing database resource; it contains persisted projects and reports.

Deleting all repository files and uploading the new set also works, provided the replacement is committed and the required root/dotfiles are present. There is no need to recreate the Render service.

> Browser uploads sometimes miss dotfiles. After the commit, explicitly confirm `.env.example` and `.gitignore` appear on GitHub. `.env.example` has blank values only. Never upload a real `.env`.

## What the Blueprint creates

- Docker-based FastAPI web service
- PostgreSQL database
- injected `DATABASE_URL`
- private `GITHUB_TOKEN` placeholder
- `/api/v1/health` monitoring
- automatic deployment from commits to the connected branch

Both resources are configured with Render's free plan.

## New Blueprint deployment

1. Put all extracted ZIP-root files at the GitHub repository root.
2. Create a fine-grained GitHub token with only `models:read`.
3. In Render choose **New → Blueprint**.
4. Connect the repository and allow Render to read `render.yaml`.
5. Enter `GITHUB_TOKEN` when prompted.
6. Deploy both resources.

The Docker entrypoint reads Render's `$PORT`. PostgreSQL stores durable data rather than the web service's ephemeral filesystem.

## Validation after every deployment

1. Wait for **Deploy live**.
2. Open `/api/v1/health` and confirm:

```json
{
  "status": "ok",
  "database": "connected",
  "ai_configured": true,
  "version": "2.0.0"
}
```

3. Open the product.
4. Choose **Verify engine → Run live provider check**.
5. Confirm `llm_operational` is true and the displayed provider/model are expected.
6. Run the included sample.
7. Inspect source evidence, perform a review action and save a report.
8. Refresh and confirm persistence.
9. Open the public URL in an incognito window.

## Troubleshooting

### Old UI remains visible

- confirm Render deployed the latest GitHub commit SHA
- use a hard refresh or incognito window
- if needed select **Clear build cache & deploy** once

### `.env.example` is missing on GitHub

Create it through **Add file → Create new file** and paste the blank values from the extracted file. Never copy the real Render token into it.

### Provider check is degraded

- confirm `GITHUB_TOKEN` exists in Render Environment
- confirm the token has `models:read`
- save the environment and redeploy
- check provider rate limits/model availability

### Database connection fails

The web service's `DATABASE_URL` must be supplied from `feedback-intelligence-db` by the Blueprint. Do not replace it with a local SQLite path in Render.

### First request is slow or temporarily returns 503

Free Render web services sleep after inactivity. The application has database startup retry and health checks, but the platform wake-up delay cannot be removed in code. Wait about a minute, refresh, and open the application shortly before review.

## Free-tier boundary

Free web-service storage is ephemeral; persisted product state is therefore in PostgreSQL. Free PostgreSQL is suitable for a time-limited review window and is not an indefinite production database.
