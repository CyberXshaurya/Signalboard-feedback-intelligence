# Free AI Setup

## Security rule

Do not copy API keys from GitHub repositories, gists, videos or shared documents. Public keys may be stolen, revoked or connected to someone else's account. This project only reads credentials from backend environment variables.

## Option 1 — GitHub Models

Use a fine-grained personal access token limited to `models:read`.

```env
GITHUB_TOKEN=
GITHUB_MODEL=openai/gpt-4.1-mini
GITHUB_API_VERSION=2026-03-10
SYNTHESIS_PROVIDER=auto
EMBEDDING_PROVIDER=tfidf
```

The token is used only by the FastAPI server. The browser never receives it. `auto` uses GitHub Models when available and preserves workflow availability with a logged deterministic fallback when the free quota or provider is temporarily unavailable. GitHub Models free usage is rate-limited, so keep the selected model configurable.

## Option 2 — Ollama

Install Ollama locally and pull a generation model plus an embedding model.

```bash
ollama pull llama3.2:3b
ollama pull embeddinggemma
```

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_SYNTHESIS_MODEL=llama3.2:3b
OLLAMA_EMBEDDING_MODEL=embeddinggemma
SYNTHESIS_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
```

## Option 3 — deterministic development mode

```env
SYNTHESIS_PROVIDER=heuristic
EMBEDDING_PROVIDER=tfidf
```

This mode is fully offline and ideal for tests, but the final reviewer deployment should use an operational LLM provider to satisfy the assignment requirement.
