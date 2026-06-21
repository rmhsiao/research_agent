import pytest
from pydantic import Field

from research_agent.agents.web_search import WebSearchAgent
from research_agent.llm import LLMClient, Message
from research_agent.search import SearchClient, SearchResult


class _StubSearchClient(SearchClient):
    results: list[SearchResult] = Field(default_factory=list)
    error: str | None = None

    async def search(self, query: str) -> list[SearchResult]:
        if self.error is not None:
            raise RuntimeError(self.error)
        return self.results


class _StubLLMClient(LLMClient):
    reply: str = "summary"
    calls: int = 0

    async def complete(self, messages: list[Message], model: str) -> str:
        self.calls += 1
        return self.reply


def _make_agent(search_client: SearchClient, llm: LLMClient) -> WebSearchAgent:
    return WebSearchAgent(
        search_client=search_client, llm=llm, model="cheap-model"
    )


class TestWebSearchPass:
    async def test_returns_structured_findings_per_result(self) -> None:
        search = _StubSearchClient(
            results=[
                SearchResult(
                    title="First",
                    url="https://a.example",
                    content="passage a",
                ),
                SearchResult(
                    title="Second",
                    url="https://b.example",
                    content="passage b",
                ),
            ]
        )
        findings = await _make_agent(search, _StubLLMClient(reply="sum")).run(
            "q"
        )
        assert [item.source_url for item in findings.items] == [
            "https://a.example",
            "https://b.example",
        ]
        first = findings.items[0]
        assert first.summary == "sum"
        assert first.snippets == ["passage a"]
        assert first.source_title == "First"

    async def test_empty_content_yields_no_snippets(self) -> None:
        search = _StubSearchClient(
            results=[
                SearchResult(title="T", url="https://x.example", content="")
            ]
        )
        findings = await _make_agent(search, _StubLLMClient()).run("q")
        assert findings.items[0].snippets == []


class TestWebSearchEmpty:
    async def test_no_results_returns_empty_findings_without_llm(self) -> None:
        llm = _StubLLMClient()
        findings = await _make_agent(_StubSearchClient(results=[]), llm).run(
            "q"
        )
        assert findings.items == []
        assert llm.calls == 0


class TestWebSearchError:
    async def test_backend_error_propagates(self) -> None:
        search = _StubSearchClient(error="tavily down")
        with pytest.raises(RuntimeError, match="tavily down"):
            await _make_agent(search, _StubLLMClient()).run("q")
