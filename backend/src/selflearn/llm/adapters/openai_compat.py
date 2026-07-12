"""OpenAI 兼容适配器（DeepSeek / 通义千问）。"""
from __future__ import annotations

from collections.abc import AsyncIterator
import json

import httpx

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class OpenAICompatAdapter(BaseLLMAdapter):
    provider_name = "openai_compat"

    def __init__(
        self, base_url: str, api_key: str, model: str, timeout: float = 30.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(
            timeout=timeout, headers={"Authorization": f"Bearer {api_key}"}
        )

    async def chat(self, req: ChatRequest) -> str:
        body: dict[str, object] = {
            "model": req.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "stream": False,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        r = await self._client.post(f"{self.base_url}/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        choices = data["choices"]
        first = choices[0]
        message = first["message"]
        return str(message["content"])

    async def chat_stream(self, req: ChatRequest) -> AsyncIterator[ChatChunk]:
        body: dict[str, object] = {
            "model": req.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "stream": True,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        async with self._client.stream(
            "POST", f"{self.base_url}/chat/completions", json=body
        ) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data.strip() == "[DONE]":
                    yield ChatChunk(delta="", finish_reason="stop")
                    return
                obj = json.loads(data)
                delta = obj["choices"][0]["delta"].get("content", "")
                if delta:
                    yield ChatChunk(delta=delta)

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/models")
            return r.status_code == 200
        except Exception:
            return False