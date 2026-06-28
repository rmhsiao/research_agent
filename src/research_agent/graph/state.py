from operator import add
from typing import Annotated

from pydantic import BaseModel, Field

from research_agent.agents.coordinator import CoordinatorDecision
from research_agent.dto import Finding, Report, Round


class ResearchState(BaseModel):
    """Shared state carried through one research flow.

    ``findings`` accumulates across rounds and parallel dispatch branches via
    an ``add`` reducer, so concurrent writes append instead of overwriting.
    ``decision`` holds the coordinator's current-round decision; ``round_index``
    counts completed coordinator rounds for the loop bound.
    """

    query: str
    session_id: str
    history: list[Round] = Field(default_factory=list)
    findings: Annotated[list[Finding], add] = Field(default_factory=list)
    decision: CoordinatorDecision | None = None
    round_index: int = 0
    report: Report | None = None
