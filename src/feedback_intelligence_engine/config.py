from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./feedback_engine.db"

    # Paid/provider-specific options. Keys stay server-side and are never returned by the API.
    openai_api_key: str | None = None
    openai_synthesis_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # GitHub Models provides included, rate-limited usage with a fine-grained PAT that only has models:read.
    github_token: str | None = None
    github_model: str = "openai/gpt-4.1-mini"
    github_models_base_url: str = "https://models.github.ai/inference"
    github_api_version: str = "2026-03-10"

    # Fully local open-model option. No key is required when Ollama runs on the same/private network.
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_synthesis_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "embeddinggemma"

    synthesis_provider: Literal["auto", "openai", "github", "ollama", "heuristic"] = "auto"
    embedding_provider: Literal["auto", "openai", "ollama", "tfidf"] = "tfidf"

    max_upload_bytes: int = 10_000_000
    max_csv_rows: int = 5_000
    cluster_distance_threshold: float = Field(default=0.90, gt=0.0, lt=2.0)
    embedding_cluster_distance_threshold: float = Field(default=0.32, gt=0.0, lt=2.0)
    low_coherence_threshold: float = Field(default=0.08, ge=-1.0, le=1.0)
    metadata_weight: int = Field(default=2, ge=0, le=6)
    max_cluster_size: int = Field(default=30, ge=5, le=100)
    embedding_batch_size: int = Field(default=128, ge=1, le=2048)
    max_clusters_per_synthesis: int = Field(default=20, ge=1, le=50)
    max_ai_text_chars: int = Field(default=6000, ge=1000, le=20000)
    max_representative_items: int = Field(default=12, ge=3, le=30)
    ai_request_timeout_seconds: float = Field(default=120.0, ge=5.0, le=300.0)
    require_user_header: bool = False
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def configured_llm_providers(self) -> list[str]:
        providers: list[str] = []
        if self.github_token:
            providers.append("github")
        if self.openai_api_key:
            providers.append("openai")
        if self.ollama_enabled:
            providers.append("ollama")
        providers.append("heuristic")
        return providers


@lru_cache
def get_settings() -> Settings:
    return Settings()
