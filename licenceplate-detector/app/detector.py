import asyncio
import io
import random
from pathlib import Path

_model = None
_mock_mode = False

MOCK_PLATES = ["WW12345", "KR54321", "GD99001", "PO11223", "WA77654", None, None]


def load_model(model_path: str):
    global _model, _mock_mode
    if not Path(model_path).exists():
        print(f"[lp-detector] Model file not found at {model_path}. Running in mock mode.")
        _mock_mode = True
        return
    try:
        from ultralytics import YOLO
        _model = YOLO(model_path)
        print(f"[lp-detector] Model loaded from {model_path}")
    except Exception as e:
        print(f"[lp-detector] Failed to load model: {e}. Running in mock mode.")
        _mock_mode = True


async def detect(image_bytes: bytes) -> str | None:
    from app.config import settings
    if settings.detection_delay > 0:
        print(f"[lp-detector] Simulating detection delay: {settings.detection_delay}s")
        await asyncio.sleep(settings.detection_delay)
    if _mock_mode:
        result = random.choice(MOCK_PLATES)
        print(f"[lp-detector] Mock detection result: {result}")
        return result
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes))
        results = _model(image)
        for result in results:
            for box in result.boxes:
                label = result.names[int(box.cls)]
                if label:
                    return label
    except Exception as e:
        print(f"[lp-detector] Detection error: {e}")
    return None
