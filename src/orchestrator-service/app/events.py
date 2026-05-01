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

    queue = await _channel.declare_queue("orchestrator-q", durable=True)
    await queue.bind(_exchange, routing_key="picture.checked")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            event_type = payload.get("type")
            inspection_id = payload.get("inspection_id")
            value = payload.get("value", "")
            valid = payload.get("valid", False)
            filename = payload.get("filename", "")

            print(f"[orchestrator] picture.checked: type={event_type} valid={valid} for {inspection_id}")

            async with session_factory() as db:
                if event_type == "LICENCEPLATE":
                    await crud.update_box(db, inspection_id,
                        licenceplate=value,
                        licenceplate_status="found" if valid else "not_found",
                        licenceplate_desc=payload.get("desc"),
                    )
                    await crud.add_box_detail(db, inspection_id, filename, "LICENCEPLATE", value)
                elif event_type == "VIN":
                    await crud.update_box(db, inspection_id,
                        vin=value,
                        vin_status="found" if valid else "not_found",
                        vin_car=payload.get("car"),
                        vin_production_year=payload.get("production_year"),
                    )
                    await crud.add_box_detail(db, inspection_id, filename, "VIN", value)

                box = await crud.get_box(db, inspection_id)
                if box and box.licenceplate is not None and box.vin is not None:
                    await crud.update_box(db, inspection_id, status="completed")

    await queue.consume(on_message)
    print("[orchestrator] Consuming picture.checked events")


def start_consumer_task(session_factory):
    asyncio.create_task(start_consuming(session_factory))
