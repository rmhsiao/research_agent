import pytest
from pydantic import ValidationError

from research_agent.config import Settings

_VALID_ENV = {
    "LLM_BASE_URL": "https://llm.example/v1",
    "LLM_API_KEY": "sk-secret",
    "COORDINATOR_MODEL": "strong-model",
    "WEB_SEARCH_MODEL": "cheap-model",
    "REPORT_MODEL": "cheap-model",
    "MEMORY_RECENT_ROUNDS": "3",
    "MEMORY_COMPRESS_EVERY_ROUNDS": "4",
    "MEMORY_DATA_DIR": "data/sessions",
    "TAVILY_API_KEY": "tvly-secret",
    "API_BASE_URL": "http://api:8000",
}


def _set_env(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> None:
    env = {**_VALID_ENV, **overrides}
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


def _load() -> Settings:
    # _env_file=None: read only the patched process env, ignore any local .env.
    return Settings(_env_file=None)  # type: ignore[call-arg]


class TestSettingsLoad:
    def test_loads_all_fields_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch)
        settings = _load()
        assert settings.llm_base_url == "https://llm.example/v1"
        assert settings.coordinator_model == "strong-model"
        assert settings.web_search_model == "cheap-model"
        assert settings.report_model == "cheap-model"
        assert settings.recent_rounds == 3
        assert settings.compress_every_rounds == 4
        assert str(settings.memory_data_dir) == "data/sessions"
        assert settings.api_base_url == "http://api:8000"

    def test_secrets_are_wrapped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _set_env(monkeypatch)
        settings = _load()
        assert settings.llm_api_key.get_secret_value() == "sk-secret"
        assert settings.tavily_api_key.get_secret_value() == "tvly-secret"
        assert "sk-secret" not in str(settings.llm_api_key)

    def test_memory_rounds_default_when_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(
            monkeypatch,
            MEMORY_RECENT_ROUNDS=None,
            MEMORY_COMPRESS_EVERY_ROUNDS=None,
        )
        settings = _load()
        assert settings.recent_rounds == 5
        assert settings.compress_every_rounds == 5

    def test_api_base_url_default_when_absent(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _set_env(monkeypatch, API_BASE_URL=None)
        assert _load().api_base_url == "http://localhost:8000"


class TestSettingsConfigValidation:
    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_recent_rounds_below_one_rejected(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        _set_env(monkeypatch, MEMORY_RECENT_ROUNDS=value)
        with pytest.raises(ValidationError):
            _load()

    @pytest.mark.parametrize("value", ["0", "-1"])
    def test_compress_every_rounds_below_one_rejected(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        _set_env(monkeypatch, MEMORY_COMPRESS_EVERY_ROUNDS=value)
        with pytest.raises(ValidationError):
            _load()


class TestSettingsMissingRequired:
    @pytest.mark.parametrize(
        "missing",
        [
            "LLM_BASE_URL",
            "LLM_API_KEY",
            "COORDINATOR_MODEL",
            "WEB_SEARCH_MODEL",
            "REPORT_MODEL",
            "MEMORY_DATA_DIR",
            "TAVILY_API_KEY",
        ],
    )
    def test_missing_required_field_raises(
        self, monkeypatch: pytest.MonkeyPatch, missing: str
    ) -> None:
        _set_env(monkeypatch, **{missing: None})
        with pytest.raises(ValidationError):
            _load()
