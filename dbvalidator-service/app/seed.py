from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import LicencePlate, Vin

LP_RECORDS = [
    ("WW12345", "Toyota Corolla, Warszawa"),
    ("KR98765", "BMW 3 Series, Kraków"),
    ("PO11223", "Ford Focus, Poznań"),
    ("GD77654", "Volkswagen Golf, Gdańsk"),
    ("WR34567", "Audi A4, Wrocław"),
]

VIN_RECORDS = [
    ("VF1LM1B0H35296680", "Renault Megane", date(2017, 6, 15)),
    ("WAUZZZ8K9BA012345", "Audi A4", date(2019, 3, 20)),
    ("WBA3A5C58CF256551", "BMW 3 Series", date(2012, 11, 8)),
    ("2T1BURHE0JC028581", "Toyota Corolla", date(2018, 9, 1)),
    ("VF7NC5FWC31614893", "Citroën C5", date(2015, 4, 22)),
]


async def seed_db(db: AsyncSession):
    existing_lp = await db.execute(select(LicencePlate).limit(1))
    if not existing_lp.scalar_one_or_none():
        for licenceplate, desc in LP_RECORDS:
            db.add(LicencePlate(licenceplate=licenceplate, desc=desc))

    existing_vin = await db.execute(select(Vin).limit(1))
    if not existing_vin.scalar_one_or_none():
        for vin, car, production_year in VIN_RECORDS:
            db.add(Vin(vin=vin, car=car, production_year=production_year))

    await db.commit()
