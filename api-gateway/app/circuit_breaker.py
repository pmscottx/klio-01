import time
from app.config import settings


class CircuitBreakerOpen(Exception):
    pass


class AsyncCircuitBreaker:
    def __init__(self, fail_max: int, reset_timeout: int, name: str):
        self.name = name
        self._fail_max = fail_max
        self._reset_timeout = reset_timeout
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def current_state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if time.time() - self._opened_at >= self._reset_timeout:
            return "half-open"
        return "open"

    async def call_async(self, coro_func):
        state = self.current_state
        if state == "open":
            raise CircuitBreakerOpen(self.name)
        try:
            result = await coro_func()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        self._failures = 0
        self._opened_at = None

    def _on_failure(self):
        self._failures += 1
        if self._failures >= self._fail_max:
            self._opened_at = time.time()


_breakers: dict[str, AsyncCircuitBreaker] = {}

SERVICE_NAMES = ["businesslogic-service"]


def init_breakers():
    for name in SERVICE_NAMES:
        _breakers[name] = AsyncCircuitBreaker(
            fail_max=settings.circuit_breaker_fail_max,
            reset_timeout=settings.circuit_breaker_reset_timeout,
            name=name,
        )


def get_breaker(service_name: str) -> AsyncCircuitBreaker | None:
    return _breakers.get(service_name)


def get_all_states() -> dict[str, str]:
    return {name: b.current_state for name, b in _breakers.items()}
