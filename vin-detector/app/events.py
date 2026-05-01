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


async def start_consuming():
    from app import detector

    queue = await _channel.declare_queue("vin-detector-q", durable=True)
    await queue.bind(_exchange, routing_key="picture.created")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            inspection_id = payload.get("inspection_id")
            filename = payload.get("filename")

            image_path = f"{settings.images_dir}/{filename}"
            try:
                with open(image_path, "rb") as f:
                    image_bytes = f.read()
            except FileNotFoundError:
                print(f"[vin-detector] File not found: {image_path}")
                return

            vin = await detector.detect(image_bytes)
            if vin:
                await publish("picture.detected", {
                    "event": "picture.detected",
                    "type": "VIN",
                    "value": vin,
                    "inspection_id": inspection_id,
                    "filename": filename,
                })
                print(f"[vin-detector] Detected {vin} in {filename}")
            else:
                print(f"[vin-detector] No VIN in {filename}")

    await queue.consume(on_message)
    print("[vin-detector] Consuming picture.created events")


def start_consumer_task():
    asyncio.create_task(start_consuming())
