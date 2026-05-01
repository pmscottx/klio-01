from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Box, BoxDetail


async def create_box(db: AsyncSession, uuid: str, picture_number: int) -> Box:
    box = Box(
        uuid=uuid,
        created=datetime.utcnow().isoformat(),
        picture_number=picture_number,
        status="pending",
    )
    db.add(box)
    await db.commit()
    await db.refresh(box)
    return box


async def get_box(db: AsyncSession, uuid: str) -> Box | None:
    result = await db.execute(select(Box).where(Box.uuid == uuid))
    return result.scalar_one_or_none()


async def update_box(db: AsyncSession, uuid: str, **fields) -> Box | None:
    await db.execute(update(Box).where(Box.uuid == uuid).values(**fields))
    await db.commit()
    return await get_box(db, uuid)


async def add_box_detail(db: AsyncSession, uuid: str, picture: str, attr_name: str, attr_value: str):
    detail = BoxDetail(uuid=uuid, picture=picture, attr_name=attr_name, attr_value=attr_value)
    db.add(detail)
    await db.commit()
