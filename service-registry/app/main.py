import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(registry.healthcheck_loop())
    yield
    task.cancel()


app = FastAPI(title="Service Registry", lifespan=lifespan)


class RegisterRequest(BaseModel):
    name: str
    url: str


@app.get("/health")
async def health():
    return {"status": "up", "service": "service-registry"}


@app.get("/services")
async def list_services():
    return registry.get_all()


@app.post("/register", status_code=201)
async def register(body: RegisterRequest):
    registry.register(body.name, body.url)
    return {"registered": body.name}


@app.delete("/deregister/{name}")
async def deregister(name: str):
    registry.deregister(name)
    return {"deregistered": name}
