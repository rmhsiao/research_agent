from research_agent.dto import Round
from research_agent.memory.session_store import SessionState


def assemble_context(state: SessionState, recent_rounds: int) -> list[Round]:
    """Return the most recent ``recent_rounds`` rounds for the LLM context.

    Long-term summary inclusion is deferred to async compression (``## 10``).
    """
    return state.rounds[-recent_rounds:]
