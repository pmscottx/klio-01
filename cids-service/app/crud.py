import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Inspection
from app.schemas import InspectionCreate, InspectionPatch


async def create_inspection(db: AsyncSession, data: InspectionCreate) -> Inspection:
    inspection = Inspection(id=str(uuid.uuid4()), image_count=data.image_count)
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)
    return inspection


async def get_inspection(db: AsyncSession, inspection_id: str) -> Inspection | None:
    result = await db.execute(select(Inspection).where(Inspection.id == inspection_id))
    return result.scalar_one_or_none()


async def list_inspections(db: AsyncSession) -> list[Inspection]:
    result = await db.execute(select(Inspection).order_by(Inspection.created_at.desc()))
    return list(result.scalars().all())


async def patch_inspection(db: AsyncSession, inspection_id: str, data: InspectionPatch) -> Inspection | None:
    inspection = await get_inspection(db, inspection_id)
    if not inspection:
        return None
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(inspection, field, value)
    await db.commit()
    await db.refresh(inspection)
    return inspection
