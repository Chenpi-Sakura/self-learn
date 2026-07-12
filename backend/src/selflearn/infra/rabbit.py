import aio_pika
from selflearn.config import get_settings

_settings = get_settings()
EXCHANGE_EVENTS = "agent.events"
EXCHANGE_DLX = "agent.events.dlx"
QUEUE_DLQ = "agent.dlq"
_connection: aio_pika.abc.AbstractRobustConnection | None = None


async def get_connection() -> aio_pika.abc.AbstractRobustConnection:
    global _connection
    if _connection is None or _connection.is_closed:
        _connection = await aio_pika.connect_robust(_settings.rabbitmq_url)
    return _connection


async def setup_topology() -> None:
    conn = await get_connection()
    ch = await conn.channel()
    await ch.declare_exchange(EXCHANGE_DLX, aio_pika.ExchangeType.TOPIC, durable=True)
    dlq = await ch.declare_queue(QUEUE_DLQ, durable=True)
    await dlq.bind(EXCHANGE_DLX, routing_key="#")
    await ch.declare_exchange(EXCHANGE_EVENTS, aio_pika.ExchangeType.TOPIC, durable=True)
    await ch.close()


async def health() -> bool:
    try:
        conn = await get_connection()
        return not conn.is_closed
    except Exception:
        return False