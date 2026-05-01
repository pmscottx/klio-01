import httpx
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    config_server_url: str = "http://config-server:8000"
    service_registry_url: str = "http://service-registry:8001"
    service_name: str = "uuid-service"
    service_url: str = "http://uuid-service:8011"

    class Config:
        env_file = ".env"


settings = Settings()


async def load_remote_config():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.config_server_url}/config/{settings.service_name}")
            if resp.status_code == 200:
                pass
    except Exception as e:
        print(f"[config] Could not reach config server: {e}. Using defaults.")


async def register_service():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.service_registry_url}/register",
                json={"name": settings.service_name, "url": settings.service_url},
            )
    except Exception as e:
        print(f"[registry] Registration failed: {e}")


async def deregister_service():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.delete(f"{settings.service_registry_url}/deregister/{settings.service_name}")
    except Exception:
        pass
