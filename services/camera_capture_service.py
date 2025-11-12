# services/camera_capture_service.py
import os, base64, time
from pathlib import Path
import numpy as np
import cv2
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
# ✨ Dùng pipeline YOLO-face + COCO + attention đã có sẵn
from services.face_recognition_service import get_face_recognition_service
FR = get_face_recognition_service()

class CameraCaptureService:
    def __init__(self):
        self.upload_dir = os.path.join("static", "camera_captures")
        os.makedirs(self.upload_dir, exist_ok=True)

    # --------- Utils ----------
    def decode_base64_image(self, base64_data: str) -> Optional[bytes]:
        """
        Nhận cả dạng thuần base64 lẫn data-URL (data:image/jpeg;base64,...).
        Nắn padding, thay ' ' -> '+', và chấp nhận cả urlsafe.
        """
        try:
            data = base64_data.strip()
            if "," in data and data.lower().startswith("data:"):
                data = data.split(",", 1)[1]
            data = data.replace(" ", "+").replace("\n", "").replace("\r", "")
            missing = (-len(data)) % 4
            if missing:
                data += "=" * missing
            try:
                return base64.b64decode(data, validate=False)
            except Exception:
                return base64.urlsafe_b64decode(data)
        except Exception:
            return None

    def save_camera_image(self, image_data: bytes, attempt_id: str, frame_number: int) -> Optional[str]:
        """Lưu file ảnh để tiện debug/log."""
        try:
            fn = f"capture_{attempt_id}_{frame_number:06d}.jpg"
            fp = os.path.join(self.upload_dir, fn)
            with open(fp, "wb") as f:
                f.write(image_data)
            return fp
        except Exception:
            return None

    # --------- Main entry ----------
    def capture_frame_from_base64(self, base64_data: str, attempt_id: str, frame_number: int) -> Dict:
        """
        Trả về:
          {
            success, filepath, frame_number, latency_ms,
            ai: {
              face_count, attention_score, cheating_detected, cheating_reason,
              objects, suspicious_objects, entities, (v.v.)
            }
          }
        """
        t0 = time.time()
        try:
            img_bytes = self.decode_base64_image(base64_data)
            if not img_bytes:
                return {"success": False, "error": "Cannot decode image"}

            filepath = self.save_camera_image(img_bytes, attempt_id, frame_number)
            if not filepath:
                return {"success": False, "error": "Cannot save image"}

            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if bgr is None:
                return {"success": False, "error": "cv2.imdecode failed"}
            
            H, W = bgr.shape[:2]
            target_min = int(os.getenv("CAPTURE_MIN_SIDE", "640"))
            max_w = int(os.getenv("CAPTURE_MAX_W", "1280"))
            max_h = int(os.getenv("CAPTURE_MAX_H", "1280"))

            if min(H, W) < target_min:
              scale = target_min / float(min(H, W))
              newW, newH = int(round(W * scale)), int(round(H * scale))
              newW = min(newW, max_w)
              newH = min(newH, max_h)
              bgr = cv2.resize(bgr, (newW, newH), interpolation=cv2.INTER_CUBIC)

            # ✨ Pipeline YOLO-face + COCO + attention
            ai = FR.detect_faces_and_objects(bgr)

            return {
                "success": True,
                "filepath": filepath,
                "frame_number": frame_number,
                "latency_ms": int((time.time() - t0) * 1000),
                "ai": ai,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# Singleton
_camera_singleton = CameraCaptureService()
def get_camera_capture_service() -> CameraCaptureService:
    return _camera_singleton
