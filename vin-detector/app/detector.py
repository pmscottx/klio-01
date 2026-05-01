import asyncio
import random
from app.config import settings

_model = None
_mock_mode = True

MOCK_VINS = [
    "VF1LM1B0H35296680",
    "WAUZZZ8K9BA012345",
    "WBA3A5C58CF256551",
    "2T1BURHE0JC028581",
    "VF7NC5FWC31614893",
]


def load_model(path: str):
    global _model, _mock_mode
    try:
        from ultralytics import YOLO
        _model = YOLO(path)
        _mock_mode = False
        print(f"[vin-detector] YOLO model loaded from {path}")
    except Exception:
        _mock_mode = True
        print(f"[vin-detector] Model not found at {path}, running in mock mode")


async def detect(image_bytes: bytes) -> str | None:
    await asyncio.sleep(settings.detection_delay)
    if _mock_mode:
        return random.choice(MOCK_VINS)
    try:
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(image_bytes)
            tmp_path = f.name
        results = _model(tmp_path)
        os.unlink(tmp_path)
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = _model.names[cls]
                return label
        return None
    except Exception as e:
        print(f"[vin-detector] Detection error: {e}")
        return None
