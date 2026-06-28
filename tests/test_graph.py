import json
from typing import Any

import pytest
from pydantic import Field

from research_agent.agents.coordinator import (
    CoordinatorAgent,
    CoordinatorDecisionError,
)
from research_agent.agents.sub_agent import DispatchContext, SubAgent
from research_agent.dto import Finding, Report
from research_agent.graph.build import build_graph
from research_agent.graph.response import assemble_response
from research_agent.graph.state import ResearchState
from research_agent.llm import LLMClient, Message


class _ScriptedLLM(LLMClient):
    """Returns canned JSON decisions, one per coordinator round."""

    replies: list[str] = Field(default_factory=list)
    calls: int = 0

    async def complete(self, messages: list[Message], model: str) -> str:
        reply = self.replies[self.calls]
        self.calls += 1
        return reply


class _StubSearch(SubAgent):
    name: str = "web_search"
    description: str = "search"

    async def run(self, task: str, context: DispatchContext) -> dict[str, Any]:
        return {
            "findings": [
                Finding(
                    summary=f"summary:{task}",
                    source_title=task,
                    source_url="https://e.example",
                )
            ]
        }


class _StubReport(SubAgent):
    name: str = "report"
    description: str = "report"

    async def run(self, task: str, context: DispatchContext) -> dict[str, Any]:
        return {
            "report": Report(html=f"<p>{len(context.findings)} findings</p>")
        }


class _FailingSearch(SubAgent):
    name: str = "web_search"
    description: str = "search"

    async def run(self, task: str, context: DispatchContext) -> dict[str, Any]:
        raise RuntimeError("search backend unreachable")


def _decision(
    message: str = "",
    dispatch: list[dict[str, str]] | None = None,
    done: bool = False,
) -> str:
    return json.dumps(
        {"message": message, "dispatch": dispatch or [], "done": done}
    )


def _coordinator(*replies: str) -> CoordinatorAgent:
    return CoordinatorAgent(
        llm=_ScriptedLLM(replies=list(replies)),
        model="coord",
        catalog={"web_search": "search", "report": "report"},
    )


def _registry(
    search: SubAgent | None = None, report: SubAgent | None = None
) -> dict[str, SubAgent]:
    return {
        "web_search": search or _StubSearch(),
        "report": report or _StubReport(),
    }


async def _run(graph: Any, query: str = "q") -> ResearchState:
    result = await graph.ainvoke(ResearchState(query=query, session_id="s"))
    return ResearchState.model_validate(result)


class TestResearchFlow:
    async def test_search_then_report_then_done(self) -> None:
        coordinator = _coordinator(
            _decision(
                "searching",
                [{"sub_agent": "web_search", "task": "topic"}],
            ),
            _decision("reporting", [{"sub_agent": "report", "task": "go"}]),
            _decision("here is the answer", done=True),
        )
        graph = build_graph(coordinator, _registry(), max_rounds=5)

        state = await _run(graph)

        assert len(state.findings) == 1
        assert state.report is not None
        reply = assemble_response(state)
        assert "here is the answer" in reply
        assert state.report.html in reply

    async def test_text_only_reply(self) -> None:
        coordinator = _coordinator(_decision("just a chat reply", done=True))
        graph = build_graph(coordinator, _registry(), max_rounds=5)

        state = await _run(graph)

        assert state.findings == []
        assert state.report is None
        assert assemble_response(state) == "just a chat reply"


class TestParallelDispatch:
    async def test_parallel_findings_merge_via_reducer(self) -> None:
        coordinator = _coordinator(
            _decision(
                "searching",
                [
                    {"sub_agent": "web_search", "task": "alpha"},
                    {"sub_agent": "web_search", "task": "beta"},
                ],
            ),
            _decision("done", done=True),
        )
        graph = build_graph(coordinator, _registry(), max_rounds=5)

        state = await _run(graph)

        assert {finding.source_title for finding in state.findings} == {
            "alpha",
            "beta",
        }


class TestRoundLimit:
    async def test_stops_at_max_rounds(self) -> None:
        # Coordinator never sets done; the cap must end the loop.
        coordinator = _coordinator(
            _decision("r0", [{"sub_agent": "web_search", "task": "a"}]),
            _decision("r1", [{"sub_agent": "web_search", "task": "b"}]),
        )
        graph = build_graph(coordinator, _registry(), max_rounds=2)

        state = await _run(graph)

        assert state.round_index == 2
        # Second round's dispatch is cut off by the cap, so only the first
        # round's search ran.
        assert len(state.findings) == 1


class TestSubAgentFailure:
    async def test_infrastructure_failure_propagates(self) -> None:
        coordinator = _coordinator(
            _decision("searching", [{"sub_agent": "web_search", "task": "a"}]),
        )
        graph = build_graph(
            coordinator, _registry(search=_FailingSearch()), max_rounds=5
        )

        with pytest.raises(RuntimeError, match="search backend unreachable"):
            await _run(graph)

    async def test_unknown_sub_agent_raises(self) -> None:
        coordinator = _coordinator(
            _decision("searching", [{"sub_agent": "ghost", "task": "a"}]),
        )
        graph = build_graph(coordinator, _registry(), max_rounds=5)

        with pytest.raises(CoordinatorDecisionError, match="ghost"):
            await _run(graph)
