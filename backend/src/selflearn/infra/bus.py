"""publish / consume 工具（在 Task 4 topology 之上）。"""
import json
from collections.abc import AsyncIterator, Awaitable, Callable

import aio_pika
from selflearn.core.envelope import Envelope
from selflearn.core.tracing import get_tracer
from selflearn.infra.rabbit import EXCHANGE_EVENTS, get_connection


Callback = Callable[[Envelope], Awaitable[None]]


async def publish_envelope(envelope: Envelope, routing_key: str) -> None:
    conn = await get_connection()
    ch = await conn.channel()
    ex = await ch.get_exchange(EXCHANGE_EVENTS)
    body = envelope.model_dump_json().encode("utf-8")
    tracer = get_tracer("bus")
    with tracer.start_as_current_span("publish") as span:
        span.set_attribute("messaging.system", "rabbitmq")
        span.set_attribute("messaging.rabbitmq.routing_key", routing_key)
        span.set_attribute("selflearn.trace_id", envelope.trace_id)
        await ex.publish(
            aio_pika.Message(body=body,
                             headers={"trace_id": envelope.trace_id},
                             content_type="application/json"),
            routing_key=routing_key,
        )
    await ch.close()


async def consume_envelope(
    queue_name: str,
    routing_key: str,
    callback: Callback,
    *,
    prefetch: int = 4,
) -> AsyncIterator[None]:
    """持续消费循环（worker 进程入口）。"""
    conn = await get_connection()
    ch = await conn.channel()
    await ch.set_qos(prefetch_count=prefetch)
    ex = await ch.get_exchange(EXCHANGE_EVENTS)
    queue = await ch.declare_queue(
        queue_name,
        durable=True,
        arguments={"x-dead-letter-exchange": "agent.events.dlx"},
    )
    await queue.bind(ex, routing_key=routing_key)
    async with queue.iterator() as it:
        async for msg in it:
            async with msg.process(requeue=False):
                payload = json.loads(msg.body.decode("utf-8"))
                env = Envelope.model_validate(payload)
                await callback(env)
        yield