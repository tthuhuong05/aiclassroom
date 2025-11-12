# services/advanced_proctor_detector.py
import os, re, cv2, numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any
from collections import deque
from PIL import Image
from services.face_recognition_service import get_enhanced_object_detector, get_face_recognition_service
from services.fewshot_action_classifier import FewShotActions

@dataclass
class ProctorResult:
    face_count: int
    attention_score: float
    cheating_detected: bool
    cheating_reason: str
    suspicious_objects: List[Dict[str, Any]]
    entities: List[Dict[str, Any]]

def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None: return float(default)
    s = raw.split('#',1)[0].split('//',1)[0].strip().replace(',', '.')
    m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
    return float(m.group(0)) if m else float(default)

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None: return int(default)
    s = raw.split('#',1)[0].split('//',1)[0].strip()
    m = re.search(r'[-+]?\d+', s)
    return int(m.group(0)) if m else int(default)

class _BoxMemory:
    def __init__(self, iou_thr=0.5, max_age=12):
        self.iou_thr = float(iou_thr); self.max_age = int(max_age)
        self.tracks = []  # [{bbox:[x1,y1,x2,y2], hits:int, age:int, score:float, cls:str}]
        

    @staticmethod
    def _iou(a,b):
        ax1,ay1,ax2,ay2 = a; bx1,by1,bx2,by2 = b
        ix1,iy1 = max(ax1,bx1), max(ay1,by1)
        ix2,iy2 = min(ax2,bx2), min(ay2,by2)
        iw,ih = max(0,ix2-ix1), max(0,iy2-iy1)
        inter = iw*ih
        ua = (ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter + 1e-6
        return inter/ua

    def update(self, dets):
        used = [False]*len(dets)
        for t in self.tracks:
            t['age'] += 1
            best, best_iou = -1, 0.0
            for i,d in enumerate(dets):
                if used[i]: continue
                iou = self._iou(t['bbox'], d['bbox'])
                if iou > best_iou: best, best_iou = i, iou
            if best >= 0 and best_iou >= self.iou_thr:
                used[best] = True; d = dets[best]
                t['bbox'] = d['bbox']; t['score'] = max(t['score'], d.get('score',0.0))
                t['hits'] += 1; t['age'] = 0
        for i,d in enumerate(dets):
            if not used[i]:
                self.tracks.append({'bbox':d['bbox'],'score':d.get('score',0.0),'cls':d.get('type','obj'),'hits':1,'age':0})
        self.tracks = [t for t in self.tracks if t['age'] <= self.max_age]

    def hot(self, min_hits=3):
        return [t for t in self.tracks if t['hits'] >= int(min_hits)]

class AdvancedProctor:
    def __init__(self):
        cascade = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
        self.face_det = cv2.CascadeClassifier(cascade)
        self.min_face = _env_int("MIN_FACE_SIZE", 60)
        
        self.fewshot = FewShotActions(
            root=os.getenv("ATTN_DATASET_DIR","attention_dataset"),
            csv_path=os.getenv("ATTN_ANNOTATIONS"),
            min_score=float(os.getenv("FEWSHOT_MIN_SCORE","0.55"))
        )

        # Open-vocabulary/Enhanced detector (ROI quanh mặt)
        self.ovd = get_enhanced_object_detector(confidence_threshold=float(os.getenv("OVD_CONF", "0.18")))
        raw_names = (os.getenv("OVD_ALERT_NAMES",
                   "phone,cell phone,smartphone,phone screen,book,notebook,paper,sheet of paper,cheat sheet,hand covering face")
                   .split('#',1)[0])
        self.ovd_names_to_alert = {s.strip().lower() for s in raw_names.split(",") if s.strip()}
        self.ovd_overlap_to_alert = _env_float("OVD_IOU_ALERT", 0.12)

        # Temporal memory & votes
        self._mem = _BoxMemory(iou_thr=_env_float("TEMP_IOU", 0.5), max_age=_env_int("TEMP_MAX_AGE", 12))
        self._min_hits = _env_int("TEMP_MIN_HITS", 3)
        self._att_ema = 0.7
        self._ema_alpha = _env_float("ATT_EMA_ALPHA", 0.35)
        self._att_thr = _env_float("ATTENTION_ALERT_THRESHOLD", 0.45)
        self._vote_window = _env_int("CHEAT_ALERT_WINDOW", 5)
        self._vote_need = _env_int("CHEAT_ALERT_FRAMES", 3)
        self._susp_hist = deque(maxlen=self._vote_window)
        self._attlow_hist = deque(maxlen=self._vote_window)
        self.debug = os.getenv("AI_DEBUG", "0") == "1"

    def run(self, bgr: np.ndarray) -> ProctorResult:
        H, W = bgr.shape[:2]
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_det.detectMultiScale(gray, 1.2, 5, minSize=(self.min_face, self.min_face))
        faces_xyxy = [[int(x), int(y), int(x+w), int(y+h)] for (x, y, w, h) in faces]
        face_count = len(faces_xyxy)

        suspicious: List[Dict[str, Any]] = []
        fr_attention = None; fr_att_alert = fr_look = fr_eyes = False

        # 1) Lấy kết quả từ FaceRecognitionService (COCO + attention)
        try:
            FR = get_face_recognition_service()
            fr = FR.detect_faces_and_objects(bgr)
            if isinstance(fr, dict):
                suspicious.extend(fr.get("suspicious_objects", []))
                fr_attention = fr.get("attention_score")
                fr_att_alert = bool(fr.get("attention_alert", False))
                fr_look = bool(fr.get("looking_away", False))
                fr_eyes = bool(fr.get("eyes_closed", False))
                # Gộp mặt từ FR (nếu có)
                if fr.get("faces"):
                    faces_xyxy = []
                    for f in fr["faces"]:
                        if isinstance(f, dict) and "box" in f: faces_xyxy.append([*map(int, f["box"])])
                        elif isinstance(f, dict) and "xywh" in f:
                            x,y,w,h = f["xywh"]; faces_xyxy.append([int(x),int(y),int(x+w),int(y+h)])
                    face_count = len(faces_xyxy) or face_count
        except Exception as e:
            if self.debug: print("[Proctor] FR error:", e)

        # 2) OVD/Enhanced trên ROI quanh mặt
        if face_count > 0 and self.ovd is not None:
            expand = _env_float("OVD_ROI_EXPAND", 0.9)
            for (x1, y1, x2, y2) in faces_xyxy:
                cx, cy = (x1+x2)/2, (y1+y2)/2; w, h = (x2-x1), (y2-y1)
                rw, rh = w*(1.0+expand), h*(1.0+expand)
                rx1, ry1 = max(0, int(cx - rw/2)), max(0, int(cy - rh/2))
                rx2, ry2 = min(W, int(cx + rw/2)), min(H, int(cy + rh/2))
                crop = bgr[ry1:ry2, rx1:rx2]
                for d in (self.ovd.detect(crop) or []):
                    name = str(d.get("type", "object")).lower()
                    if name in self.ovd_names_to_alert:
                        px,py,pw,ph = map(int, d.get("position", (0,0,0,0)))
                        if pw > 0 and ph > 0:
                            gx, gy = rx1 + px, ry1 + py
                            suspicious.append({
                                "type": name, "label": name, "score": float(d.get("score", 0.5)),
                                "bbox": [gx, gy, gx+pw, gy+ph], "near_face": True, "source": "ovd_roi"
                            })
                            
        if face_count > 0 and self.fewshot and self.fewshot.centroids:
          expand = _env_float("OVD_ROI_EXPAND", 0.9)
          for (x1, y1, x2, y2) in faces_xyxy:
             cx, cy = (x1+x2)/2, (y1+y2)/2; w, h = (x2-x1), (y2-y1)
             rw, rh = w*(1.0+expand), h*(1.0+expand)
             rx1, ry1 = max(0, int(cx - rw/2)), max(0, int(cy - rh/2))
             rx2, ry2 = min(W, int(cx + rw/2)), min(H, int(cy + rh/2))
             crop = bgr[ry1:ry2, rx1:rx2]
             pred = self.fewshot.predict(crop)
             if pred.get("is_cheat"):
            # Ghép về cùng format với OVD để vào bước hợp nhất/tracking
                suspicious.append({
                "type": pred["label"] or "cheat_action",
                "label": pred["label"] or "cheat_action",
                "score": float(pred["score"]),
                "bbox": [rx1, ry1, rx2, ry2],
                "near_face": True,
                "source": "fewshot_roi"
                })     

        # 3) Hợp nhất theo IoU & cập nhật bộ nhớ
        merged: List[Dict[str, Any]] = []
        def _iou_xyxy(a,b):
            ax1,ay1,ax2,ay2=a; bx1,by1,bx2,by2=b
            ix1,iy1=max(ax1,bx1),max(ay1,by1); ix2,iy2=min(ax2,bx2),min(ay2,by2)
            inter=max(0,ix2-ix1)*max(0,iy2-iy1)
            ua=(ax2-ax1)*(ay2-ay1)+(bx2-bx1)*(by2-by1)-inter+1e-6
            return inter/ua
        for d in suspicious:
            bb = d.get("bbox") or d.get("position")
            if not bb or len(bb)!=4: continue
            x,y,w_or_x2,h_or_y2 = map(int, bb)
            if w_or_x2<=x or h_or_y2<=y: x1,y1,x2,y2 = x,y,x+w_or_x2,y+h_or_y2
            else: x1,y1,x2,y2 = x,y,w_or_x2,h_or_y2
            keep=True
            for m in merged:
                if m["type"]==d.get("type") and _iou_xyxy([x1,y1,x2,y2], m["bbox_xyxy"])>=self.ovd_overlap_to_alert:
                    if float(d.get("score",0.0))>m["score"]:
                        m["score"]=float(d.get("score",0.0)); m["bbox_xyxy"]=[x1,y1,x2,y2]
                    keep=False; break
            if keep:
                merged.append({"type": d.get("type","unknown"), "score": float(d.get("score",0.0)),
                               "bbox_xyxy": [x1,y1,x2,y2], "near_face": bool(d.get("near_face",False)),
                               "source": d.get("source","unknown")})
        self._mem.update([{"bbox": m["bbox_xyxy"], "score": m["score"], "type": m["type"]} for m in merged])
        hot = self._mem.hot(self._min_hits)

        # 4) EMA attention + voting đa khung
        attention = 0.0 if (face_count==0 or fr_attention is None) else \
                    (_ := setattr(self, "_att_ema", (1.0-self._ema_alpha)*self._att_ema + self._ema_alpha*float(fr_attention))) or float(self._att_ema)
        self._susp_hist.append(1 if hot else 0)
        self._attlow_hist.append(1 if (attention < self._att_thr or fr_att_alert or fr_eyes or fr_look) else 0)

        cheating = False; reasons=[]
        if face_count==0: cheating=True; reasons.append("no_face")
        if sum(self._susp_hist) >= self._vote_need: cheating=True; reasons.append("suspicious_object_consistent")
        if sum(self._attlow_hist) >= self._vote_need: cheating=True; reasons.append("low_attention_consistent")

        return ProctorResult(
            face_count=face_count,
            attention_score=float(attention),
            cheating_detected=cheating,
            cheating_reason=";".join(reasons),
            suspicious_objects=[{"type": m["type"], "score": m["score"], "bbox": m["bbox_xyxy"],
                                 "source": m["source"], "near_face": m["near_face"]} for m in merged],
            entities=[{"kind":"face","box":fb} for fb in faces_xyxy],
        )
