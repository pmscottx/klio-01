from datetime import datetime, timezone

_services: dict[str, dict] = {}


def register(name: str, url: str) -> dict:
    _services[name] = {
        "name": name,
        "url": url,
        "status": "up",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    return _services[name]


def deregister(name: str) -> bool:
    return _services.pop(name, None) is not None


def get_service(name: str) -> dict | None:
    return _services.get(name)


def get_all() -> dict:
    return dict(_services)
