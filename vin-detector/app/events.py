import asyncio
import base64
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


async def start_consuming():
    queue = await _channel.declare_queue("vin-detector-q", durable=True)
    await queue.bind(_exchange, routing_key="vin.created")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            inspection_id = payload.get("inspection_id")
            image_bytes = base64.b64decode(payload["image_b64"])
            from app import detector
            vin = await detector.detect(image_bytes)
            if vin:
                await publish("vin.detected", {
                    "event": "vin.detected",
                    "inspection_id": inspection_id,
                    "vin": vin,
                })
                print(f"[vin-detector] Published vin.detected: {vin}")
            else:
                print(f"[vin-detector] No VIN detected for inspection {inspection_id}")

    await queue.consume(on_message)
    print("[vin-detector] Consuming vin.created events")


def start_consumer_task():
    asyncio.ensure_future(start_consuming())
