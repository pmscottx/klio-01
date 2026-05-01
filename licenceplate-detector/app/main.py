from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings, load_remote_config, register_service, deregister_service
from app import detector, events


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_remote_config()
    detector.load_model(settings.model_path)
    await events.connect()
    events.start_consumer_task()
    await register_service()
    yield
    await deregister_service()
    await events.disconnect()


app = FastAPI(title="LicencePlate Detector", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "up", "service": "licenceplate-detector"}
