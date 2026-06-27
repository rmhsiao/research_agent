from pydantic import Field

from research_agent.agents.report_generate import ReportGenerateAgent
from research_agent.agents.sub_agent import (
    DispatchContext,
    ReportSubAgent,
    WebSearchSubAgent,
    build_sub_agent_registry,
)
from research_agent.agents.web_search import WebSearchAgent
from research_agent.dto import Finding
from research_agent.llm import LLMClient, Message
from research_agent.search import SearchClient, SearchResult


class _StubSearchClient(SearchClient):
    results: list[SearchResult] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)

    async def search(self, query: str) -> list[SearchResult]:
        self.queries.append(query)
        return self.results


class _StubLLM(LLMClient):
    reply: str = "text"

    async def complete(self, messages: list[Message], model: str) -> str:
        return self.reply


def _web_search_agent(search: SearchClient) -> WebSearchAgent:
    return WebSearchAgent(
        search_client=search, llm=_StubLLM(reply="summary"), model="m"
    )


def _report_agent() -> ReportGenerateAgent:
    return ReportGenerateAgent(llm=_StubLLM(reply="<p>answer</p>"), model="m")


class TestRegistry:
    def test_keyed_by_name(self) -> None:
        registry = build_sub_agent_registry(
            _web_search_agent(_StubSearchClient()), _report_agent()
        )

        assert set(registry) == {"web_search", "report"}
        assert isinstance(registry["web_search"], WebSearchSubAgent)
        assert isinstance(registry["report"], ReportSubAgent)


class TestWebSearchSubAgent:
    async def test_runs_task_as_query_and_writes_findings(self) -> None:
        search = _StubSearchClient(
            results=[
                SearchResult(title="T", url="https://e.example", content="body")
            ]
        )
        sub_agent = WebSearchSubAgent(agent=_web_search_agent(search))

        update = await sub_agent.run(
            "everest height", DispatchContext(query="original")
        )

        assert search.queries == ["everest height"]
        assert list(update) == ["findings"]
        assert update["findings"][0].source_title == "T"


class TestReportSubAgent:
    async def test_reports_from_context_findings_and_query(self) -> None:
        sub_agent = ReportSubAgent(agent=_report_agent())
        context = DispatchContext(
            query="how tall is Everest",
            findings=[
                Finding(
                    summary="8849 m",
                    source_title="Everest facts",
                    source_url="https://e.example",
                )
            ],
        )

        update = await sub_agent.run("write it up", context)

        assert list(update) == ["report"]
        html = update["report"].html
        assert "how tall is Everest" in html
        assert "Everest facts" in html

    async def test_empty_findings_yields_no_information_report(self) -> None:
        sub_agent = ReportSubAgent(agent=_report_agent())

        update = await sub_agent.run("write it up", DispatchContext(query="q"))

        assert "No relevant information" in update["report"].html
