import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app import crud, events

router = APIRouter(tags=["orchestrator"])


class InspectionRequest(BaseModel):
    filenames: list[str]


async def _get_db():
    from app.main import session_factory
    async with session_factory() as session:
        yield session


@router.post("/inspections", status_code=201)
async def create_inspection(body: InspectionRequest, db: AsyncSession = Depends(_get_db)):
    if len(body.filenames) < 3:
        raise HTTPException(status_code=422, detail="Należy przesłać min 3 zdjęcia!")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{settings.uuid_service_url}/uuid/generate")
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="UUID service error")
            inspection_id = resp.json()["uuid"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"UUID service unreachable: {e}")

    await crud.create_box(db, inspection_id, len(body.filenames))

    for filename in body.filenames:
        await events.publish("picture.created", {
            "event": "picture.created",
            "inspection_id": inspection_id,
            "filename": filename,
        })

    print(f"[orchestrator] Created inspection {inspection_id} for {len(body.filenames)} files")
    return {"inspection_id": inspection_id}


@router.get("/inspections/{inspection_id}")
async def get_inspection(inspection_id: str, db: AsyncSession = Depends(_get_db)):
    box = await crud.get_box(db, inspection_id)
    if not box:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return {
        "id": box.uuid,
        "status": box.status,
        "image_count": box.picture_number,
        "created_at": box.created,
        "licenceplate": box.licenceplate,
        "licenceplate_status": box.licenceplate_status,
        "licenceplate_desc": box.licenceplate_desc,
        "vin": box.vin,
        "vin_status": box.vin_status,
        "vin_car": box.vin_car,
        "vin_production_year": box.vin_production_year,
    }
