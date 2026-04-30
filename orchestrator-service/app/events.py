import json
import aio_pika
from app.config import settings

_connection = None
_channel = None
_exchange = None


async def connect():
    global _connection, _channel, _exchange
    _connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    _channel = await _connection.channel()
    _exchange = await _channel.declare_exchange(
        "microservices",
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )


async def disconnect():
    if _connection:
        await _connection.close()


async def publish(routing_key: str, payload: dict):
    if not _exchange:
        return
    message = aio_pika.Message(
        body=json.dumps(payload).encode(),
        content_type="application/json",
    )
    await _exchange.publish(message, routing_key=routing_key)
