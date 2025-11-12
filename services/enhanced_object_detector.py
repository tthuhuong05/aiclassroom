
"""
Enhanced Object Detector (open-vocabulary fallback)
---------------------------------------------------
Drop-in fallback used by FaceRecognitionService when YOLO/SSD models are missing
or too weak. It tries, in order:
  1) OWL-ViT (open-vocabulary) from HuggingFace Transformers if available.
  2) Lightweight rectangle heuristic for phone/laptop/paper-like shapes.
All imports are optional; module will degrade gracefully.

Returned format: list of dicts:
  { "type": <label>, "position": (x,y,w,h), "score": <0..1>, "source": "enhanced" }
"""

from typing import List, Dict, Tuple, Optional
import math
import numpy as np

try:
    import cv2  # type: ignore
except Exception:
    cv2 = None  # type: ignore

# Optional: Transformers OWL-ViT
_HAS_OWL = False
try:
    from transformers import OwlViTProcessor, OwlViTForObjectDetection  # type: ignore
    import torch  # type: ignore
    _HAS_OWL = True
except Exception:
    _HAS_OWL = False

DEFAULT_PROMPTS = [
    # keep short, concrete nouns to improve OWL-ViT results
    "cell phone", "mobile phone", "smartphone",
    "laptop", "notebook", "tablet",
    "book", "paper", "sheet of paper",
    "keyboard", "mouse", "monitor", "tv", "remote"
]

def _to_rgb(img_bgr):
    if img_bgr is None:
        return None
    return img_bgr[:, :, ::-1]

class EnhancedObjectDetector:
    def __init__(self, confidence_threshold: float = 0.20, prompts: Optional[List[str]] = None):
        self.conf = float(confidence_threshold)
        self.prompts = prompts[:] if prompts else DEFAULT_PROMPTS[:]
        self._owl_processor = None
        self._owl_model = None
        if _HAS_OWL:
            try:
                # Pick a small OWL-ViT by default
                self._owl_processor = OwlViTProcessor.from_pretrained("google/owlvit-base-patch32")
                self._owl_model = OwlViTForObjectDetection.from_pretrained("google/owlvit-base-patch32")
                self._owl_model.eval()
            except Exception:
                # If model cannot load, fall back to heuristics only
                self._owl_processor = None
                self._owl_model = None

    def _detect_owl(self, img_bgr) -> List[Dict]:
        if self._owl_processor is None or self._owl_model is None or cv2 is None:
            return []
        # Run OWL-ViT in CPU by default
        try:
            H, W = img_bgr.shape[:2]
            rgb = _to_rgb(img_bgr)
            if rgb is None:
                return []
            with torch.no_grad():  # type: ignore
                inputs = self._owl_processor(text=[self.prompts], images=rgb, return_tensors="pt")
                outputs = self._owl_model(**inputs)
                # Post-process
                target_sizes = torch.tensor([[H, W]])  # type: ignore
                results = self._owl_processor.post_process_object_detection(outputs=outputs, target_sizes=target_sizes)[0]
                boxes = results["boxes"].cpu().numpy()
                scores = results["scores"].cpu().numpy()
                labels = results["labels"].cpu().numpy()

            out: List[Dict] = []
            for (x1, y1, x2, y2), sc, lid in zip(boxes, scores, labels):
                if float(sc) < self.conf:
                    continue
                x, y = int(max(0, x1)), int(max(0, y1))
                w, h = int(max(0, x2 - x1)), int(max(0, y2 - y1))
                if w <= 2 or h <= 2:
                    continue
                name = str(self.prompts[int(lid)]) if 0 <= int(lid) < len(self.prompts) else "object"
                out.append({"type": name, "position": (x, y, w, h), "score": float(sc), "source": "enhanced"})
            return out
        except Exception:
            return []

    def _detect_rectangles(self, img_bgr) -> List[Dict]:
        if cv2 is None or img_bgr is None or img_bgr.size == 0:
            return []
        try:
            H, W = img_bgr.shape[:2]
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            edges = cv2.Canny(gray, 60, 160)
            edges = cv2.dilate(edges, None, iterations=1)
            cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            min_side = max(10, int(min(W, H) * 0.02))
            res: List[Dict] = []
            for c in cnts:
                x, y, w, h = cv2.boundingRect(c)
                if min(w, h) < min_side:
                    continue
                area = w * h
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.03 * peri, True)
                # Likely rectangle-ish object (screen/paper)
                if len(approx) in (4, 5):
                    ar = w / float(h + 1e-6)
                    if 0.4 <= ar <= 3.0 and area < W * H * 0.6:
                        res.append({
                            "type": "rectangular_device_or_paper",
                            "position": (int(x), int(y), int(w), int(h)),
                            "score": 0.55,
                            "source": "enhanced"
                        })
            return res
        except Exception:
            return []

    def detect(self, img_bgr) -> List[Dict]:
        # Try OWL-ViT first
        out = self._detect_owl(img_bgr)
        # Merge with rectangles if any
        rects = self._detect_rectangles(img_bgr)
        # De-dup by IoU
        def iou(a, b):
            ax1, ay1, aw, ah = a
            bx1, by1, bw, bh = b
            ax2, ay2 = ax1 + aw, ay1 + ah
            bx2, by2 = bx1 + bw, by1 + bh
            x1, y1 = max(ax1, bx1), max(ay1, by1)
            x2, y2 = min(ax2, bx2), min(ay2, by2)
            inter = max(0, x2 - x1) * max(0, y2 - y1)
            if inter <= 0:
                return 0.0
            area_a = aw * ah
            area_b = bw * bh
            return inter / float(area_a + area_b - inter + 1e-6)

        final = out[:]
        for r in rects:
            dup = False
            for o in out:
                if iou(r["position"], o["position"]) > 0.5:
                    dup = True
                    break
            if not dup:
                final.append(r)
        return final

def get_enhanced_object_detector(confidence_threshold: float = 0.20):
    try:
        return EnhancedObjectDetector(confidence_threshold=confidence_threshold)
    except Exception:
        return None
