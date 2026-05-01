import asyncio
from datetime import datetime, timedelta

_services: dict[str, dict] = {}
_TIMEOUT = timedelta(seconds=90)


def register(name: str, url: str):
    _services[name] = {"name": name, "url": url, "status": "up", "last_seen": datetime.utcnow()}


def deregister(name: str):
    _services.pop(name, None)


def get_all() -> list[dict]:
    return [
        {**v, "last_seen": v["last_seen"].isoformat()}
        for v in _services.values()
    ]


def get_url(name: str) -> str | None:
    svc = _services.get(name)
    return svc["url"] if svc else None


async def healthcheck_loop():
    import httpx
    while True:
        await asyncio.sleep(30)
        now = datetime.utcnow()
        for name, svc in list(_services.items()):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{svc['url']}/health")
                if resp.status_code == 200:
                    _services[name]["status"] = "up"
                    _services[name]["last_seen"] = now
                else:
                    _services[name]["status"] = "down"
            except Exception:
                _services[name]["status"] = "down"
