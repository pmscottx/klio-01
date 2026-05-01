from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LicencePlate, Vin


async def find_licenceplate(db: AsyncSession, licenceplate: str) -> LicencePlate | None:
    result = await db.execute(select(LicencePlate).where(LicencePlate.licenceplate == licenceplate))
    return result.scalar_one_or_none()


async def find_vin(db: AsyncSession, vin: str) -> Vin | None:
    result = await db.execute(select(Vin).where(Vin.vin == vin))
    return result.scalar_one_or_none()
