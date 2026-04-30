from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app import crud
from app.schemas import InspectionCreate, InspectionPatch, InspectionOut

router = APIRouter(prefix="/cids", tags=["cids"])


async def _get_db():
    from app.main import session_factory
    async with session_factory() as session:
        yield session


@router.post("/inspections", response_model=InspectionOut, status_code=201)
async def create_inspection(body: InspectionCreate, db: AsyncSession = Depends(_get_db)):
    return await crud.create_inspection(db, body)


@router.get("/inspections", response_model=list[InspectionOut])
async def list_inspections(db: AsyncSession = Depends(_get_db)):
    return await crud.list_inspections(db)


@router.get("/inspections/{inspection_id}", response_model=InspectionOut)
async def get_inspection(inspection_id: str, db: AsyncSession = Depends(_get_db)):
    item = await crud.get_inspection(db, inspection_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return item


@router.patch("/inspections/{inspection_id}", response_model=InspectionOut)
async def patch_inspection(inspection_id: str, body: InspectionPatch, db: AsyncSession = Depends(_get_db)):
    item = await crud.patch_inspection(db, inspection_id, body)
    if not item:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return item
