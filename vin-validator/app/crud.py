from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Vin


async def find_vin(db: AsyncSession, vin: str) -> Vin | None:
    result = await db.execute(select(Vin).where(Vin.vin == vin))
    return result.scalar_one_or_none()
