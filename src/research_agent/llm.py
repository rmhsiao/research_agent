from abc import ABC, abstractmethod
from typing import Any, Literal, cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, PrivateAttr, SecretStr

from research_agent.config import Settings


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMClient(BaseModel, ABC):
    """Thin seam over an LLM backend.

    Methods are async because LLM calls are I/O-bound and run inside the
    async graph/API. The model id is chosen per call so each agent can pick
    its own model from settings. Kept minimal so the provider/endpoint can be
    swapped without touching agents.
    """

    @abstractmethod
    async def complete(self, messages: list[Message], model: str) -> str: ...


class OpenAICompatibleLLMClient(LLMClient):
    """``LLMClient`` backed by any OpenAI-compatible endpoint."""

    base_url: str
    api_key: SecretStr

    _client: AsyncOpenAI = PrivateAttr()

    def model_post_init(self, __context: Any) -> None:
        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key.get_secret_value(),
        )

    async def complete(self, messages: list[Message], model: str) -> str:
        response = await self._client.chat.completions.create(
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
