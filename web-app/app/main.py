import httpx
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.config import settings

app = FastAPI(title="Web App")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload")
async def upload(request: Request, files: list[UploadFile] = File(...)):
    form_files = []
    for f in files:
        content = await f.read()
        form_files.append(("files", (f.filename, content, f.content_type or "image/jpeg")))

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.api_gateway_url}/api/inspections",
                headers={"X-API-Key": settings.api_key},
                files=form_files,
            )
            if resp.status_code == 201:
                data = resp.json()
                inspection_id = data.get("inspection_id")
                return RedirectResponse(url=f"/results/{inspection_id}", status_code=303)
            error = resp.text
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "error": f"Upload failed: {error}"},
        status_code=500,
    )


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
                error = f"Inspection not found (status {resp.status_code})"
    except Exception as e:
        error = str(e)

    return templates.TemplateResponse(
        "results.html",
        {"request": request, "inspection": inspection, "error": error, "inspection_id": inspection_id},
    )


@app.get("/health")
async def health():
    return {"status": "up", "service": "web-app"}
