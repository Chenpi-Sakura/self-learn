"""AOP LLM adapter 测试：chat_stream 自动装 hook + 双层包装防护。"""
import asyncio

import pytest

from selflearn.llm.adapters.mock import MockLLMAdapter
from selflearn.llm.base import ChatMessage, ChatRequest
from selflearn.observability.hooks import hook_bus


@pytest.mark.asyncio
async def test_llm_adapter_emits_hook_event() -> None:
    hook_bus.clear()
    adapter = MockLLMAdapter()
    req = ChatRequest(messages=[ChatMessage(role="user", content="hi")])
    # 必须消费完整流：hook_stream 的 emit("ok") 在 async-for 结束后执行；
    # 若提前 break，wrapper 生成器被 GeneratorExit 关闭，emit 不会触发。
    chunks = [c async for c in adapter.chat_stream(req)]
    assert chunks

    snap = hook_bus.snapshot()
    assert any(
        e["kind"] == "llm.call" and e["status"] == "ok" for e in snap
    ), f"LLM adapter 未触发 hook: {snap}"


def test_base_llm_adapter_double_wrap_protection() -> None:
    """验证 __init_subclass__ 不会把 hook 重复装在同一方法上。"""
    from selflearn.llm.base import BaseLLMAdapter

    class Probe(BaseLLMAdapter):
        provider_name = "probe"

        async def chat(self, req: object) -> str:
            return ""

        async def chat_stream(self, req: object):  # type: ignore[no-untyped-def]
            if False:
                yield None

        async def health(self) -> bool:
            return True

    # __init_subclass__ 时已装了一层 hook_stream；标记必须存在。
    assert getattr(Probe.chat_stream, "_is_hook_wrapped", False)

    from selflearn.llm.base import ChatRequest as CR

    async def run() -> None:
        hook_bus.clear()
        async for _ in Probe().chat_stream(CR(messages=[])):
            break

    asyncio.run(run())
    n = sum(1 for e in hook_bus.snapshot() if e["kind"] == "llm.call")
    assert n == 1, f"double wrap: got {n} events"
