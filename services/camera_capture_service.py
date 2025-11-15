# services/camera_capture_service.py
import os, base64, time, shutil, re, unicodedata
from datetime import datetime
from pathlib import Path
import numpy as np
import cv2
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
# ✨ Dùng pipeline YOLO-face + COCO + attention đã có sẵn
from services.face_recognition_service import get_face_recognition_service
FR = get_face_recognition_service()


def _slugify(text: Optional[str], fallback: str) -> str:
    fallback = str(fallback or "item").lower()
    value = (text or "").strip()
    if not value:
        value = fallback
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        value = fallback
    return value[:80]

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

            rel_path = filepath.replace("\\", "/")
            web_url = f"/{rel_path.lstrip('/')}"
            captured_at = datetime.utcnow().isoformat()

            return {
                "success": True,
                "filepath": filepath,
                "relative_filepath": rel_path,
                "web_url": web_url,
                "captured_at": captured_at,
                "frame_number": frame_number,
                "latency_ms": int((time.time() - t0) * 1000),
                "ai": ai,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def promote_evidence(
        self,
        source_path: str,
        *,
        user_slug: str,
        course_slug: str,
        attempt_id: str,
        frame_no: int,
        event_type: str,
        reason: Optional[str] = None,
        captured_at: Optional[str] = None,
    ) -> Optional[Dict[str, str]]:
        """
        Sao chép ảnh nguồn vào thư mục evidence theo người dùng & khóa học.
        """
        if not source_path:
            return None

        abs_source = source_path
        if not os.path.isfile(abs_source):
            abs_source = os.path.abspath(source_path)
            if not os.path.isfile(abs_source):
                return None

        timestamp = captured_at
        if not timestamp:
            timestamp = datetime.utcnow().isoformat()
        try:
            ts_obj = datetime.fromisoformat(timestamp)
        except Exception:
            ts_obj = datetime.utcnow()
        ts_label = ts_obj.strftime("%Y%m%d-%H%M%S")

        reason_slug = _slugify(reason, "reason") if reason else ""
        event_slug = _slugify(event_type, "event")
        user_slug = _slugify(user_slug, "user")
        course_slug = _slugify(course_slug, "course")

        base_name = f"{ts_label}_{course_slug}_{attempt_id}_frame{int(frame_no):04d}_{event_slug}"
        if reason_slug:
            base_name = f"{base_name}_{reason_slug}"

        ext = os.path.splitext(abs_source)[1] or ".jpg"
        dest_dir = os.path.join(self.upload_dir, "evidence", user_slug)
        os.makedirs(dest_dir, exist_ok=True)

        dest_path = os.path.join(dest_dir, f"{base_name}{ext}")
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{base_name}_{counter}{ext}")
            counter += 1

        shutil.copy2(abs_source, dest_path)

        rel_path = dest_path.replace("\\", "/")
        if not rel_path.startswith("static/"):
            try:
                rel_path = os.path.relpath(dest_path, start=os.getcwd()).replace("\\", "/")
            except Exception:
                rel_path = dest_path.replace("\\", "/")
        web_url = f"/{rel_path.lstrip('/')}"

        return {
            "absolute_path": dest_path,
            "relative_path": rel_path,
            "web_url": web_url,
            "captured_at": ts_obj.isoformat(),
        }

# Singleton
_camera_singleton = CameraCaptureService()
def get_camera_capture_service() -> CameraCaptureService:
    return _camera_singleton
