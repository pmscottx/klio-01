from uuid import uuid4
from fastapi import APIRouter

router = APIRouter(tags=["uuid"])


@router.post("/uuid/generate")
async def generate_uuid():
    return {"uuid": str(uuid4())}
