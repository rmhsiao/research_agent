import json

from pydantic import BaseModel, Field, ValidationError

from research_agent.agents.base import BaseAgent
from research_agent.dto import Finding, Round
from research_agent.llm import LLMClient, Message


class DispatchItem(BaseModel):
    """One sub-agent task the coordinator wants to run this round."""

    sub_agent: str = Field(min_length=1)
    task: str = Field(min_length=1)


class CoordinatorDecision(BaseModel):
    """One round's structured decision from the coordinator.

    ``message`` is the text shown to the user, ``dispatch`` the sub-agent
    tasks to run this round, and ``done`` whether the research flow should end.
    """

    message: str = ""
    dispatch: list[DispatchItem] = Field(default_factory=list)
    done: bool = False


class CoordinatorDecisionError(Exception):
    """Raised when the coordinator LLM output is not a valid decision.

    A coordinator that cannot produce a decision is a real failure, not a
    state to silently degrade into an empty or default decision.
    """


_SYSTEM_PROMPT = (
    "You are the coordinator of a research system. Each round you decide what "
    "to do next and reply with ONLY a JSON object of this exact shape:\n"
    '{{"message": "<text for the user>", '
    '"dispatch": [{{"sub_agent": "<name>", "task": "<instruction>"}}], '
    '"done": <true|false>}}\n'
    "Available sub-agents:\n"
    "{catalog}\n"
    "Dispatch web_search to gather information for the query, then dispatch "
    "the report sub-agent to turn the gathered findings into the final HTML "
    "report. Set done=true once the query is answered (leave dispatch empty "
    "that round); set done=false on any round where you dispatch tasks. Reply "
    "with raw JSON only — no code fences and no text outside the object."
)


class CoordinatorAgent(BaseAgent):
    """Per-round decision maker driving the research flow.

    Given the query, recent conversation and findings gathered so far, it asks
    ``model`` for a structured decision: text for the user, sub-agent tasks to
    dispatch, and whether to stop. The LLM picks sub-agents by the name and
    description in ``catalog``. Invalid JSON raises rather than degrading.
    """

    name: str = "coordinator"
    description: str = (
        "Decide each round what to do next and dispatch sub-agents."
    )
    llm: LLMClient
    model: str
    catalog: dict[str, str]

    async def decide(
        self,
        query: str,
        history: list[Round],
        findings: list[Finding],
        round_index: int,
        max_rounds: int,
    ) -> CoordinatorDecision:
        raw = await self.llm.complete(
            self._messages(query, history, findings, round_index, max_rounds),
            model=self.model,
        )
        try:
            return CoordinatorDecision.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as error:
            raise CoordinatorDecisionError(
                f"Coordinator returned an invalid decision: {raw!r}"
            ) from error

    def _messages(
        self,
        query: str,
        history: list[Round],
        findings: list[Finding],
        round_index: int,
        max_rounds: int,
    ) -> list[Message]:
        catalog = "\n".join(
            f"- {name}: {description}"
            for name, description in self.catalog.items()
        )
        system = _SYSTEM_PROMPT.format(catalog=catalog)
        return [
            Message(role="system", content=system),
            Message(
                role="user",
                content=self._context(
                    query, history, findings, round_index, max_rounds
                ),
            ),
        ]

    def _context(
        self,
        query: str,
        history: list[Round],
        findings: list[Finding],
        round_index: int,
        max_rounds: int,
    ) -> str:
        past = "\n".join(
            f"- Q: `{round_.query}`\n- A: `{round_.response}`"
            for round_ in history
        )
        gathered = "\n".join(
            f"- {finding.source_title}: {finding.summary}"
            for finding in findings
        )
        return (
            f"<query>{query}</query>\n"
            f"<round>{round_index + 1} of at most {max_rounds}</round>\n"
            f"<history>\n{past or 'none yet'}\n</history>\n"
            f"<findings>\n{gathered or 'none yet'}\n</findings>"
        )
