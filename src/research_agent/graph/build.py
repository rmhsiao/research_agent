from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from research_agent.agents.coordinator import (
    CoordinatorAgent,
    CoordinatorDecisionError,
)
from research_agent.agents.sub_agent import (
    DispatchContext,
    DispatchTask,
    SubAgent,
)
from research_agent.graph.state import ResearchState


def build_graph(
    coordinator: CoordinatorAgent,
    registry: dict[str, SubAgent],
    max_rounds: int,
) -> CompiledStateGraph[ResearchState]:
    """Assemble the coordinator/dispatch loop graph.

    The flow loops ``coordinator → (dispatch | end) → coordinator``: each round
    the coordinator decides, and either fans tasks out to the generic dispatch
    node (one ``Send`` per task, run in parallel) or ends. It ends when the
    coordinator sets ``done`` or ``max_rounds`` coordinator rounds are reached,
    so it never loops forever.
    """

    async def coordinator_node(state: ResearchState) -> dict[str, Any]:
        decision = await coordinator.decide(
            query=state.query,
            history=state.history,
            findings=state.findings,
            round_index=state.round_index,
            max_rounds=max_rounds,
        )
        return {"decision": decision, "round_index": state.round_index + 1}

    def route(state: ResearchState) -> list[Send] | str:
        decision = state.decision
        if decision is None or decision.done:
            return END
        if state.round_index >= max_rounds or not decision.dispatch:
            return END
        context = DispatchContext(query=state.query, findings=state.findings)
        return [
            Send(
                "dispatch",
                DispatchTask(
                    sub_agent=item.sub_agent,
                    task=item.task,
                    context=context,
                ),
            )
            for item in decision.dispatch
        ]

    async def dispatch_node(state: DispatchTask) -> dict[str, Any]:
        try:
            sub_agent = registry[state.sub_agent]
        except KeyError as error:
            raise CoordinatorDecisionError(
                f"Unknown sub-agent: {state.sub_agent!r}"
            ) from error
        return await sub_agent.run(state.task, state.context)

    graph = StateGraph(ResearchState)
    graph.add_node("coordinator", coordinator_node)
    graph.add_node("dispatch", dispatch_node, input_schema=DispatchTask)
    graph.add_edge(START, "coordinator")
    graph.add_conditional_edges("coordinator", route, ["dispatch", END])
    graph.add_edge("dispatch", "coordinator")
    return graph.compile()
