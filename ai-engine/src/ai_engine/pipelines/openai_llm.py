"""OpenAI Chat Completions LLM component with streaming."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx
import structlog

from ai_engine.pipelines.base import LLMChunk, LLMComponent

logger = structlog.get_logger()


class OpenAILLM(LLMComponent):
    """OpenAI Chat Completions API for LLM responses."""

    def __init__(self, api_key: str, model: str = "gpt-4o", **kwargs) -> None:
        self._api_key = api_key
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        system_prompt: str = "",
    ) -> AsyncIterator[LLMChunk]:
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        body: dict[str, Any] = {
            "model": self._model,
            "messages": full_messages,
            "stream": True,
        }

        if tools:
            body["tools"] = tools

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream(
                "POST",
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            ) as resp:
                resp.raise_for_status()
                tool_call_name = ""
                tool_call_args = ""

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        if tool_call_name:
                            yield LLMChunk(
                                tool_call_name=tool_call_name,
                                tool_call_args=tool_call_args,
                                is_final=True,
                            )
                        else:
                            yield LLMChunk(is_final=True)
                        break

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    delta = chunk.get("choices", [{}])[0].get("delta", {})

                    # Text content
                    content = delta.get("content", "")
                    if content:
                        yield LLMChunk(text=content)

                    # Tool calls
                    tool_calls = delta.get("tool_calls", [])
                    if tool_calls:
                        tc = tool_calls[0]
                        fn = tc.get("function", {})
                        if fn.get("name"):
                            tool_call_name = fn["name"]
                        if fn.get("arguments"):
                            tool_call_args += fn["arguments"]
