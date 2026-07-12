"""启动入口：通过 --role 区分 gateway / worker / all。"""
from __future__ import annotations

import argparse
import asyncio
import sys


def parse_role() -> str:
    p = argparse.ArgumentParser()
    p.add_argument("--role", choices=["gateway", "worker", "all"], default="all")
    return p.parse_args().role


async def run_gateway() -> None:
    import uvicorn

    from selflearn.config import get_settings

    s = get_settings()
    uvicorn.run(
        "selflearn.gateway.app:create_app",
        factory=True,
        host=s.gateway_host,
        port=s.gateway_port,
        log_level=s.log_level.lower(),
    )


async def run_worker() -> None:
    # Task 12 替换为真实 aio-pika consumer
    print("[worker] placeholder - Task 12 will wire aio-pika consumer here")


def main() -> int:
    role = parse_role()
    if role == "gateway":
        asyncio.run(run_gateway())
    elif role == "worker":
        asyncio.run(run_worker())
    else:
        print("[main] role=all: run gateway + worker in same process (dev only)")
        asyncio.run(run_gateway())
    return 0


if __name__ == "__main__":
    sys.exit(main())
