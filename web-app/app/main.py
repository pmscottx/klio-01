import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from typing import Annotated
from app.config import settings

app = FastAPI(title="Web App")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

AVAILABLE_IMAGES = ["img-1.jpeg", "img-2.jpeg", "img-3.jpeg", "img-4.jpeg"]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "images": AVAILABLE_IMAGES,
    })


@app.post("/submit")
async def submit(request: Request, filenames: Annotated[list[str] | None, Form()] = None):
    if not filenames:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "images": AVAILABLE_IMAGES,
            "error": "Wybierz co najmniej 3 zdjęcia.",
        }, status_code=422)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.api_gateway_url}/api/inspections",
                json={"filenames": filenames},
                headers={"X-API-Key": settings.api_key, "Content-Type": "application/json"},
            )
            if resp.status_code == 201:
                inspection_id = resp.json().get("inspection_id")
                return RedirectResponse(url=f"/results/{inspection_id}", status_code=303)
            error = resp.json().get("detail", resp.text)
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "images": AVAILABLE_IMAGES,
        "error": f"Błąd: {error}",
    }, status_code=500)


@app.get("/results/{inspection_id}", response_class=HTMLResponse)
async def results(request: Request, inspection_id: str):
    inspection = None
    error = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.api_gateway_url}/api/inspections/{inspection_id}",
                headers={"X-API-Key": settings.api_key},
            )
            if resp.status_code == 200:
                inspection = resp.json()
            else:
                error = f"Inspekcja nie znaleziona (status {resp.status_code})"
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "inspection": inspection,
        "error": error,
        "inspection_id": inspection_id,
    })


@app.get("/health")
async def health():
    return {"status": "up", "service": "web-app"}
