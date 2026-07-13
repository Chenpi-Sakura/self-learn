def test_hook_bus_emits_and_snapshots() -> None:
    from selflearn.observability.hooks import HookBus
    bus = HookBus(maxlen=10)
    bus.emit("test.kind", {"a": 1})
    bus.emit("test.kind2", {"b": 2})
    snap = bus.snapshot()
    assert len(snap) == 2
    assert snap[0]["kind"] == "test.kind"
    assert snap[1]["kind"] == "test.kind2"
    assert snap[0]["ts"] > 0


def test_hook_bus_respects_maxlen() -> None:
    from selflearn.observability.hooks import HookBus
    bus = HookBus(maxlen=3)
    for i in range(5):
        bus.emit("x", {"i": i})
    assert len(bus.snapshot()) == 3
    snap = bus.snapshot()
    assert [s["i"] for s in snap] == [2, 3, 4]


def test_hook_bus_is_thread_safe() -> None:
    import threading
    from selflearn.observability.hooks import HookBus
    bus = HookBus(maxlen=1000)

    def worker() -> None:
        for i in range(100):
            bus.emit("t", {"i": i})

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(bus.snapshot()) == 500
