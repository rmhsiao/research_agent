from typing import Annotated

from pydantic import BaseModel, Field

from research_agent.dto import Findings, Report, Round


def merge_findings(left: Findings, right: Findings) -> Findings:
    """Reducer that concatenates findings from parallel web_search branches.

    Each fanned-out branch writes its own ``Findings``; this merges them into
    one accumulated set so no branch's results overwrite another's.
    """
    return Findings(items=[*left.items, *right.items])


class GraphState(BaseModel):
    """Shared state the coordinator graph passes between nodes.

    ``history`` carries the recent session rounds read before the run so the
    coordinator can plan in light of the ongoing conversation. ``findings``
    accumulates across parallel ``web_search`` branches via ``merge_findings``.
    """

    query: str
    session_id: str
    history: list[Round] = Field(default_factory=list)
    subqueries: list[str] = Field(default_factory=list)
    findings: Annotated[Findings, merge_findings] = Field(
        default_factory=Findings
    )
    report: Report | None = None
