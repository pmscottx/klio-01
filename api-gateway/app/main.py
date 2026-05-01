from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, HTTPException, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings, load_remote_config, register_service, deregister_service
from app import circuit_breaker, proxy

limiter = Limiter(key_func=get_remote_address)

_http_client: httpx.AsyncClient | None = None

EXEMPT_PATHS = {"/health", "/", "/api/gateway/breakers"}
SERVICE_SEGMENT_MAP = {
    "inspections": "orchestrator-service",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _http_client
    await load_remote_config()
    circuit_breaker.init_breakers()
    _http_client = httpx.AsyncClient()
    proxy.set_client(_http_client)
    await register_service()
    yield
    await deregister_service()
    await _http_client.aclose()


app = FastAPI(title="API Gateway", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _require_auth(request: Request):
    if request.url.path in EXEMPT_PATHS:
        return
    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
async def health():
    return {"status": "up", "service": "api-gateway"}


@app.get("/api/gateway/breakers")
async def get_breaker_states():
    return circuit_breaker.get_all_states()


@app.api_route("/api/{resource}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit("60/minute")
async def proxy_with_path(resource: str, path: str, request: Request):
    _require_auth(request)
    service_name = SERVICE_SEGMENT_MAP.get(resource)
    if not service_name:
        raise HTTPException(status_code=404, detail=f"Unknown resource '{resource}'")
    full_path = f"{resource}/{path}"
    resp = await proxy.forward(service_name, full_path, request)
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


@app.api_route("/api/{resource}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
@limiter.limit("60/minute")
async def proxy_root(resource: str, request: Request):
    _require_auth(request)
    service_name = SERVICE_SEGMENT_MAP.get(resource)
    if not service_name:
        raise HTTPException(status_code=404, detail=f"Unknown resource '{resource}'")
    resp = await proxy.forward(service_name, resource, request)
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )
