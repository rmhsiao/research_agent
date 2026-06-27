from typing import Any

import pytest
from langgraph.graph.state import CompiledStateGraph

from research_agent.agents.coordinator import CoordinatorAgent
from research_agent.agents.report_generate import ReportGenerateAgent
from research_agent.agents.web_search import WebSearchAgent
from research_agent.dto import Report
from research_agent.graph.build import build_research_graph
from research_agent.graph.state import GraphState
from research_agent.llm import LLMClient, Message
from research_agent.search import SearchClient, SearchResult


class _ReplyLLM(LLMClient):
    reply: str = "ok"

    async def complete(self, messages: list[Message], model: str) -> str:
        return self.reply


class _StubSearch(SearchClient):
    hits: bool = True
    error: str | None = None

    async def search(self, query: str) -> list[SearchResult]:
        if self.error is not None:
            raise RuntimeError(self.error)
        if not self.hits:
            return []
        return [
            SearchResult(
                title=f"T:{query}", url=f"https://e/{query}", content=query
            )
        ]


def _make_graph(
    *,
    subqueries: str,
    search: SearchClient,
    report_body: str = "<p>answer</p>",
) -> CompiledStateGraph[GraphState, Any, Any, Any]:
    return build_research_graph(
        CoordinatorAgent(llm=_ReplyLLM(reply=subqueries), model="c"),
        WebSearchAgent(
            search_client=search, llm=_ReplyLLM(reply="sum"), model="w"
        ),
        ReportGenerateAgent(llm=_ReplyLLM(reply=report_body), model="r"),
    )


async def _run(
    graph: CompiledStateGraph[GraphState, Any, Any, Any], query: str = "q"
) -> dict[str, Any]:
    result: dict[str, Any] = await graph.ainvoke(
        {"query": query, "session_id": "s1", "history": []}
    )
    return result


class TestResearchGraphPass:
    async def test_full_flow_decomposes_searches_merges_reports(self) -> None:
        graph = _make_graph(
            subqueries="alpha\nbeta\ngamma", search=_StubSearch()
        )
        result = await _run(graph, "big question")
        assert result["subqueries"] == ["alpha", "beta", "gamma"]
        assert len(result["findings"].items) == 3
        assert isinstance(result["report"], Report)
        assert "<p>answer</p>" in result["report"].html

    async def test_parallel_branch_findings_all_merged(self) -> None:
        graph = _make_graph(
            subqueries="alpha\nbeta\ngamma", search=_StubSearch()
        )
        result = await _run(graph)
        urls = {item.source_url for item in result["findings"].items}
        assert urls == {
            "https://e/alpha",
            "https://e/beta",
            "https://e/gamma",
        }

    async def test_single_subquery(self) -> None:
        graph = _make_graph(subqueries="only one", search=_StubSearch())
        result = await _run(graph)
        assert result["subqueries"] == ["only one"]
        assert len(result["findings"].items) == 1

    async def test_no_hits_reports_empty(self) -> None:
        graph = _make_graph(
            subqueries="alpha\nbeta", search=_StubSearch(hits=False)
        )
        result = await _run(graph)
        assert result["findings"].items == []
        assert "No relevant information" in result["report"].html


class TestResearchGraphError:
    async def test_search_backend_failure_propagates(self) -> None:
        graph = _make_graph(
            subqueries="alpha\nbeta", search=_StubSearch(error="tavily down")
        )
        with pytest.raises(RuntimeError, match="tavily down"):
            await _run(graph)
