from pydantic import BaseModel, Field


class Finding(BaseModel):
    """A single piece of researched information with its source."""

    summary: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: str = Field(min_length=1)


class Findings(BaseModel):
    """Fixed structured result the web search agent returns.

    Shape stays stable regardless of whether the search produced anything:
    no results means ``items`` is empty, not a different type.
    """

    items: list[Finding] = Field(default_factory=list)


class Report(BaseModel):
    """A standalone HTML report produced for a query."""

    html: str = Field(min_length=1)


class Round(BaseModel):
    """One query/response turn of a session's chat history."""

    query: str = Field(min_length=1)
    response: str = Field(min_length=1)
