import base64
from fastapi import APIRouter, UploadFile, File, Form
from app import events

router = APIRouter(tags=["orchestrator"])


@router.post("/orchestrator/process")
async def process_image(
    inspection_id: str = Form(...),
    file: UploadFile = File(...),
):
    image_bytes = await file.read()
    image_b64 = base64.b64encode(image_bytes).decode()
    payload_base = {
        "inspection_id": inspection_id,
        "image_b64": image_b64,
        "filename": file.filename or "image.jpg",
    }
    await events.publish("licenceplate.created", {"event": "licenceplate.created", **payload_base})
    await events.publish("vin.created", {"event": "vin.created", **payload_base})
    print(f"[orchestrator] Published licenceplate.created + vin.created for {inspection_id}")
    return {"inspection_id": inspection_id, "status": "processing"}
