import httpx
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    config_server_url: str = "http://config-server:8000"
    service_registry_url: str = "http://service-registry:8001"
    service_name: str = "licenceplate-detector"
    service_url: str = "http://licenceplate-detector:8013"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq/"
    model_path: str = "/app/models/licenceplate-model.pt"
    detection_delay: int = 8
    images_dir: str = "/app/images"

    class Config:
        env_file = ".env"


settings = Settings()


async def load_remote_config():
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.config_server_url}/config/{settings.service_name}")
            if resp.status_code == 200:
                data = resp.json()
                settings.rabbitmq_url = data.get("rabbitmq_url", settings.rabbitmq_url)
                settings.model_path = data.get("model_path", settings.model_path)
                settings.detection_delay = data.get("detection_delay", settings.detection_delay)
                settings.images_dir = data.get("images_dir", settings.images_dir)
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
