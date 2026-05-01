import asyncio
import random
from app.config import settings

_model = None
_mock_mode = True

MOCK_PLATES = ["WW12345", "KR98765", "PO11223", "GD77654", "WR34567"]


def load_model(path: str):
    global _model, _mock_mode
    try:
        from ultralytics import YOLO
        _model = YOLO(path)
        _mock_mode = False
        print(f"[lp-detector] YOLO model loaded from {path}")
    except Exception:
        _mock_mode = True
        print(f"[lp-detector] Model not found at {path}, running in mock mode")


async def detect(image_bytes: bytes) -> str | None:
    await asyncio.sleep(settings.detection_delay)
    if _mock_mode:
        return random.choice(MOCK_PLATES)
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
        print(f"[lp-detector] Detection error: {e}")
        return None
