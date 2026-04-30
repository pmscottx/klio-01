from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import LicencePlate

SEED_DATA = [
    {"licenceplate": "WW12345", "desc": "Toyota Corolla"},
    {"licenceplate": "KR54321", "desc": "BMW 3 Series"},
    {"licenceplate": "GD99001", "desc": "Volkswagen Golf"},
    {"licenceplate": "PO11223", "desc": "Ford Focus"},
    {"licenceplate": "WA77654", "desc": "Audi A4"},
]


async def seed_db(db: AsyncSession):
    for entry in SEED_DATA:
        result = await db.execute(
            select(LicencePlate).where(LicencePlate.licenceplate == entry["licenceplate"])
        )
        if not result.scalar_one_or_none():
            db.add(LicencePlate(**entry))
    await db.commit()
