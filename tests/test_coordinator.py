from pydantic import Field

from research_agent.agents.coordinator import _MAX_SUBQUERIES, CoordinatorAgent
from research_agent.dto import Round
from research_agent.llm import LLMClient, Message


class _ReplyLLM(LLMClient):
    reply: str = "ok"
    seen: list[Message] = Field(default_factory=list)

    async def complete(self, messages: list[Message], model: str) -> str:
        self.seen = list(messages)
        return self.reply


def _make_agent(reply: str) -> CoordinatorAgent:
    return CoordinatorAgent(
        llm=_ReplyLLM(reply=reply), model="coordinator-model"
    )


class TestCoordinatorPlan:
    async def test_splits_reply_into_subqueries(self) -> None:
        agent = _make_agent("alpha\nbeta\ngamma")
        assert await agent.plan("q", []) == ["alpha", "beta", "gamma"]

    async def test_single_line_yields_single_subquery(self) -> None:
        agent = _make_agent("just one focused query")
        assert await agent.plan("q", []) == ["just one focused query"]

    async def test_blank_lines_dropped(self) -> None:
        agent = _make_agent("alpha\n\n  \nbeta")
        assert await agent.plan("q", []) == ["alpha", "beta"]

    async def test_caps_at_max(self) -> None:
        reply = "\n".join(f"sub-{i}" for i in range(_MAX_SUBQUERIES + 5))
        agent = _make_agent(reply)
        assert len(await agent.plan("q", [])) == _MAX_SUBQUERIES


class TestCoordinatorFallback:
    async def test_empty_reply_falls_back_to_query(self) -> None:
        agent = _make_agent("   \n  \n")
        assert await agent.plan("original query", []) == ["original query"]


class TestCoordinatorHistory:
    async def test_prior_queries_passed_into_prompt(self) -> None:
        llm = _ReplyLLM(reply="x")
        agent = CoordinatorAgent(llm=llm, model="coordinator-model")
        history = [Round(query="earlier ask", response="<p>r</p>")]
        await agent.plan("current ask", history)
        prompt = llm.seen[-1].content
        assert "earlier ask" in prompt
        assert "current ask" in prompt
