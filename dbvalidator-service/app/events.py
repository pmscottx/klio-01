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
    from app import crud

    queue = await _channel.declare_queue("dbvalidator-q", durable=True)
    await queue.bind(_exchange, routing_key="picture.detected")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            event_type = payload.get("type")
            value = payload.get("value", "")
            inspection_id = payload.get("inspection_id")
            filename = payload.get("filename", "")

            print(f"[dbvalidator] picture.detected: type={event_type} value={value}")

            async with session_factory() as db:
                if event_type == "LICENCEPLATE":
                    record = await crud.find_licenceplate(db, value)
                    await publish("picture.checked", {
                        "event": "picture.checked",
                        "type": "LICENCEPLATE",
                        "value": value,
                        "valid": record is not None,
                        "desc": record.desc if record else None,
                        "inspection_id": inspection_id,
                        "filename": filename,
                    })
                elif event_type == "VIN":
                    record = await crud.find_vin(db, value)
                    await publish("picture.checked", {
                        "event": "picture.checked",
                        "type": "VIN",
                        "value": value,
                        "valid": record is not None,
                        "car": record.car if record else None,
                        "production_year": record.production_year.isoformat() if record else None,
                        "inspection_id": inspection_id,
                        "filename": filename,
                    })

    await queue.consume(on_message)
    print("[dbvalidator] Consuming picture.detected events")


def start_consumer_task(session_factory):
    asyncio.create_task(start_consuming(session_factory))
