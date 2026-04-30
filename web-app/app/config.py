from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_gateway_url: str = "http://api-gateway:8080"
    api_key: str = "demo-key-123"

    class Config:
        env_file = ".env"


settings = Settings()
