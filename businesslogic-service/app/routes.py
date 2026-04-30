import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings

router = APIRouter(tags=["businesslogic"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}


@router.post("/inspections", status_code=201)
async def create_inspection(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=422, detail="No files provided")

    for f in files:
        if f.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported file type: {f.content_type}. Use jpg/jpeg/png.",
            )

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.cids_service_url}/cids/inspections",
            json={"image_count": len(files)},
        )
        if resp.status_code != 201:
            raise HTTPException(status_code=502, detail="Failed to create inspection record")
        inspection = resp.json()

    inspection_id = inspection["id"]

    for f in files:
        image_bytes = await f.read()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                await client.post(
                    f"{settings.orchestrator_service_url}/orchestrator/process",
                    data={"inspection_id": inspection_id},
                    files={"file": (f.filename or "image.jpg", image_bytes, f.content_type or "image/jpeg")},
                )
        except Exception as e:
            print(f"[businesslogic] Error sending image to orchestrator: {e}")

    return {"inspection_id": inspection_id}


@router.get("/inspections/{inspection_id}")
async def get_inspection(inspection_id: str):
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.cids_service_url}/cids/inspections/{inspection_id}"
            )
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="Inspection not found")
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CIDS service error: {e}")
