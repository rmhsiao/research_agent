from pathlib import Path

from pydantic import Field

from research_agent.agents.coordinator import CoordinatorAgent
from research_agent.agents.report_generate import ReportGenerateAgent
from research_agent.agents.web_search import WebSearchAgent
from research_agent.graph.runner import ResearchRunner
from research_agent.llm import LLMClient, Message
from research_agent.memory.session_store import FileSessionStore, SessionStore
from research_agent.search import SearchClient, SearchResult


class _ReplyLLM(LLMClient):
    reply: str = "ok"
    seen: list[Message] = Field(default_factory=list)

    async def complete(self, messages: list[Message], model: str) -> str:
        self.seen = list(messages)
        return self.reply


class _StubSearch(SearchClient):
    async def search(self, query: str) -> list[SearchResult]:
        return [SearchResult(title="T", url="https://e/x", content=query)]


def _make_runner(
    store: SessionStore, coordinator_llm: LLMClient | None = None
) -> ResearchRunner:
    return ResearchRunner(
        coordinator=CoordinatorAgent(
            llm=coordinator_llm or _ReplyLLM(reply="sub"), model="c"
        ),
        web_search=WebSearchAgent(
            search_client=_StubSearch(), llm=_ReplyLLM(reply="s"), model="w"
        ),
        report=ReportGenerateAgent(llm=_ReplyLLM(reply="<p>a</p>"), model="r"),
        store=store,
        recent_rounds=5,
    )


class TestResearchRunnerMemory:
    async def test_appends_round_after_research(self, tmp_path: Path) -> None:
        store = FileSessionStore(data_dir=tmp_path)
        runner = _make_runner(store)
        report = await runner.research("q1", "s1")
        history = store.get_history("s1")
        assert len(history) == 1
        assert history[0].query == "q1"
        assert history[0].response == report.html

    async def test_second_round_sees_prior_query(self, tmp_path: Path) -> None:
        store = FileSessionStore(data_dir=tmp_path)
        coordinator_llm = _ReplyLLM(reply="sub")
        runner = _make_runner(store, coordinator_llm=coordinator_llm)
        await runner.research("first question", "s1")
        await runner.research("second question", "s1")
        prompt = coordinator_llm.seen[-1].content
        assert "first question" in prompt
        assert "second question" in prompt

    async def test_sessions_are_isolated(self, tmp_path: Path) -> None:
        store = FileSessionStore(data_dir=tmp_path)
        runner = _make_runner(store)
        await runner.research("q-a", "session-a")
        await runner.research("q-b", "session-b")
        assert [r.query for r in store.get_history("session-a")] == ["q-a"]
        assert [r.query for r in store.get_history("session-b")] == ["q-b"]
