import asyncio
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


async def start_consuming(session_factory):
    queue = await _channel.declare_queue("vin-validator-q", durable=True)
    await queue.bind(_exchange, routing_key="vin.detected")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            inspection_id = payload.get("inspection_id")
            vin = payload.get("vin")
            print(f"[vin-validator] Received vin.detected: {vin} for inspection {inspection_id}")
            async with session_factory() as db:
                from app.crud import find_vin
                record = await find_vin(db, vin)
            if record:
                await publish("vin.checked", {
                    "event": "vin.checked",
                    "inspection_id": inspection_id,
                    "vin": vin,
                    "valid": True,
                    "car": record.car,
                    "production_year": record.production_year.isoformat(),
                })
            else:
                await publish("vin.checked", {
                    "event": "vin.checked",
                    "inspection_id": inspection_id,
                    "vin": vin,
                    "valid": False,
                    "car": None,
                    "production_year": None,
                })

    await queue.consume(on_message)


def start_consumer_task(session_factory):
    asyncio.create_task(start_consuming(session_factory))
