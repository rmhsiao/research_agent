import json

import pytest
from pydantic import Field

from research_agent.agents.base import BaseAgent
from research_agent.agents.coordinator import (
    CoordinatorAgent,
    CoordinatorDecisionError,
)
from research_agent.dto import Finding, Round
from research_agent.llm import LLMClient, Message


class _StubLLM(LLMClient):
    """Returns a fixed reply and records the messages it was called with."""

    reply: str = ""
    seen: list[Message] = Field(default_factory=list)

    async def complete(self, messages: list[Message], model: str) -> str:
        self.seen = messages
        return self.reply


def _make_coordinator(reply: str) -> CoordinatorAgent:
    return CoordinatorAgent(
        llm=_StubLLM(reply=reply),
        model="coord-model",
        catalog={"web_search": "search the web", "report": "write report"},
    )


class TestCoordinatorDecide:
    async def test_parses_dispatch_decision(self) -> None:
        coordinator = _make_coordinator(
            json.dumps(
                {
                    "message": "looking into it",
                    "dispatch": [{"sub_agent": "web_search", "task": "x"}],
                    "done": False,
                }
            )
        )

        decision = await coordinator.decide(
            query="q",
            history=[],
            findings=[],
            round_index=0,
            max_rounds=5,
        )

        assert decision.message == "looking into it"
        assert decision.dispatch[0].sub_agent == "web_search"
        assert decision.dispatch[0].task == "x"
        assert decision.done is False

    async def test_parses_done_decision_without_dispatch(self) -> None:
        coordinator = _make_coordinator(
            json.dumps({"message": "all set", "dispatch": [], "done": True})
        )

        decision = await coordinator.decide(
            query="q", history=[], findings=[], round_index=0, max_rounds=5
        )

        assert decision.done is True
        assert decision.dispatch == []


class TestCoordinatorPrompt:
    async def test_prompt_carries_catalog_query_and_findings(self) -> None:
        coordinator = _make_coordinator(json.dumps({"done": True}))

        await coordinator.decide(
            query="how tall is Everest",
            history=[Round(query="hi", response="hello")],
            findings=[
                Finding(
                    summary="8849 m",
                    source_title="Everest facts",
                    source_url="https://e.example",
                )
            ],
            round_index=1,
            max_rounds=3,
        )

        system, user = coordinator.llm.seen  # type: ignore[attr-defined]
        assert "web_search" in system.content
        assert "report" in system.content
        assert "how tall is Everest" in user.content
        assert "Everest facts" in user.content
        assert "hello" in user.content

    async def test_context_uses_xml_like_tags(self) -> None:
        coordinator = _make_coordinator(json.dumps({"done": True}))

        await coordinator.decide(
            query="q",
            history=[Round(query="hi", response="hello")],
            findings=[],
            round_index=0,
            max_rounds=3,
        )

        _, user = coordinator.llm.seen  # type: ignore[attr-defined]
        assert "<query>q</query>" in user.content
        assert "<history>\n- Q: `hi`\n- A: `hello`\n</history>" in user.content
        assert "<findings>\nnone yet\n</findings>" in user.content


class TestCoordinatorIdentity:
    def test_is_a_base_agent(self) -> None:
        assert isinstance(_make_coordinator(""), BaseAgent)


class TestCoordinatorDecisionError:
    async def test_non_json_raises(self) -> None:
        coordinator = _make_coordinator("not json at all")

        with pytest.raises(CoordinatorDecisionError):
            await coordinator.decide(
                query="q",
                history=[],
                findings=[],
                round_index=0,
                max_rounds=5,
            )

    async def test_schema_invalid_raises(self) -> None:
        # dispatch item missing the required "task" field.
        coordinator = _make_coordinator(
            json.dumps({"dispatch": [{"sub_agent": "web_search"}]})
        )

        with pytest.raises(CoordinatorDecisionError):
            await coordinator.decide(
                query="q",
                history=[],
                findings=[],
                round_index=0,
                max_rounds=5,
            )
