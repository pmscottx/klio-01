import time
import httpx
from app.config import settings

_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 10.0


async def get_service_url(service_name: str) -> str | None:
    now = time.monotonic()
    if service_name in _cache:
        url, ts = _cache[service_name]
        if now - ts < CACHE_TTL:
            return url

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.service_registry_url}/services/{service_name}"
            )
            if resp.status_code == 200:
                url = resp.json()["url"]
                _cache[service_name] = (url, now)
                return url
    except Exception:
        pass

    if service_name in _cache:
        return _cache[service_name][0]
    return None
