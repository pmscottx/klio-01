from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import load_remote_config, register_service, deregister_service
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_remote_config()
    await register_service()
    yield
    await deregister_service()


app = FastAPI(title="UUID Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "up", "service": "uuid-service"}
