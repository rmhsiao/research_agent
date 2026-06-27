from pydantic import BaseModel

from research_agent.dto import Round
from research_agent.llm import LLMClient, Message

_SYSTEM_PROMPT = (
    "You are a research coordinator. Break the research query into 1 to N "
    "focused web-search subqueries that together cover what is needed to "
    "answer it. If the query is already focused, return a single subquery. "
    "Take the earlier questions in the conversation into account. Respond "
    "with one subquery per line, no numbering and no other text."
)

# Cap fan-out width so one query can't spawn an unbounded number of searches.
_MAX_SUBQUERIES = 5


class CoordinatorAgent(BaseModel):
    """The decision brain that plans which searches to run for a query.

    Given the query and recent conversation, it returns the subqueries to
    search next. Order and direction of the research flow live here, not in
    the graph topology; the graph only executes what this plans.
    """

    llm: LLMClient
    model: str

    async def plan(self, query: str, history: list[Round]) -> list[str]:
        reply = await self.llm.complete(
            [
                Message(role="system", content=_SYSTEM_PROMPT),
                Message(role="user", content=self._prompt(query, history)),
            ],
            model=self.model,
        )
        subqueries = [
            line.strip() for line in reply.splitlines() if line.strip()
        ][:_MAX_SUBQUERIES]
        # Fall back to the original query so the flow always searches at least
        # once, even if the model returns nothing usable.
        return subqueries or [query]

    def _prompt(self, query: str, history: list[Round]) -> str:
        if not history:
            return f"Research query: {query}"
        prior = "\n".join(f"- {round.query}" for round in history)
        return f"Earlier questions:\n{prior}\n\nResearch query: {query}"
