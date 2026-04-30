import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app import registry

app = FastAPI(title="Service Registry")


class RegisterRequest(BaseModel):
    name: str
    url: str


@app.get("/health")
async def health():
    return {"status": "up"}


@app.post("/register")
async def register(req: RegisterRequest):
    entry = registry.register(req.name, req.url)
    return entry


@app.delete("/deregister/{name}")
async def deregister(name: str):
    if not registry.deregister(name):
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return {"message": f"Service '{name}' deregistered"}


@app.get("/services")
async def list_services():
    return registry.get_all()


@app.get("/services/{name}")
async def get_service(name: str):
    entry = registry.get_service(name)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return entry


async def _health_check_loop():
    """Periodically verify registered services are still alive."""
    await asyncio.sleep(15)
    while True:
        services = registry.get_all()
        async with httpx.AsyncClient(timeout=3.0) as client:
            for name, info in services.items():
                try:
                    resp = await client.get(f"{info['url']}/health")
                    status = "up" if resp.status_code == 200 else "down"
                except Exception:
                    status = "down"
                registry._services[name]["status"] = status
        await asyncio.sleep(30)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_health_check_loop())
