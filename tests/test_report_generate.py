from research_agent.agents.report_generate import ReportGenerateAgent
from research_agent.dto import Finding, Findings
from research_agent.llm import LLMClient, Message


class _StubLLMClient(LLMClient):
    reply: str = "<p>answer</p>"
    calls: int = 0

    async def complete(self, messages: list[Message], model: str) -> str:
        self.calls += 1
        return self.reply


def _make_agent(llm: LLMClient) -> ReportGenerateAgent:
    return ReportGenerateAgent(llm=llm, model="report-model")


class TestReportGeneratePass:
    async def test_renders_html_with_answer_and_sources(self) -> None:
        findings = Findings(
            items=[
                Finding(
                    summary="s1",
                    snippets=["p1"],
                    source_title="First",
                    source_url="https://a.example",
                ),
                Finding(
                    summary="s2",
                    snippets=["p2"],
                    source_title="Second",
                    source_url="https://b.example",
                ),
            ]
        )
        report = await _make_agent(
            _StubLLMClient(reply="<p>the answer</p>")
        ).run("q", findings)

        html = report.html
        assert html.startswith("<!DOCTYPE html>")
        assert "<p>the answer</p>" in html
        assert '<a href="https://a.example">First</a>' in html
        assert '<a href="https://b.example">Second</a>' in html

    async def test_escapes_query_in_title_and_heading(self) -> None:
        findings = Findings(
            items=[
                Finding(
                    summary="s",
                    source_title="T",
                    source_url="https://x.example",
                )
            ]
        )
        report = await _make_agent(_StubLLMClient()).run("a <b> & c", findings)
        assert "a &lt;b&gt; &amp; c" in report.html
        assert "<b>" not in report.html


class TestReportGenerateEmpty:
    async def test_empty_findings_report_no_information_without_llm(
        self,
    ) -> None:
        llm = _StubLLMClient()
        report = await _make_agent(llm).run("q", Findings(items=[]))

        assert llm.calls == 0
        assert "No relevant information was found" in report.html
        assert report.html.startswith("<!DOCTYPE html>")
