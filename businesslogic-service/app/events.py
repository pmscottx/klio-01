import asyncio
import json
import httpx
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


async def _patch_inspection(inspection_id: str, patch: dict):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.patch(
                f"{settings.cids_service_url}/cids/inspections/{inspection_id}",
                json=patch,
            )
    except Exception as e:
        print(f"[businesslogic] Failed to patch inspection {inspection_id}: {e}")


async def start_consuming():
    queue = await _channel.declare_queue("businesslogic-service-q", durable=True)
    await queue.bind(_exchange, routing_key="licenceplate.checked")
    await queue.bind(_exchange, routing_key="vin.checked")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            event = payload.get("event")
            inspection_id = payload.get("inspection_id")
            print(f"[businesslogic] Received {event} for inspection {inspection_id}")

            if event == "licenceplate.checked":
                patch = {
                    "licenceplate": payload.get("licenceplate"),
                    "licenceplate_status": "found" if payload.get("valid") else "not_found",
                    "licenceplate_desc": payload.get("desc"),
                }
                await _patch_inspection(inspection_id, patch)

            elif event == "vin.checked":
                patch = {
                    "vin": payload.get("vin"),
                    "vin_status": "found" if payload.get("valid") else "not_found",
                    "vin_car": payload.get("car"),
                    "vin_production_year": payload.get("production_year"),
                }
                await _patch_inspection(inspection_id, patch)

    await queue.consume(on_message)


def start_consumer_task():
    asyncio.create_task(start_consuming())
