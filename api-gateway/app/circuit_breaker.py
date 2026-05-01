import time
from app.config import settings

_breakers: dict[str, dict] = {}


class CircuitBreakerOpen(Exception):
    pass


def init_breakers():
    pass


def get_breaker(service_name: str):
    if service_name not in _breakers:
        _breakers[service_name] = {
            "failures": 0,
            "state": "closed",
            "opened_at": None,
        }
    return _breakers[service_name]


def get_all_states() -> dict:
    return {name: {"state": b["state"], "failures": b["failures"]} for name, b in _breakers.items()}


class AsyncCircuitBreaker:
    def __init__(self, service_name: str):
        self.service_name = service_name
        self._state = get_breaker(service_name)

    async def call_async(self, func):
        state = self._state
        if state["state"] == "open":
            elapsed = time.time() - (state["opened_at"] or 0)
            if elapsed >= settings.circuit_breaker_reset_timeout:
                state["state"] = "half-open"
            else:
                raise CircuitBreakerOpen(f"Circuit breaker open for {self.service_name}")

        try:
            result = await func()
            if state["state"] == "half-open":
                state["state"] = "closed"
                state["failures"] = 0
            return result
        except Exception:
            state["failures"] += 1
            if state["failures"] >= settings.circuit_breaker_fail_max:
                state["state"] = "open"
                state["opened_at"] = time.time()
            raise


def get_breaker(service_name: str) -> AsyncCircuitBreaker:
    if service_name not in _breakers:
        _breakers[service_name] = {"failures": 0, "state": "closed", "opened_at": None}
    return AsyncCircuitBreaker(service_name)
