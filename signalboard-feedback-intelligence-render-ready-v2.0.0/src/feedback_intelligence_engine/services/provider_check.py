from __future__ import annotations

import time

import httpx

from ..config import Settings
from ..schemas import ProviderSelfTestOut


def _github_check(settings: Settings) -> ProviderSelfTestOut:
    started = time.perf_counter()
    url = settings.github_models_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.github_token}",
        "X-GitHub-Api-Version": settings.github_api_version,
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=min(settings.ai_request_timeout_seconds, 35.0)) as client:
        response = client.post(
            url,
            headers=headers,
            json={
                "model": settings.github_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Return exactly the word READY. Do not add punctuation.",
                    },
                    {"role": "user", "content": "Provider readiness check."},
                ],
                "temperature": 0,
                "max_tokens": 8,
            },
        )
        response.raise_for_status()
        data = response.json()
    content = str(data["choices"][0]["message"]["content"]).strip()
    latency = int((time.perf_counter() - started) * 1000)
    return ProviderSelfTestOut(
        status="ok" if "READY" in content.upper() else "degraded",
        provider="github",
        model=settings.github_model,
        llm_operational=True,
        latency_ms=latency,
        message="GitHub Models returned a live inference response.",
        request_id=response.headers.get("x-github-request-id") or data.get("id"),
    )


def _openai_check(settings: Settings) -> ProviderSelfTestOut:
    started = time.perf_counter()
    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - installation/configuration path
        raise RuntimeError("The optional openai package is not installed") from exc
    client = OpenAI(api_key=settings.openai_api_key, timeout=min(settings.ai_request_timeout_seconds, 35.0))
    response = client.responses.create(
        model=settings.openai_synthesis_model,
        input="Return exactly the word READY.",
        max_output_tokens=8,
    )
    latency = int((time.perf_counter() - started) * 1000)
    content = getattr(response, "output_text", "").strip()
    return ProviderSelfTestOut(
        status="ok" if "READY" in content.upper() else "degraded",
        provider="openai",
        model=settings.openai_synthesis_model,
        llm_operational=True,
        latency_ms=latency,
        message="OpenAI returned a live inference response.",
        request_id=getattr(response, "id", None),
    )


def _ollama_check(settings: Settings) -> ProviderSelfTestOut:
    started = time.perf_counter()
    with httpx.Client(timeout=min(settings.ai_request_timeout_seconds, 35.0)) as client:
        response = client.post(
            settings.ollama_base_url.rstrip("/") + "/api/generate",
            json={
                "model": settings.ollama_synthesis_model,
                "prompt": "Return exactly the word READY.",
                "stream": False,
                "options": {"temperature": 0, "seed": 42, "num_predict": 8},
            },
        )
        response.raise_for_status()
        data = response.json()
    latency = int((time.perf_counter() - started) * 1000)
    content = str(data.get("response", "")).strip()
    return ProviderSelfTestOut(
        status="ok" if "READY" in content.upper() else "degraded",
        provider="ollama",
        model=settings.ollama_synthesis_model,
        llm_operational=True,
        latency_ms=latency,
        message="Ollama returned a live local inference response.",
        request_id=None,
    )


def run_provider_self_test(settings: Settings) -> ProviderSelfTestOut:
    if settings.synthesis_provider == "github" or (
        settings.synthesis_provider == "auto" and settings.github_token
    ):
        return _github_check(settings)
    if settings.synthesis_provider == "openai" or (
        settings.synthesis_provider == "auto" and settings.openai_api_key
    ):
        return _openai_check(settings)
    if settings.synthesis_provider == "ollama" or (
        settings.synthesis_provider == "auto" and settings.ollama_enabled
    ):
        return _ollama_check(settings)
    return ProviderSelfTestOut(
        status="degraded",
        provider="heuristic",
        model=None,
        llm_operational=False,
        latency_ms=0,
        message=(
            "Deterministic fallback is available, but no live LLM provider is configured. "
            "Add a server-side GitHub Models, OpenAI, or Ollama configuration."
        ),
        request_id=None,
    )
