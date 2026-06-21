from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError
from pytest_mock import MockerFixture

from research_agent.config import Settings
from research_agent.search import SearchResult, build_search_client


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


def _patch_tavily(mocker: MockerFixture, response: dict[str, Any]) -> Any:
    mock_class = mocker.patch("research_agent.search.AsyncTavilyClient")
    client = mock_class.return_value
    client.search = mocker.AsyncMock(return_value=response)
    return client


class TestSearchPass:
    async def test_maps_backend_hits_to_results(
        self, mocker: MockerFixture
    ) -> None:
        _patch_tavily(
            mocker,
            {
                "results": [
                    {
                        "title": "First",
                        "url": "https://a.example",
                        "content": "passage a",
                    },
                    {"title": "Second", "url": "https://b.example"},
                ]
            },
        )
        client = build_search_client(_make_settings())
        results = await client.search("query")
        assert results == [
            SearchResult(
                title="First", url="https://a.example", content="passage a"
            ),
            SearchResult(title="Second", url="https://b.example", content=""),
        ]


class TestSearchEmpty:
    async def test_no_hits_returns_empty_list(
        self, mocker: MockerFixture
    ) -> None:
        client = _patch_tavily(mocker, {"results": []})
        results = await build_search_client(_make_settings()).search("query")
        assert results == []
        client.search.assert_awaited_once_with("query")


class TestSearchError:
    async def test_backend_error_propagates(
        self, mocker: MockerFixture
    ) -> None:
        client = _patch_tavily(mocker, {"results": []})
        client.search.side_effect = RuntimeError("tavily down")
        with pytest.raises(RuntimeError, match="tavily down"):
            await build_search_client(_make_settings()).search("query")


class TestSearchResultValidation:
    @pytest.mark.parametrize("field", ["title", "url"])
    def test_blank_required_field_rejected(self, field: str) -> None:
        kwargs = {"title": "t", "url": "https://x.example"}
        kwargs[field] = ""
        with pytest.raises(ValidationError):
            SearchResult(**kwargs)
