import httpx
from app.config import settings


async def get_service_url(service_name: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.service_registry_url}/services")
            if resp.status_code == 200:
                services = resp.json()
                for svc in services:
                    if svc["name"] == service_name and svc.get("status") == "up":
                        return svc["url"]
    except Exception:
        pass
    return None
