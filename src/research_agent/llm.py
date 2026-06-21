from typing import Any, Literal, Protocol, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, PrivateAttr, SecretStr

from research_agent.config import Settings


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMClient(Protocol):
    """Thin seam over an LLM backend.

    Kept deliberately minimal so the LLM provider/endpoint can be swapped
    without touching agents. The model id is chosen per call, letting each
    agent pick its own model from settings.
    """

    def complete(self, messages: list[Message], model: str) -> str: ...


class OpenAICompatibleLLMClient(BaseModel):
    """``LLMClient`` backed by any OpenAI-compatible endpoint."""

    base_url: str
    api_key: SecretStr

    _client: OpenAI = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key.get_secret_value(),
        )

    def complete(self, messages: list[Message], model: str) -> str:
        response = self._client.chat.completions.create(
            model=model,
            messages=cast(
                list[ChatCompletionMessageParam],
                [message.model_dump() for message in messages],
            ),
        )
        return response.choices[0].message.content or ""


def build_llm_client(settings: Settings) -> LLMClient:
    return OpenAICompatibleLLMClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )
