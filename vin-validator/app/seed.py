from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Vin

SEED_DATA = [
    {"vin": "1HGBH41JXMN109186", "car": "Honda Civic", "production_year": date(2020, 3, 15)},
    {"vin": "2T1BURHE0JC028581", "car": "Toyota Corolla", "production_year": date(2018, 7, 22)},
    {"vin": "3VWFE21C04M000001", "car": "Volkswagen Golf", "production_year": date(2019, 1, 10)},
    {"vin": "WBANA73534B123456", "car": "BMW 3 Series", "production_year": date(2021, 11, 5)},
    {"vin": "WAUZZZ8K9BA012345", "car": "Audi A4", "production_year": date(2017, 6, 30)},
]


async def seed_db(db: AsyncSession):
    for entry in SEED_DATA:
        result = await db.execute(select(Vin).where(Vin.vin == entry["vin"]))
        if not result.scalar_one_or_none():
            db.add(Vin(**entry))
    await db.commit()
