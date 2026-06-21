import asyncio

from pydantic import BaseModel

from research_agent.dto import Finding, Findings
from research_agent.llm import LLMClient, Message
from research_agent.search import SearchClient, SearchResult

_SYSTEM_PROMPT = (
    "You summarize a single web search result for a research query. "
    "Given the query and the source content, write a concise summary of how "
    "this source addresses the query. Use only the provided content; do not "
    "add facts. Respond with the summary text only."
)


class WebSearchAgent(BaseModel):
    """Query -> backend search -> per-result LLM summary -> ``Findings``.

    Returns a fixed-shape ``Findings`` regardless of hit count: no results
    yields empty ``items`` rather than a different type or fabricated sources.
    Backend errors propagate (raised by the search client), so the caller can
    distinguish "search broke" from "found nothing".
    """

    search_client: SearchClient
    llm: LLMClient
    model: str

    async def run(self, query: str) -> Findings:
        results = await self.search_client.search(query)
        if not results:
            return Findings(items=[])
        findings = await asyncio.gather(
            *(self._summarize(query, result) for result in results)
        )
        return Findings(items=list(findings))

    async def _summarize(self, query: str, result: SearchResult) -> Finding:
        prompt = f"Query: {query}\n\nSource content:\n{result.content}"
        summary = await self.llm.complete(
            [
                Message(role="system", content=_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ],
            model=self.model,
        )
        return Finding(
            summary=summary,
            snippets=[result.content] if result.content else [],
            source_title=result.title,
            source_url=result.url,
        )
