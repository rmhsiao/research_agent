from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr, SecretStr
from tavily import AsyncTavilyClient

from research_agent.config import Settings


class SearchResult(BaseModel):
    """One raw hit from the search backend, before any summarization."""

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    content: str = Field(default="")


class SearchClient(BaseModel, ABC):
    """Thin seam over a web search backend.

    ``search`` is async because it is a network call running inside the async
    graph/agents. Backend errors propagate; a query with no hits returns an
    empty list, so callers can tell "search failed" from "found nothing".
    """

    @abstractmethod
    async def search(self, query: str) -> list[SearchResult]: ...


class TavilySearchClient(SearchClient):
    """``SearchClient`` backed by Tavily."""

    api_key: SecretStr

    _client: AsyncTavilyClient = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._client = AsyncTavilyClient(self.api_key.get_secret_value())

    async def search(self, query: str) -> list[SearchResult]:
        response = await self._client.search(query)
        return [
            SearchResult(
                title=hit["title"],
                url=hit["url"],
                content=hit.get("content", ""),
            )
            for hit in response["results"]
        ]


def build_search_client(settings: Settings) -> SearchClient:
    return TavilySearchClient(api_key=settings.tavily_api_key)
