from typing import Any

from pydantic import BaseModel, Field, PrivateAttr

from research_agent.agents.coordinator import CoordinatorAgent
from research_agent.agents.report_generate import ReportGenerateAgent
from research_agent.agents.web_search import WebSearchAgent
from research_agent.config import Settings
from research_agent.dto import Report, Round
from research_agent.graph.build import build_research_graph
from research_agent.llm import build_llm_client
from research_agent.memory.context import assemble_context
from research_agent.memory.session_store import (
    SessionStore,
    build_session_store,
)
from research_agent.search import build_search_client


class ResearchRunner(BaseModel):
    """Runs one research turn for a session: read memory, run graph, persist.

    Memory lives here rather than inside the graph so the graph stays the pure
    research flow. Recent rounds are read before the run and fed to the
    coordinator; the resulting round is appended to the full history after.
    """

    coordinator: CoordinatorAgent
    web_search: WebSearchAgent
    report: ReportGenerateAgent
    store: SessionStore
    recent_rounds: int = Field(ge=1)

    _graph: Any = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._graph = build_research_graph(
            self.coordinator, self.web_search, self.report
        )

    async def research(self, query: str, session_id: str) -> Report:
        history = assemble_context(
            self.store.load(session_id), self.recent_rounds
        )
        result = await self._graph.ainvoke(
            {"query": query, "session_id": session_id, "history": history}
        )
        report: Report = result["report"]
        # Re-read before appending so a concurrent write isn't lost.
        state = self.store.load(session_id)
        state.rounds.append(Round(query=query, response=report.html))
        self.store.save(session_id, state)
        return report


def build_research_runner(settings: Settings) -> ResearchRunner:
    llm = build_llm_client(settings)
    search = build_search_client(settings)
    return ResearchRunner(
        coordinator=CoordinatorAgent(llm=llm, model=settings.coordinator_model),
        web_search=WebSearchAgent(
            search_client=search, llm=llm, model=settings.web_search_model
        ),
        report=ReportGenerateAgent(llm=llm, model=settings.report_model),
        store=build_session_store(settings),
        recent_rounds=settings.memory_recent_rounds,
    )
