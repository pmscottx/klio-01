from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import load_remote_config, register_service, deregister_service
from app import events
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_remote_config()
    await events.connect()
    events.start_consumer_task()
    await register_service()
    yield
    await deregister_service()
    await events.disconnect()


app = FastAPI(title="BusinessLogic Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "up", "service": "businesslogic-service"}
