"""Configuração central da aplicação (variáveis de ambiente)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Geophysics AI"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://geophysicsai:geophysicsai@db:5432/geophysicsai"
    redis_url: str = "redis://redis:6379/0"

    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "geophysicsai"
    s3_secret_key: str = "geophysicsai-secret"
    s3_bucket_layers: str = "geophysics-ai-layers"
    s3_bucket_reports: str = "geophysics-ai-reports"

    anthropic_api_key: str | None = None
    agent_model: str = "claude-sonnet-4-5"
    agent_max_tool_iterations: int = 8

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
