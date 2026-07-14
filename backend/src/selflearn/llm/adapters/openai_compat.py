"""OpenAI 兼容适配器（DeepSeek / 通义千问）。Stage 3: 解析 reasoning_content。"""
from __future__ import annotations

from collections.abc import AsyncIterator
import json

import httpx

from selflearn.llm.base import BaseLLMAdapter, ChatChunk, ChatRequest


class OpenAICompatAdapter(BaseLLMAdapter):
    provider_name = "openai_compat"

    def __init__(
        self, base_url: str, api_key: str, model: str, timeout: float = 120.0
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self._client = httpx.AsyncClient(
            timeout=timeout, headers={"Authorization": f"Bearer {api_key}"}
        )

    async def chat(self, req: ChatRequest) -> str:
        # Stage 4-fix: reasoning 模型在兼容 endpoint 下"stream:false" 也可能 chunked-stream 响应，
        # httpx 等不到 body 关闭就 ReadTimeout。统一走 chat_stream() 拼出 content。
        if req.reasoning:
            content_parts: list[str] = []
            async for chunk in self.chat_stream(req):
                if chunk.delta:
                    content_parts.append(chunk.delta)
            return "".join(content_parts)

        body: dict[str, object] = {
            "model": req.model or self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "temperature": req.temperature,
            "stream": False,
        }
        if req.max_tokens is not None:
            body["max_tokens"] = req.max_tokens
        if req.reasoning:
            body["reasoning"] = True
        r = await self._client.post(f"{self.base_url}/chat/completions", json=body)
        r.raise_for_status()
        data = r.json()
        first = data["choices"][0]
        return str(first["message"]["content"])

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
                # Stage 4-fix: reasoning 模型流式响应里 reasoning-only chunk 没有 choices 字段
                choices = obj.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                # Stage 3: DeepSeek-R1 / 通义 QwQ 在 stream 中同时含 reasoning_content 与 content
                if reasoning := delta.get("reasoning_content"):
                    yield ChatChunk(delta="", reasoning_delta=reasoning)
                if content := delta.get("content", ""):
                    yield ChatChunk(delta=content)

    async def health(self) -> bool:
        try:
            r = await self._client.get(f"{self.base_url}/models")
            return r.status_code == 200
        except Exception:
            return False
