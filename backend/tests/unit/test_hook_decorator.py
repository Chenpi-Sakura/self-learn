import pytest


@pytest.mark.asyncio
async def test_hook_decorator_emits_ok_event() -> None:
    from selflearn.observability.hooks import hook_bus
    from selflearn.observability.decorators import hook
    hook_bus.clear()

    @hook("test.fn")
    async def fn(x: int) -> int:
        return x * 2

    result = await fn(3)
    assert result == 6

    snap = hook_bus.snapshot()
    assert any(e["kind"] == "test.fn" and e["status"] == "ok" for e in snap)


@pytest.mark.asyncio
async def test_hook_decorator_emits_error_event_on_exception() -> None:
    from selflearn.observability.hooks import hook_bus
    from selflearn.observability.decorators import hook
    hook_bus.clear()

    @hook("test.err")
    async def bad() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await bad()
    snap = hook_bus.snapshot()
    assert any(
        e["kind"] == "test.err" and e["status"] == "error" and "boom" in e["error"]
        for e in snap
    )


@pytest.mark.asyncio
async def test_hook_stream_counts_chunks() -> None:
    from selflearn.observability.hooks import hook_bus
    from selflearn.observability.decorators import hook_stream
    hook_bus.clear()

    @hook_stream("test.stream")
    async def gen():  # type: ignore[no-untyped-def]
        for i in range(3):
            yield i

    out = []
    async for x in gen():
        out.append(x)
    assert out == [0, 1, 2]

    snap = hook_bus.snapshot()
    assert any(e["kind"] == "test.stream" and e["n_chunks"] == 3 for e in snap)
