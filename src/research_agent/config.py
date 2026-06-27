from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration for the research agent system.

    Loaded from process environment (and an optional ``.env``). Secrets are
    held as ``SecretStr``; numeric memory windows carry field-level bounds so
    invalid values fail at load time rather than deep inside the memory
    subsystem.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM — OpenAI-compatible endpoint, per-agent model ids.
    llm_base_url: str
    llm_api_key: SecretStr
    coordinator_model: str
    web_search_model: str
    report_model: str

    # Coordinator orchestration loop bound.
    coordinator_max_rounds: int = Field(default=5, ge=1)

    # Coordinator memory.
    memory_recent_rounds: int = Field(default=5, ge=1)
    memory_compress_every_rounds: int = Field(default=5, ge=1)
    memory_data_dir: Path

    # Web search backend.
    tavily_api_key: SecretStr

    # API base URL the UI calls.
    api_base_url: str = "http://localhost:8000"
