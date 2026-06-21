from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import SecretStr
from pytest_mock import MockerFixture

from research_agent.config import Settings
from research_agent.llm import (
    LLMClient,
    Message,
    OpenAICompatibleLLMClient,
    build_llm_client,
)


def _make_settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        llm_base_url="https://llm.example/v1",
        llm_api_key=SecretStr("sk-secret"),
        coordinator_model="strong-model",
        web_search_model="cheap-model",
        report_model="cheap-model",
        memory_data_dir=Path("data/sessions"),
        tavily_api_key=SecretStr("tvly-secret"),
    )


def _completion(content: str | None) -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _patch_openai(
    mocker: MockerFixture, content: str | None = "answer"
) -> SimpleNamespace:
    mock_class = mocker.patch("research_agent.llm.AsyncOpenAI")
    mock_client = mock_class.return_value
    mock_client.chat.completions.create = mocker.AsyncMock(
        return_value=_completion(content)
    )
    return SimpleNamespace(klass=mock_class, client=mock_client)


class TestBuildLLMClient:
    def test_builds_openai_client_from_settings(
        self, mocker: MockerFixture
    ) -> None:
        mocks = _patch_openai(mocker)
        client = build_llm_client(_make_settings())
        assert isinstance(client, OpenAICompatibleLLMClient)
        mocks.klass.assert_called_once_with(
            base_url="https://llm.example/v1",
            api_key="sk-secret",
        )


class TestComplete:
    async def test_passes_model_and_messages_and_returns_content(
        self, mocker: MockerFixture
    ) -> None:
        mocks = _patch_openai(mocker, content="hello")
        client: LLMClient = build_llm_client(_make_settings())
        result = await client.complete(
            [Message(role="user", content="hi")], model="cheap-model"
        )
        assert result == "hello"
        mocks.client.chat.completions.create.assert_awaited_once_with(
            model="cheap-model",
            messages=[{"role": "user", "content": "hi"}],
        )

    async def test_empty_content_returns_empty_string(
        self, mocker: MockerFixture
    ) -> None:
        _patch_openai(mocker, content=None)
        client = build_llm_client(_make_settings())
        result = await client.complete(
            [Message(role="user", content="hi")], model="cheap-model"
        )
        assert result == ""


class TestCompleteError:
    async def test_backend_error_propagates(
        self, mocker: MockerFixture
    ) -> None:
        mocks = _patch_openai(mocker)
        mocks.client.chat.completions.create.side_effect = RuntimeError(
            "backend down"
        )
        client = build_llm_client(_make_settings())
        with pytest.raises(RuntimeError, match="backend down"):
            await client.complete(
                [Message(role="user", content="hi")], model="cheap-model"
            )
