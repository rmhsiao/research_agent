from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from research_agent.agents.coordinator import CoordinatorAgent
from research_agent.agents.report_generate import ReportGenerateAgent
from research_agent.agents.web_search import WebSearchAgent
from research_agent.graph.state import GraphState


class _SearchTask(TypedDict):
    """Per-branch input a fanned-out ``web_search`` node gets via ``Send``."""

    subquery: str


def build_research_graph(
    coordinator: CoordinatorAgent,
    web_search: WebSearchAgent,
    report: ReportGenerateAgent,
) -> CompiledStateGraph[GraphState, Any, Any, Any]:
    """Wire the coordinator/web_search/report nodes into a compiled graph.

    ``coordinator`` plans subqueries; a conditional edge fans them out to
    parallel ``web_search`` branches via ``Send``, whose findings merge through
    the state reducer; ``report`` then renders the accumulated findings. This
    skeleton runs one search round (``## 7`` adds the replan loop).
    """

    async def coordinator_node(state: GraphState) -> dict[str, Any]:
        subqueries = await coordinator.plan(state.query, state.history)
        return {"subqueries": subqueries}

    def fan_out(state: GraphState) -> list[Send]:
        return [Send("web_search", {"subquery": q}) for q in state.subqueries]

    async def web_search_node(task: _SearchTask) -> dict[str, Any]:
        return {"findings": await web_search.run(task["subquery"])}

    async def report_node(state: GraphState) -> dict[str, Any]:
        return {"report": await report.run(state.query, state.findings)}

    builder = StateGraph(GraphState)
    builder.add_node("coordinator", coordinator_node)
    # add_node is typed for nodes over the graph state; a fanned-out node takes
    # its own per-branch input schema, which langgraph supports at runtime but
    # cannot express in this overload.
    builder.add_node("web_search", web_search_node)  # type: ignore[arg-type]
    builder.add_node("report", report_node)
    builder.add_edge(START, "coordinator")
    builder.add_conditional_edges("coordinator", fan_out, ["web_search"])
    builder.add_edge("web_search", "report")
    builder.add_edge("report", END)
    return builder.compile()
