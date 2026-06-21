import pytest
from pydantic import ValidationError

from research_agent.dto import Finding, Findings, Report, Round


def _finding() -> Finding:
    return Finding(
        summary="LangGraph models agents as a state graph.",
        snippets=["LangGraph lets you build stateful, multi-actor apps."],
        source_title="LangGraph docs",
        source_url="https://example.test/langgraph",
    )


class TestModelsValid:
    def test_finding_holds_summary_and_source(self) -> None:
        finding = _finding()
        assert finding.summary
        assert finding.source_title == "LangGraph docs"
        assert finding.source_url == "https://example.test/langgraph"

    def test_finding_allows_empty_snippets(self) -> None:
        finding = Finding(
            summary="summary",
            snippets=[],
            source_title="title",
            source_url="https://example.test",
        )
        assert finding.snippets == []

    def test_findings_default_to_empty(self) -> None:
        assert Findings().items == []

    def test_findings_carry_items(self) -> None:
        findings = Findings(items=[_finding()])
        assert len(findings.items) == 1

    def test_report_holds_html(self) -> None:
        assert Report(html="<h1>Report</h1>").html == "<h1>Report</h1>"

    def test_round_holds_query_and_response(self) -> None:
        round_ = Round(query="What is X?", response="<p>X is ...</p>")
        assert round_.query == "What is X?"
        assert round_.response == "<p>X is ...</p>"


class TestModelsValidation:
    @pytest.mark.parametrize(
        ("summary", "snippets", "source_title", "source_url"),
        [
            ("", ["snippet"], "title", "https://example.test"),
            ("summary", [""], "title", "https://example.test"),
            ("summary", ["snippet"], "", "https://example.test"),
            ("summary", ["snippet"], "title", ""),
        ],
    )
    def test_finding_rejects_empty_fields(
        self,
        summary: str,
        snippets: list[str],
        source_title: str,
        source_url: str,
    ) -> None:
        with pytest.raises(ValidationError):
            Finding(
                summary=summary,
                snippets=snippets,
                source_title=source_title,
                source_url=source_url,
            )

    def test_report_rejects_empty_html(self) -> None:
        with pytest.raises(ValidationError):
            Report(html="")

    @pytest.mark.parametrize(
        ("query", "response"),
        [("", "answer"), ("question", "")],
    )
    def test_round_rejects_empty_fields(
        self, query: str, response: str
    ) -> None:
        with pytest.raises(ValidationError):
            Round(query=query, response=response)
