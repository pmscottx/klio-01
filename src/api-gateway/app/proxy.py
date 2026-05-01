import httpx
from fastapi import HTTPException, Request
from app import registry_client, circuit_breaker
from app.circuit_breaker import CircuitBreakerOpen

_http_client: httpx.AsyncClient | None = None


def set_client(client: httpx.AsyncClient):
    global _http_client
    _http_client = client


async def forward(service_name: str, path: str, request: Request) -> httpx.Response:
    base_url = await registry_client.get_service_url(service_name)
    if not base_url:
        raise HTTPException(status_code=503, detail=f"Service '{service_name}' not found in registry")

    breaker = circuit_breaker.get_breaker(service_name)
    url = f"{base_url}/{path}"
    body = await request.body()
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ("host", "x-api-key", "content-length")
    }

    async def _do_request():
        return await _http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
            timeout=60.0,
        )

    try:
        response = await breaker.call_async(_do_request)
        return response
    except CircuitBreakerOpen:
        raise HTTPException(status_code=503, detail=f"Service '{service_name}' unavailable (circuit breaker open)")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Service '{service_name}' unreachable: {e}")
