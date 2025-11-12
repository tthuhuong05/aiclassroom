# services/ovd/ovd_owlvit.py
import os, re, torch
from PIL import Image
from transformers import OwlViTProcessor, OwlViTForObjectDetection

def _env_float(name: str, default: float) -> float:
    """Đọc env an toàn: bỏ comment (#,//), trim, chấp nhận '0,15'."""
    raw = os.getenv(name)
    if not raw:
        return float(default)
    s = raw.split('#', 1)[0].split('//', 1)[0].strip().replace(',', '.')
    m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
    return float(m.group(0)) if m else float(default)

class OwlVitOVD:
    def __init__(self, threshold=None, labels=None, device=None):
        self.threshold = float(threshold) if threshold is not None else _env_float("OVD_THRESHOLD", 0.15)
        self.labels = labels or [
            "hand", "fingers", "hand covering face",
            "phone", "cell phone", "smartphone", "phone screen",
            "book", "notebook", "paper", "sheet of paper", "cheat sheet",
            "pen", "pencil", "calculator",
            "glasses", "mask", "headset", "earbuds"
        ]
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = OwlViTProcessor.from_pretrained("google/owlvit-base-patch32")
        self.model = OwlViTForObjectDetection.from_pretrained("google/owlvit-base-patch32").to(self.device).eval()

    def detect_on_roi(self, pil_image: Image.Image, face_box, expand=0.6):
        """Chạy OVD quanh vùng mặt (mở rộng expand) và trả list dict {label, score, box} (tọa độ theo khung gốc)."""
        W, H = pil_image.size
        x0, y0, x1, y1 = [float(v) for v in face_box]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        w, h = (x1 - x0), (y1 - y0)
        w2, h2 = w * (1 + expand), h * (1 + expand)
        X0 = int(max(0, cx - w2 / 2)); Y0 = int(max(0, cy - h2 / 2))
        X1 = int(min(W, cx + w2 / 2)); Y1 = int(min(H, cy + h2 / 2))
        roi = pil_image.crop((X0, Y0, X1, Y1))

        inputs = self.processor(text=[self.labels], images=roi, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)

        target_sizes = torch.tensor([roi.size[::-1]], device=self.device)
        res = self.processor.post_process_object_detection(
            outputs, target_sizes=target_sizes, threshold=self.threshold
        )[0]

        out = []
        for score, label, box in zip(res["scores"], res["labels"], res["boxes"]):
            lx0, ly0, lx1, ly1 = [float(v) for v in box.tolist()]
            out.append({
                "label": self.labels[int(label)],
                "score": float(score),
                "box": [lx0 + X0, ly0 + Y0, lx1 + X0, ly1 + Y0],  # bù offset ROI
            })
        return out
