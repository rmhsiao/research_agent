from html import escape

from pydantic import BaseModel

from research_agent.dto import Findings, Report
from research_agent.llm import LLMClient, Message

_SYSTEM_PROMPT = (
    "You write the body of a research report answering a query, based only on "
    "the provided findings. Synthesize them into a clear answer; do not add "
    "facts beyond the findings and do not invent sources. Respond with HTML "
    "body content only (headings, paragraphs, lists) — no <html>, <head>, or "
    "<body> tags and no surrounding code fences."
)

_EMPTY_BODY = "  <p>No relevant information was found for this query.</p>"


class ReportGenerateAgent(BaseModel):
    """``Findings`` + query -> a standalone HTML ``Report``.

    Empty findings short-circuit to a fixed "no information" report without an
    LLM call, so nothing is fabricated. The answer body is LLM-written from the
    findings; the sources list is rendered deterministically from them so it
    can never cite a source that was not searched. HTML is the only output
    format and is wired in here directly — no format abstraction until a second
    one exists.
    """

    llm: LLMClient
    model: str

    async def run(self, query: str, findings: Findings) -> Report:
        if not findings.items:
            return Report(html=self._document(query, _EMPTY_BODY))
        answer = await self.llm.complete(
            [
                Message(role="system", content=_SYSTEM_PROMPT),
                Message(role="user", content=self._prompt(query, findings)),
            ],
            model=self.model,
        )
        sources = "\n".join(
            f'    <li><a href="{escape(item.source_url, quote=True)}">'
            f"{escape(item.source_title)}</a></li>"
            for item in findings.items
        )
        # The LLM body is embedded as-is so a report can carry rich, interactive
        # HTML. It is deliberately not sanitized; the findings it is built from
        # come from untrusted web content, so a later guard must screen the
        # output for malicious code before this is exposed to real browsers.
        # TODO: add malicious-code detection over the generated report.
        body = f"  {answer}\n  <h2>Sources</h2>\n  <ul>\n{sources}\n  </ul>"
        return Report(html=self._document(query, body))

    def _prompt(self, query: str, findings: Findings) -> str:
        blocks = []
        for index, item in enumerate(findings.items, start=1):
            passages = "\n".join(item.snippets)
            blocks.append(
                f"[{index}] {item.source_title} ({item.source_url})\n"
                f"Summary: {item.summary}\n"
                f"Passages:\n{passages}"
            )
        return f"Query: {query}\n\nFindings:\n" + "\n\n".join(blocks)

    def _document(self, query: str, body: str) -> str:
        title = f"Research report: {escape(query)}"
        return (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '  <meta charset="utf-8">\n'
            f"  <title>{title}</title>\n"
            "</head>\n"
            "<body>\n"
            f"  <h1>{title}</h1>\n"
            f"{body}\n"
            "</body>\n"
            "</html>\n"
        )
