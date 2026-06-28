from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from research_agent.agents.base import BaseAgent
from research_agent.agents.report_generate import ReportGenerateAgent
from research_agent.agents.web_search import WebSearchAgent
from research_agent.dto import Finding, Findings


class DispatchContext(BaseModel):
    """The shared flow state a sub-agent may read while running its task.

    Carries the original user query and the findings accumulated so far, so a
    sub-agent (e.g. report generation) can work from prior rounds' results
    without the sub-agents talking to each other.
    """

    query: str
    findings: list[Finding] = Field(default_factory=list)


class DispatchTask(BaseModel):
    """A single sub-agent invocation: which sub-agent, its task, its context.

    This is the payload the dispatch node fans out with one per task.
    """

    sub_agent: str = Field(min_length=1)
    task: str = Field(min_length=1)
    context: DispatchContext


class SubAgent(BaseAgent, ABC):
    """A coordinator-dispatchable unit, selected by ``name``/``description``.

    ``run`` returns a partial state update keyed by the concrete channel the
    sub-agent writes (``findings`` or ``report``), merged back into the flow
    state. Sub-agents never call each other; they only take a task from the
    coordinator and return their result.
    """

    @abstractmethod
    async def run(
        self, task: str, context: DispatchContext
    ) -> dict[str, Any]: ...


class WebSearchSubAgent(SubAgent):
    """Wraps ``WebSearchAgent``; writes its findings to the ``findings``
    channel."""

    name: str = "web_search"
    description: str = (
        "Search the web for a focused query and return summarized findings "
        "with their sources."
    )
    agent: WebSearchAgent

    async def run(self, task: str, context: DispatchContext) -> dict[str, Any]:
        findings = await self.agent.run(task)
        return {"findings": findings.items}


class ReportSubAgent(SubAgent):
    """Wraps ``ReportGenerateAgent``; writes its report to the ``report``
    channel.

    Renders the findings accumulated so far for the original query, so it is
    dispatched after search rather than given findings in its task text.
    """

    name: str = "report"
    description: str = (
        "Generate the final standalone HTML report from the findings gathered "
        "so far for the original query."
    )
    agent: ReportGenerateAgent

    async def run(self, task: str, context: DispatchContext) -> dict[str, Any]:
        report = await self.agent.run(
            context.query, Findings(items=context.findings)
        )
        return {"report": report}


def build_sub_agent_registry(
    web_search_agent: WebSearchAgent,
    report_agent: ReportGenerateAgent,
) -> dict[str, SubAgent]:
    sub_agents: list[SubAgent] = [
        WebSearchSubAgent(agent=web_search_agent),
        ReportSubAgent(agent=report_agent),
    ]
    return {sub_agent.name: sub_agent for sub_agent in sub_agents}
