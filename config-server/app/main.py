import json
from pathlib import Path
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Config Server")

CONFIGS_DIR = Path(__file__).parent / "configs"


@app.get("/health")
async def health():
    return {"status": "up", "service": "config-server"}


@app.get("/config/{service_name}")
async def get_config(service_name: str):
    config_file = CONFIGS_DIR / f"{service_name}.json"
    if not config_file.exists():
        raise HTTPException(status_code=404, detail=f"Config for '{service_name}' not found")
    return json.loads(config_file.read_text())
