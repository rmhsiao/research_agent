from research_agent.graph.state import ResearchState


def assemble_response(state: ResearchState) -> str:
    """Build the user-facing reply from a finished flow's final state.

    The coordinator's text leads; when this flow produced an HTML report, it is
    appended. The coordinator is the conversational face, the report the
    artifact it presents.
    """
    parts: list[str] = []
    if state.decision is not None and state.decision.message:
        parts.append(state.decision.message)
    if state.report is not None:
        parts.append(state.report.html)
    return "\n\n".join(parts)
