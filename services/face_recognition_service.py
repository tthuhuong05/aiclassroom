# -*- coding: utf-8 -*-
"""
Face Recognition & Suspicious Object Service — v3.6 (risk-scored)
--------------------------------------------------------------
Focus of this update: fix _hard_bypass crash + stabilize pre-arm masking.
Key changes from v3.4:
1) Define all *_hard_bypass* knobs in __init__ with safe defaults (OFF by default).
2) Rewrite the pre-arm hard-bypass block to use _Track fields (no dict .get calls).
3) Keep objects masked before 'armed' while optionally letting only high-confidence,
   stable, near-face cheat-tools leak through when HARD_BYPASS_BEFORE_ARM=1.
4) Small safety: recompute suspicious_count after masking; avoid NameErrors.
5) Extra debug in _empty_result to make backend load issues visible via debug_status().

Env knobs (defaults in code; can be overridden in .env):
- WARMUP_SEC=2.0
- WARMUP_FRAMES=8
- MASK_OBJECTS_BEFORE_ARM=1
- SUPPRESS_ATTENTION_BEFORE_ARM=1
- PROCTOR_GRACE_SEC (existing)  | ARM_FACE_MIN_FRAMES (existing)
- PROCTOR_COOLDOWN_SEC=3.0      | OBJ_MIN_TRACK_FRAMES (existing)
- HARD_BYPASS_BEFORE_ARM=0      | HARD_BYPASS_CLASSES=cell phone,book,paper,rectangular_device_or_paper
- HARD_BYPASS_CONF=0.70         | HARD_BYPASS_HITS=3
- HARD_BYPASS_REQUIRE_NEAR=1    | SUS_ONLY_NEAR_FACE=1
"""

from __future__ import annotations
from io import BytesIO
from typing import Dict, Optional, List, Tuple
import base64, os, time
from collections import Counter, deque

import numpy as np
from PIL import Image
import cv2

# --- Robust ENV readers (safe with inline comments and commas) ---
def _envf(key: str, default: float) -> float:
    raw = os.getenv(key, str(default))
    try:
        s = str(raw).split('#', 1)[0].strip().replace(',', '.')
        return float(s)
    except Exception:
        return float(default)

def _envi(key: str, default: int) -> int:
    raw = os.getenv(key, str(default))
    try:
        s = str(raw).split('#', 1)[0].strip()
        # allow "1,000" style
        s = s.replace(',', '')
        return int(float(s))
    except Exception:
        return int(default)

# ---- Optional MediaPipe ----
try:
    import mediapipe as mp
    _HAS_MP = True
    _mp_face_det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.2)
    # FaceMesh for attention/landmarks
    _mp_face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False, max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5, min_tracking_confidence=0.5
    )
except Exception:
    _HAS_MP = False
    _mp_face_det = None
    _mp_face_mesh = None


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0/(1.0+np.exp(-x))


# ---------- Simple IoU-based tracker ----------
# ---------- Simple IoU-based tracker ----------
class _Track:
    __slots__ = ("id","box","hit","last_t","label","near_face","score")
    def __init__(self, tid: int, det: Dict):
        self.id = tid
        self.box = det["position"]              # (x,y,w,h)
        self.label = str(det.get("type","object"))
        self.near_face = bool(det.get("near_face", False))
        self.score = float(det.get("score", 0.0))
        self.hit = 1
        self.last_t = time.time()


def _iou_xywh(a: Tuple[int,int,int,int], b: Tuple[int,int,int,int]) -> float:
    ax,ay,aw,ah = a; bx,by,bw,bh = b
    a1,a2 = ax, ay; a3,a4 = ax+aw, ay+ah
    b1,b2 = bx, by; b3,b4 = bx+bw, by+bh
    x1, y1 = max(a1,b1), max(a2,b2)
    x2, y2 = min(a3,b3), min(a4,b4)
    inter = max(0, x2-x1) * max(0, y2-y1)
    ua = aw*ah + bw*bh - inter + 1e-6
    return inter/ua

def _same_class(a: Dict, b: Dict) -> bool:
    return (a.get("type") or "") == (b.get("type") or "")

class _TrackMgr:
    def __init__(self, iou_min=0.30, req_frames=1, stale_s=2.0):  # Giảm từ 2 xuống 1 để phát hiện nhanh hơn
        self.iou_min = float(iou_min)
        self.req_frames = int(req_frames)
        self.stale_s = float(stale_s)
        self.tracks: List[_Track] = []
        self.next_id = 1
        
    def update(self, detections: List[Dict]) -> List[_Track]:
        now = time.time()
        # loại track quá cũ
        self.tracks = [t for t in self.tracks if (now - t.last_t) <= self.stale_s]
        used = set()

        # ghép theo IoU + cùng lớp
        for det in detections:
            best_i, best_iou = -1, 0.0
            for i, tr in enumerate(self.tracks):
                if i in used: continue
                if not _same_class({"type": tr.label}, det): continue
                iou = _iou_xywh(tr.box, det["position"])
                if iou >= self.iou_min and iou > best_iou:
                    best_i, best_iou = i, iou
            if best_i >= 0:
                tr = self.tracks[best_i]
                tr.box = det["position"]
                tr.near_face = det.get("near_face", tr.near_face)
                tr.score = max(tr.score, float(det.get("score",0.0)))
                tr.hit += 1
                tr.last_t = now
                used.add(best_i)
            else:
                self.tracks.append(_Track(self.next_id, det))
                self.next_id += 1

        # chỉ trả track đủ ổn định
        return [t for t in self.tracks if t.hit >= self.req_frames]



class FaceRecognitionService:
    def __init__(self):
        self._dbg = (os.getenv("AI_DEBUG","0").strip() in ("1","true","yes","on"))
        self._init_log: List[str] = []
        
        

        # ---- Policy knobs ----
        self._warmup_sec = self._env_float("WARMUP_SEC", 2.0)
        self._warmup_frames_need = _envi("WARMUP_FRAMES", 8)
        self._near_face_delay = self._env_float("NEAR_FACE_DELAY_SEC", 2.5)
        self._mask_before_arm = self._env_bool("MASK_OBJECTS_BEFORE_ARM", "1")
        self._suppress_attention_before_arm = self._env_bool("SUPPRESS_ATTENTION_BEFORE_ARM", "1")
        self._cooldown_sec = self._env_float("PROCTOR_COOLDOWN_SEC", 0.0)
        
        # --- AutoBoost defaults ---
        self._no_obj_frames = 0
        self._autoboost_trig  = _envi("AUTOBOOST_TRIG_FRAMES", 6)
        self._autoboost_win   = self._env_float("AUTOBOOST_WIN_SEC", 2.0)
        self._autoboost_conf  = self._env_float("AUTOBOOST_OBJ_CONF_ROI", 0.06)
        self._autoboost_scale = self._env_float("AUTOBOOST_EXTRA_SCALE", 3.2)
        self._autoboost_until = 0.0
        self._roi_autoboost_active = False

        # --- NEW: hard bypass knobs (fix AttributeError, default OFF) ---
        self._hard_bypass = self._env_bool("HARD_BYPASS_BEFORE_ARM", "0")
        _hb_list = self._env_list("HARD_BYPASS_CLASSES")
        if _hb_list:
            self._hard_bypass_classes = {s.lower() for s in _hb_list}
        else:
            self._hard_bypass_classes = {
                "cell phone","mobile phone","phone","smartphone",
                "book","paper","sheet of paper","rectangular_device_or_paper"
            }
        self._hard_bypass_conf = self._env_float("HARD_BYPASS_CONF", 0.70)
        self._hard_bypass_hits = _envi("HARD_BYPASS_HITS", 3)
        self._hard_bypass_require_near = self._env_bool("HARD_BYPASS_REQUIRE_NEAR", "1")

        # Face backends
        self._yolo_face_net = None           # OpenCV DNN
        self._yolo_face_ort = None           # ORT session
        self._yolo_face_backend = None       # "yolov8-face"|"yolov5-face"
        self._haar = None
        self._dnn_face = None                # Caffe-SSD

        # Object backends
        self._obj_dnn = None                 # OpenCV DNN YOLO/SSD wrapper
        self._obj_ort = None                 # ORT session
        self._obj_names: List[str] = []
        self._obj_backend = None             # "yolo"|"yolo_ort"|"ssd"

        # State (debounce/arming-lite)
        self._session_started_at: Optional[float] = None
        self._warmup_frames = 0
        self._face_seen_once: bool = False
        self._votes: deque[str] = deque(maxlen=_envi("CHEAT_VOTE_WIN", 12))
        self._vote_win = _envi("CHEAT_VOTE_WIN", 12)
        self._req_susp = _envi("CHEAT_REQ_SUSP", 6)
        self._req_mf   = _envi("CHEAT_REQ_MF", 6)
        self._req_nf   = _envi("CHEAT_REQ_NF", 8)
        self._grace_s  = _envf("PROCTOR_GRACE_SEC", 3.0)
        self._arm_min_frames = _envi("ARM_FACE_MIN_FRAMES", 8)
        self._face_stable_frames = 0
        self._mf_min_ratio = self._env_float("MF_MIN_SIZE_RATIO", 0.55)  # mặt phụ phải đủ lớn so với mặt chính
        self._cooldown_until = 0.0
        self._state = "INIT"
        self._last_dbg = {}
        # ---- Gating states (v3.7) ----
        self._last_infer_t: Optional[float] = None
        self._att_accum_s: float = 0.0
        self._armed_since: Optional[float] = None

        # ---- Risk scoring knobs (new in v3.6) ----
        self._risk_w_class  = self._env_float("RISK_W_CLASS", 0.25)   # Giảm từ 0.35
        self._risk_w_near   = self._env_float("RISK_W_NEAR", 0.40)   # Tăng từ 0.25 - ƯU TIÊN near_face
        self._risk_w_size   = self._env_float("RISK_W_SIZE", 0.15)
        self._risk_w_stable = self._env_float("RISK_W_STABLE",0.10)   # Giảm từ 0.15
        self._risk_w_att    = self._env_float("RISK_W_ATT",   0.10)
        self._risk_min      = self._env_float("SUSP_MIN_RISK", 0.45)  # Giảm từ 0.55 để phát hiện dễ hơn
        self._risk_min_prearm = self._env_float("SUSP_MIN_RISK_PREARM", max(0.0, self._risk_min-0.10))
        self._prearm_surface_susp = self._env_bool("PREARM_SURFACE_SUSP", "0")
        # class base risk (0..1). You can override with env JSON later if needed
        self._risk_class_base = {
            "cell phone": 0.95, "mobile phone": 0.95, "phone": 0.95, "smartphone": 0.95,
            "laptop": 0.85, "notebook": 0.85, "tablet": 0.85,
            "book": 0.75, "paper": 0.65, "sheet of paper": 0.65,
            "keyboard": 0.50, "mouse": 0.45, "remote": 0.40,
            "monitor": 0.40, "tv": 0.40,
            "rectangular_device_or_paper": 0.60
        }
        self._ear_zone_scale = self._env_float("EAR_ZONE_SCALE", 1.25)

        # ---- Fast-lane blocking (v3.6.3) ----
        self._fast_block = self._env_bool("FAST_BLOCK", "1")
        fb_classes = self._env_list("FAST_BLOCK_CLASSES")
        if fb_classes:
          self._fast_block_classes = {c.strip().lower() for c in fb_classes}
        else:
            self._fast_block_classes = {
                "cell phone","mobile phone","phone","smartphone",
                "tablet","book","paper","rectangular_device_or_paper"
            }

        self._fast_block_risk = self._env_float("FAST_BLOCK_RISK", 0.78)
        self._fast_block_frames = _envi("FAST_BLOCK_FRAMES", 2)
        self._fast_hits: Dict[str, int] = {}

        # ---- Start-up/Gating knobs (v3.7) ----
        self._cheat_start_delay = self._env_float("CHEAT_START_DELAY_SEC", 4.0)
        self._susp_require_att  = self._env_bool("SUSP_REQUIRE_ATT_BASELINE", "1")
        self._susp_hold_until = 0.0
        self._susp_hold_sec   = self._env_float("SUSP_HOLD_SEC", 1.5)
        self._susp_hold_calls = 0
        self._susp_hold_calls_need = _envi("SUSP_HOLD_CALLS", 3)
        self._attn_base_sec     = self._env_float("ATTN_BASELINE_SEC", 3.0)
        self._attn_base_min     = self._env_float("ATTN_BASELINE_MIN", 0.55)
        self._fast_block_delay  = self._env_float("FAST_BLOCK_DELAY_SEC", 3.0)

        # Geometry / thresholds
        self._coco_classes = {
            "cell phone","mobile phone","phone","smartphone",
            "laptop","notebook","tablet",
            "book","paper","sheet of paper",
            "mouse","keyboard","remote","monitor","tv"
        }

        # NEW: object tracker
        self._tracker = _TrackMgr()

        self._init_face_backends()
        self._init_object_backends()
        self._warmup()

    # ---------- Utils ----------
    def _log(self, *a):
        if self._dbg:
            print("[FRS]", *a)

    @staticmethod
    def _resolve(path: str) -> Optional[str]:
        """Try as-is, then CWD+path, then module_dir+path."""
        if not path:
            return None
        p = path if os.path.isabs(path) else os.path.abspath(path)
        if os.path.exists(p):
            return p
        cwdp = os.path.abspath(os.path.join(os.getcwd(), path))
        if os.path.exists(cwdp):
            return cwdp
        import os as _os
        mdir = _os.path.dirname(__file__)
        mpath = _os.path.abspath(os.path.join(mdir, path))
        if _os.path.exists(mpath):
            return mpath
        return None

    @staticmethod
    def _env_float(key: str, default) -> float:
        raw = os.getenv(key)
        if raw is None:
            return float(default)
        s = raw.split('#', 1)[0].split('//', 1)[0].strip().replace(',', '.')
        import re
        m = re.search(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', s)
        return float(m.group(0)) if m else float(default)

    @staticmethod
    def _env_bool(key: str, default: str = "0") -> bool:
        v = (os.getenv(key, default) or "").strip().lower()
        return v in ("1", "true", "yes", "on")

    @staticmethod
    def _env_list(key: str) -> List[str]:
        raw = os.getenv(key)
        if not raw:
            return []
        return [t.strip() for t in raw.split('#', 1)[0].split(',') if t.strip()]

    # ---------- Model init ----------
    def _init_face_backends(self):
        # Haar
        try:
            p = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if os.path.exists(p):
                cas = cv2.CascadeClassifier(p)
                if not cas.empty():
                    self._haar = cas
                    self._init_log.append(f"Haar OK: {p}")
        except Exception as e:
            self._init_log.append(f"Haar fail: {e}")

        # Caffe DNN face (res10)
        try:
            base = os.path.join(os.path.dirname(__file__), "models", "face_detector")
            proto = os.path.join(base, "deploy.prototxt")
            caff  = os.path.join(base, "res10_300x300_ssd_iter_140000.caffemodel")
            if os.path.exists(proto) and os.path.exists(caff):
                self._dnn_face = cv2.dnn.readNetFromCaffe(proto, caff)
                self._init_log.append("Caffe-SSD face OK")
        except Exception as e:
            self._init_log.append(f"Caffe face fail: {e}")

        # YOLO-face ONNX
        paths = []
        env = (os.getenv("YOLO_FACE_ONNX") or "").strip()
        rp = self._resolve(env) if env else None
        if rp: paths.append(rp)
        base = os.path.join(os.path.dirname(__file__), "models", "face_detector")
        for n in ["yolov8n-face.onnx","yolov8s-face.onnx","yolov5n-face.onnx","yolov5s-face.onnx"]:
            p = os.path.join(base, n)
            if os.path.exists(p): paths.append(p)

        for p in paths:
            try:
                self._yolo_face_net = cv2.dnn.readNetFromONNX(p)
                self._yolo_face_backend = "yolov8-face" if "yolov8" in os.path.basename(p).lower() else "yolov5-face"
                self._init_log.append(f"YOLO-face OpenCV DNN OK: {p}")
                return
            except Exception as e:
                self._init_log.append(f"YOLO-face OpenCV fail: {p} -> {e}")
                self._yolo_face_net = None

        for p in paths:
            try:
                import onnxruntime as ort
                self._yolo_face_ort = ort.InferenceSession(p, providers=['CPUExecutionProvider'])
                self._yolo_face_backend = "yolov8-face" if "yolov8" in os.path.basename(p).lower() else "yolov5-face"
                self._init_log.append(f"YOLO-face ORT OK: {p}")
                return
            except Exception as e:
                self._init_log.append(f"YOLO-face ORT fail: {p} -> {e}")
                self._yolo_face_ort = None

    def _init_object_backends(self):
        env_yolo = (os.getenv("COCO_ONNX") or "").strip()
        env_names = (os.getenv("COCO_CLASSES_FILE") or os.getenv("COCO_CLASSES") or "").strip()

        base = os.path.join(os.path.dirname(__file__), "models", "coco")
        names = self._resolve(env_names) if env_names else os.path.join(base, "coco.names")
        yolo  = self._resolve(env_yolo)  if env_yolo  else os.path.join(base, "yolov5s.onnx")

        # OpenCV DNN YOLO
        if os.path.exists(yolo) and os.path.exists(names):
            try:
                self._obj_dnn = cv2.dnn.readNetFromONNX(yolo)
                with open(names, "r", encoding="utf-8") as f:
                    self._obj_names = [ln.strip() for ln in f if ln.strip()]
                self._obj_backend = "yolo"
                self._init_log.append(f"COCO OpenCV DNN OK: {yolo}")
                return
            except Exception as e:
                self._init_log.append(f"COCO OpenCV fail: {e}")
                self._obj_dnn = None

        # ONNX Runtime
        if os.path.exists(yolo) and os.path.exists(names):
            try:
                import onnxruntime as ort
                self._obj_ort = ort.InferenceSession(yolo, providers=['CPUExecutionProvider'])
                with open(names, "r", encoding="utf-8") as f:
                    self._obj_names = [ln.strip() for ln in f if ln.strip()]
                self._obj_backend = "yolo_ort"
                self._init_log.append(f"COCO ORT OK: {yolo}")
                return
            except Exception as e:
                self._init_log.append(f"COCO ORT fail: {e}")
                self._obj_ort = None

        # SSD fallback
        try:
            pb = os.path.join(base, "frozen_inference_graph.pb")
            pbt = os.path.join(base, "ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt")
            if os.path.exists(pb) and os.path.exists(pbt) and os.path.exists(names):
                net = cv2.dnn_DetectionModel(pb, pbt)
                net.setInputSize(320, 320)
                net.setInputScale(1.0/127.5)
                net.setInputMean((127.5,127.5,127.5))
                net.setInputSwapRB(True)
                self._obj_dnn = net
                with open(names, "r", encoding="utf-8") as f:
                    self._obj_names = [ln.strip() for ln in f if ln.strip()]
                self._obj_backend = "ssd"
                self._init_log.append("COCO SSD fallback OK")
        except Exception as e:
            self._init_log.append(f"COCO SSD fail: {e}")
            self._obj_backend = None

    def _warmup(self):
        try:
            fake = np.zeros((320, 480, 3), dtype=np.uint8)
            _ = self._detect_faces(fake)
            _ = self._detect_objects(fake)
            self._init_log.append("Warmup OK")
        except Exception as e:
            self._init_log.append(f"Warmup fail: {e}")

    # ---------- Public helpers ----------
    def is_available(self) -> bool:
        return any([self._yolo_face_net, self._yolo_face_ort, self._haar, self._dnn_face])

    def debug_status(self) -> Dict[str, object]:
        return {
            "yolo_face": bool(self._yolo_face_net or self._yolo_face_ort),
            "yolo_face_backend": "ort" if self._yolo_face_ort else ("opencv_dnn" if self._yolo_face_net else "unloaded"),
            "mediapipe_face": bool(_HAS_MP and _mp_face_det is not None),
            "mediapipe_facemesh": bool(_HAS_MP and _mp_face_mesh is not None),
            "haar": bool(self._haar),
            "dnn_face": bool(self._dnn_face),
            "coco_backend": self._obj_backend or "unloaded",
            "init_log": list(self._init_log),
            "state": self._state,
            "policy": {
                "warmup_sec": self._warmup_sec,
                "warmup_frames": self._warmup_frames_need,
                "mask_before_arm": self._mask_before_arm,
                "suppress_attention_before_arm": self._suppress_attention_before_arm,
                "cooldown_sec": self._cooldown_sec,
                "hard_bypass": self._hard_bypass
            }
        }

    # ==================================================================
    def detect_faces_and_objects(self, image_input):
        faces_raw: List[Tuple[int,int,int,int]] = []
        dbg = {"decode": None, "faces_before_filter": 0}
            # --- defaults to avoid UnboundLocalError even if attention calc is skipped ---
        attention = 0.5
        look_away = False
        eyes_closed = False
        mouth_open = False
        pose = None
        try:
            img = self._coerce_to_bgr(image_input)
            if isinstance(image_input, str):
              s = image_input.strip()
              if os.path.exists(s) and os.path.isfile(s):
                 with open(s, "rb") as f:
                    img = self._coerce_to_bgr(f.read())
            if img is None or getattr(img, "size", 0) == 0:
                return self._empty_result("Empty/invalid image", alert=True)
            
            


            H, W = img.shape[:2]
            dbg["decode"] = {"H": H, "W": W}

            if max(H, W) > 1280:
                scale = 1280.0/float(max(H,W))
                img = cv2.resize(img, (int(W*scale), int(H*scale)), interpolation=cv2.INTER_LINEAR)
                H, W = img.shape[:2]

            img = self._enhance_for_detection(img)

            now = time.time()
            # time delta for attention accumulation (safe default if first frame)
            dt = 0.0
            if self._last_infer_t is not None:
                dt = max(0.0, now - self._last_infer_t)
            self._last_infer_t = now
            if self._session_started_at is None:
                self._session_started_at = now
                self._warmup_frames = 0
                self._state = "WARMUP"

            # ---- Faces ----
            faces_raw = self._detect_faces(img)
            dbg["faces_before_filter"] = len(faces_raw)

            # --- Filter out tiny secondary faces to avoid false "multiple faces" ---
            faces_raw = list(faces_raw)
            if faces_raw:
                areas = [(w*h) for (x,y,w,h) in faces_raw]
                try:
                    import numpy as _np
                    main_i = int(_np.argmax(areas))
                except Exception:
                    main_i = max(range(len(areas)), key=lambda i: areas[i])
                main_area = float(areas[main_i]) if areas else 0.0
                keep = []
                for i,(x,y,w,h) in enumerate(faces_raw):
                    if i == main_i or (w*h) >= (main_area * float(getattr(self, "_mf_min_ratio", 0.55))):
                        keep.append((x,y,w,h))
                faces_raw = keep
    
            faces = [{"bbox":[x,y,x+w,y+h], "score":0.8} for (x,y,w,h) in faces_raw]
            face_count = len(faces)

            # ---- EARLY attention computation (moved up in v3.6.1 to avoid UnboundLocalError) ----
            if faces_raw:
                main_face = max(faces_raw, key=lambda b: b[2]*b[3])
                att, look_away, eyes_closed, mouth_open, pose = self._compute_attention_with_facemesh(img, main_face)
            else:
                att, look_away, eyes_closed, mouth_open, pose = 0.0, False, False, False, None
            attention = float(att)
            # accumulate attention baseline time (only when attentive and not looking away)
            if face_count >= 1 and (attention >= self._attn_base_min) and (not look_away):
                self._att_accum_s = min(self._attn_base_sec + 5.0, self._att_accum_s + dt)
            else:
                # gentle decay so short hiccups don't reset completely
                self._att_accum_s = max(0.0, self._att_accum_s - dt*0.5)

            # ---- Objects (global + near-face ROI) ----
            objects_all, suspicious_pre = self._detect_objects(img)
            extra_roi = self._roi_near_faces(img, faces_raw)

            def _xyxy(pos):
                x,y,w,h = pos
                return (x, y, x+w, y+h)

            def _iou(a,b):
                x1=max(a[0],b[0]); y1=max(a[1],b[1])
                x2=min(a[2],b[2]); y2=min(a[3],b[3])
                w=max(0,x2-x1); h=max(0,y2-y1)
                inter=w*h
                if inter==0: return 0.0
                aa=(a[2]-a[0])*(a[3]-a[1]); bb=(b[2]-b[0])*(b[3]-b[1])
                return inter/float(aa+bb-inter+1e-6)

            merged = list(objects_all)
            for e in extra_roi:
                ex = _xyxy(e["position"])
                if all(_iou(ex, _xyxy(o["position"])) <= 0.45 for o in merged):
                    merged.append(e)

            faces_xyxy = [(x,y,x+w,y+h) for (x,y,w,h) in faces_raw]
            only_near  = self._env_bool("SUS_ONLY_NEAR_FACE","1")
            expand     = self._env_float("NEAR_FACE_EXPAND",4.0)  # Tăng từ 3.0 lên 4.0 để phát hiện rộng hơn nhiều
            iou_min    = self._env_float("NEAR_FACE_MIN_IOU",0.005)  # Giảm từ 0.01 xuống 0.005 để nhạy hơn nhiều
            dist_ratio = self._env_float("NEAR_FACE_DIST",0.80)    # Tăng từ 0.65 lên 0.80 để phát hiện xa hơn nhiều

            def _near(box_xyxy):
                if not faces_xyxy:
                    return False
                for fb in faces_xyxy:
                    if self._near_face(box_xyxy, fb, expand, iou_min, dist_ratio):
                        return True
                return False

            # Full objects list (for UI)
            objects: List[Dict] = []
            for o in merged:
                x,y,w,h = o["position"]
                bx = (x,y,x+w,y+h); near = _near(bx)
                objects.append({
                    "bbox":[x,y,x+w,y+h],
                    "score": float(o.get("score",0.0)),
                    "label": str(o.get("type") or o.get("label") or "object"),
                    "type":  str(o.get("type") or o.get("label") or "object"),
                    "near_face": bool(near),
                    "source": o.get("source","dnn")
                })

            # Enrich suspicious_pre with near_face before tracking
            enriched_pre = []
            for s in suspicious_pre or []:
                x,y,w,h = s["position"]
                bx = (x,y,x+w,y+h); near = _near(bx)
                enriched_pre.append({
                    "position": (x,y,w,h),
                    "type": s.get("type","object"),
                    "score": float(s.get("score",0.0)),
                    "near_face": bool(near),
                    "source": s.get("source","dnn")
                })

            # ---- Tracking suspicious (stabilize across frames) ----
            stable_tracks = self._tracker.update(enriched_pre)

            # Build quick track index by IoU to reuse stability info
            def _track_for(o_xywh, label):
                ox,oy,ow,oh = o_xywh
                ob = (ox,oy,ox+ow,oy+oh)
                best=None; best_iou=0.0
                for t in stable_tracks:
                    if t.label != label: continue
                    tx,ty,tw,th = t.box
                    tb = (tx,ty,tx+tw,ty+th)
                    i = self._iou(ob, tb)
                    if i > best_iou:
                        best, best_iou = t, i
                return best, best_iou

            # Risk-scored suspicious selection (v3.6)
            suspicious: List[Dict] = []
            sus_debug: List[Dict] = []
            allow_only_near = self._env_bool("SUS_ONLY_NEAR_FACE","1")

            frame_area = float(max(1, W*H))
            main_face_xywh = max(faces_raw, key=lambda b: b[2]*b[3]) if faces_raw else None

            for o in objects:
                lbl = (o.get("type") or o.get("label") or "object").lower()
                
                # BỎ QUA filter class nếu object gần mặt - BẤT KỲ object nào gần mặt đều là gian lận
                x1,y1,x2,y2 = o["bbox"]
                ow,oh = max(0,x2-x1), max(0,y2-y1)
                if ow==0 or oh==0: continue
                size_frac = ((ow*oh)/frame_area) ** 0.5
                near = bool(o.get("near_face", False))
                
                # QUAN TRỌNG: Nếu object gần mặt HOẶC ở cạnh mặt, BẤT KỲ object nào đều là gian lận
                # Bỏ qua class filter hoàn toàn cho objects gần mặt
                if not near:
                    # Chỉ filter class nếu object KHÔNG gần mặt
                    class_set = {s.strip().lower() for s in (self._env_list("SUSPICIOUS_CLASSES") or self._env_list("CHEAT_CLASSES"))}
                    # Nếu có class set, chỉ lọc theo set. Nếu không có, lấy tất cả (trừ person)
                    if class_set and lbl not in class_set and lbl != "rectangular_device_or_paper":
                        continue
                else:
                    # Object gần mặt - BẤT KỲ object nào (trừ person) đều là gian lận
                    # Không cần filter class nữa
                    pass
                
                tr,iou = _track_for((x1,y1,ow,oh), lbl)
                hits = int(getattr(tr, "hit", 1)) if tr else 1
                conf = float(o.get("score",0.0))
                near_ear = False
                if main_face_xywh and lbl in {"cell phone","mobile phone","phone","smartphone","tablet"}:
                    near_ear = self._near_ear(main_face_xywh, (x1,y1,ow,oh))
                # face occlusion fraction
                occl_frac = 0.0
                if main_face_xywh:
                    fx,fy,fw,fh = main_face_xywh
                    fa = max(1.0, float(fw*fh))
                    inter_x1 = max(x1, fx); inter_y1 = max(y1, fy)
                    inter_x2 = min(x2, fx+fw); inter_y2 = min(y2, fy+fh)
                    iw = max(0, inter_x2 - inter_x1); ih = max(0, inter_y2 - inter_y1)
                    occl_frac = float(iw*ih)/fa
                
                # Nếu object gần mặt, tăng risk base lên cao
                risk_base_multiplier = 2.0 if near else 1.0  # Tăng 100% nếu gần mặt (từ 1.5 lên 2.0)
                risk = self._risk_score(
                    lbl,                # nhãn của object hiện tại
                    near,               # "gần mặt" của object hiện tại
                    size_frac,          # kích thước đã tính: ((ow*oh)/frame_area)**0.5
                    hits,               # độ ổn định từ track (nếu có), mặc định 1
                    conf,               # score detector
                    attention,          # attention khung hình
                    near_ear,           # riêng cho phone/tablet
                    occl_frac           # tỉ lệ che mặt đã tính
                )
                risk = min(1.0, risk * risk_base_multiplier)  # Áp dụng multiplier

                near_override = (near_ear or (occl_frac >= self._env_float("OCCL_MIN_FOR_NEAR", 0.10)))  # Giảm từ 0.12 xuống 0.10
                gate_near = (not allow_only_near) or near or near_override
                
                # Nếu object gần mặt, giảm threshold xuống để phát hiện dễ hơn
                effective_risk_min = self._risk_min * (0.4 if near else 1.0)  # Giảm 60% nếu gần mặt (từ 0.6 xuống 0.4)
                
                if gate_near and risk >= effective_risk_min:
                    suspicious.append({
                        "bbox":[x1,y1,x2,y2],
                        "score": max(conf, risk),
                        "label": lbl, "type": lbl,
                        "near_face": near,
                        "source": o.get("source","risk"),
                        "hits": hits, "risk": risk,
                        "near_ear": bool(near_ear),
                        "occl_frac": float(occl_frac)
                    })
                sus_debug.append({"label": lbl, "near": near, "risk": risk, "hits": hits, "conf": conf, "size": size_frac, "near_ear": near_ear})

            # Nếu có tracks gần mặt, đánh dấu ngay (bất kỳ object nào)
            for t in stable_tracks:
                if t.label.lower() == "person": continue  # Bỏ qua person
                if allow_only_near and not t.near_face: continue
                
                x,y,w,h = t.box
                risk = self._risk_score(
                   t.label, t.near_face, ((w*h)/frame_area)**0.5,
                   t.hit, t.score, attention, False, 0.0
                )
                
                # Nếu gần mặt, giảm threshold
                effective_risk_min = self._risk_min * (0.6 if t.near_face else 1.0)
                
                # Kiểm tra xem đã có trong suspicious chưa
                already_added = any(
                    abs(s.get("bbox", [0,0,0,0])[0] - x) < 10 and 
                    abs(s.get("bbox", [0,0,0,0])[1] - y) < 10
                    for s in suspicious
                )
                
                if not already_added and risk >= effective_risk_min:
                        suspicious.append({
                            "bbox":[x,y,x+w,y+h],
                            "score": max(t.score, risk),
                            "label": t.label, "type": t.label,
                            "near_face": bool(t.near_face),
                            "source": "tracker", "hits": int(t.hit), "risk": risk
                        })

            object_count = len(objects)
            suspicious_count = len(suspicious)

            dbg["sus_scores"] = sus_debug
            # Latch: nếu vừa thấy nghi vấn thì giữ trạng thái trong ~SUSP_HOLD_SEC
            # Latch: giữ nghi vấn theo thời gian + theo số LẦN GỌI detect()
            if suspicious_count > 0:
              self._susp_hold_until = max(self._susp_hold_until, now + float(self._susp_hold_sec))
              self._susp_hold_calls = int(self._susp_hold_calls_need)
            else:
              if self._susp_hold_calls > 0:
                  self._susp_hold_calls -= 1
            hold_active = (now < self._susp_hold_until) or (self._susp_hold_calls > 0)
            dbg["susp_hold"] = bool(hold_active)



            # ---- Fast-lane accumulation for high-risk objects (v3.6.3) ----
            if self._fast_block:
                seen_fast = set()
                for s in suspicious:
                    lbl = (s.get("label") or s.get("type") or "").lower()
                    if lbl in self._fast_block_classes:
                        rk = float(s.get("risk", s.get("score", 0.0)))
                        if rk >= float(self._fast_block_risk) and (bool(s.get("near_face")) or bool(s.get("near_ear"))):
                            self._fast_hits[lbl] = int(self._fast_hits.get(lbl, 0)) + 1
                            seen_fast.add(lbl)
                # decay non-seen classes
                for k in list(self._fast_hits.keys()):
                    if k not in seen_fast:
                        v = int(self._fast_hits.get(k, 0)) - 1
                        if v <= 0:
                            self._fast_hits.pop(k, None)
                        else:
                            self._fast_hits[k] = v
                dbg["fast_hits"] = dict(self._fast_hits)
            else:
                self._fast_hits.clear(); dbg["fast_hits"] = {}

            # ---- Attention via FaceMesh/Head pose ----
            # (already computed earlier in v3.6.1 to feed risk scoring)

            # ---- State machine: WARMUP + ARMING + MONITORING ----
            self._warmup_frames += 1
            in_warmup = ((now - self._session_started_at) < self._warmup_sec) or (self._warmup_frames < self._warmup_frames_need)
            if in_warmup:
                self._state = "WARMUP"
            # Update face stability counters
            if face_count >= 1:
                self._face_seen_once = True
                self._face_stable_frames += 1
            else:
                self._face_stable_frames = 0

            armed = self._face_seen_once and (not in_warmup) and \
                    ((now - self._session_started_at) >= self._grace_s) and \
                    (self._face_stable_frames >= self._arm_min_frames)
            self._state = ("MONITORING" if armed else ("SEEK_FACE" if not in_warmup else "WARMUP"))
            # armed-since timestamp
            if armed and self._armed_since is None:
                self._armed_since = now
            if not armed:
                self._armed_since = None
            in_cooldown = (now < self._cooldown_until)

            # ---- Mask outputs before 'armed' (critical for UX) ----
            masked_reason = None
            if not armed:
                if self._prearm_surface_susp:
                    # Keep suspicious list visible for UI/QA during warmup, but apply a softer pre-arm threshold
                    # and never escalate to warn/block via policy gates (handled later).
                    # If any items have a 'risk' field, re-filter by prearm threshold.
                    if suspicious:
                        if any(('risk' in s) for s in suspicious):
                            suspicious = [s for s in suspicious if float(s.get('risk', 0.0)) >= float(self._risk_min_prearm)]
                    masked_reason = "prearm_surface_susp"
                    # Optionally still hide cheat-classes from the general objects overlay pre-arm
                    if self._mask_before_arm:
                        cheat_alias = set(self._env_list("SUSPICIOUS_CLASSES")) or set(self._env_list("CHEAT_CLASSES"))
                        cheat_alias = {c.lower() for c in cheat_alias} if cheat_alias else set()
                        def is_cheat(name: str) -> bool:
                            n = (name or "").lower()
                            if cheat_alias:
                                return n in cheat_alias
                            return n in {"cell phone","phone","mobile phone","smartphone","laptop","notebook","tablet","book","paper","sheet of paper","keyboard","mouse","remote","monitor","tv","rectangular_device_or_paper"}
                        objects = [o for o in objects if not is_cheat(o.get("type") or o.get("label"))]
                        object_count = len(objects)
                    suspicious_count = len(suspicious)
                else:
                    # default legacy behavior: do not surface suspicious before armed, unless hard-bypass allows
                    bypassed: List[Dict] = []
                    if self._hard_bypass:
                        for t in stable_tracks:
                            label = (t.label or "").lower()
                            conf  = float(t.score); hits = int(t.hit); nearf = bool(t.near_face)
                            if (label in self._hard_bypass_classes and conf >= self._hard_bypass_conf and hits >= self._hard_bypass_hits and (nearf or not self._hard_bypass_require_near)):
                                x,y,w,h = t.box
                                risk = self._risk_score(
                                    t.label, t.near_face, ((w*h)/frame_area)**0.5,
                                    t.hit, t.score, attention, False, 0.0  # occl_frac: 0.0 ở fallback
                                )
                                bypassed.append({"bbox":[x,y,x+w,y+h],"score":conf,"label":label,"type":label,"near_face":nearf,"source":"tracker","hits":hits})
                    suspicious = bypassed
                    masked_reason = "masked_before_arm_with_hard_bypass" if bypassed else "masked_before_arm"
                    prearm_warn = bool(bypassed and self._env_bool("PREARM_WARN_FOR_BYPASS","0"))
                    if self._mask_before_arm:
                        cheat_alias = set(self._env_list("SUSPICIOUS_CLASSES")) or set(self._env_list("CHEAT_CLASSES"))
                        cheat_alias = {c.lower() for c in cheat_alias} if cheat_alias else set()
                        def is_cheat(name: str) -> bool:
                            n = (name or "").lower()
                            if cheat_alias:
                                return n in cheat_alias
                            return n in {"cell phone","phone","mobile phone","smartphone","laptop","notebook","tablet","book","paper","sheet of paper","keyboard","mouse","remote","monitor","tv","rectangular_device_or_paper"}
                        objects = [o for o in objects if not is_cheat(o.get("type") or o.get("label"))]
                        object_count = len(objects)
                    suspicious_count = len(suspicious)

            # ---- Attention alert (optionally suppressed before armed) ----
            attention_alert = (attention < self._env_float("ATTENTION_ALERT_THRESHOLD", 0.45))
            if not armed and self._suppress_attention_before_arm:
                attention_alert = False

            # ---- Debounce/arming/votes ----
            event = None
            # Gate opening rules (must hold to start voting/fast-lane)
            baseline_ok = (self._att_accum_s >= self._attn_base_sec)
            time_ok = (self._armed_since is not None) and ((now - self._armed_since) >= self._cheat_start_delay)
            susp_gate_open = bool(armed and time_ok and (baseline_ok or (not self._susp_require_att)))

            near_face_ready = (
                self._session_started_at is not None
                and (now - self._session_started_at) >= self._near_face_delay
            )
            if armed and not in_cooldown and susp_gate_open:
                if near_face_ready and ((suspicious_count > 0) or hold_active):
                    event = "susp"
                elif face_count > 1:
                    event = "mf"
                elif face_count == 0:
                    event = "nf"  # No face - cảnh báo ngay
            # Cảnh báo sớm ngay cả khi chưa armed (nhưng sau warmup)
            elif not in_warmup and face_count == 0 and (now - self._session_started_at) >= (self._warmup_sec + 1.0):
                event = "nf"  # Cảnh báo sớm khi không có mặt
            if event:
                self._votes.append(event)

            cheating_detected, cheating_reason = self._vote_pick()
                # Optional: escalate ngay khung đầu sau khi mở gate
            if armed and susp_gate_open and self._env_bool("CHEAT_ESCALATE_ON_FIRST_SUSP","0") and (suspicious_count > 0 or hold_active):
                  cheating_detected = True
                  cheating_reason = "first-susp escalate"

                

            # ---- Fast-lane override (v3.6.3 + gated in v3.7) ----
            if armed and not in_cooldown and susp_gate_open and self._fast_block and self._fast_hits:
                # also delay fast-lane for a short time after arming
                if (self._armed_since is not None) and ((now - self._armed_since) >= self._fast_block_delay):
                    for k, cnt in self._fast_hits.items():
                        if cnt >= int(self._fast_block_frames):
                            cheating_detected = True
                            cheating_reason = f"fast-lane: {k} high-risk near face"
                            break
            if cheating_detected and armed and self._cooldown_sec > 0.0:
                self._cooldown_until = max(self._cooldown_until, now + self._cooldown_sec)
                
            # ---- AutoBoost (chạy sau khi có armed & susp_gate_open) ----
            if face_count >= 1 and object_count == 0 and armed:
              self._no_obj_frames += 1
            else:
              self._no_obj_frames = 0

            if armed and susp_gate_open and self._no_obj_frames >= int(self._autoboost_trig):
              self._autoboost_until = max(self._autoboost_until, now + float(self._autoboost_win))

            self._roi_autoboost_active = (time.time() < self._autoboost_until)
            dbg["autoboost_active"] = bool(self._roi_autoboost_active)

            # ---- Policy surface (for UI to adopt)
            should_block = bool(armed and susp_gate_open and cheating_detected)
            should_warn  = bool(
                (armed and susp_gate_open and ((suspicious_count > 0) or hold_active) and not should_block)
                or locals().get("prearm_warn", False)
            )
            policy_level = "cooldown" if in_cooldown else ("monitor" if armed else "warmup")

            dbg.update({
                "face_count": face_count,
                "object_count": object_count,
                "suspicious_count": suspicious_count,
                "armed": armed,
                "in_warmup": in_warmup,
                "cooldown_until": self._cooldown_until,
                "state": self._state,
                "attention": attention,
                "masked_reason": masked_reason,
                "armed_since": float(self._armed_since) if self._armed_since else None,
                "att_baseline_s": round(self._att_accum_s, 3),
                "baseline_ok": bool(baseline_ok),
                "susp_gate_open": bool(susp_gate_open),
                "gate_rules": {
                    "require_att_baseline": bool(self._susp_require_att),
                    "attn_base_sec": float(self._attn_base_sec),
                    "attn_base_min": float(self._attn_base_min),
                    "start_delay_sec": float(self._cheat_start_delay),
                    "fast_block_delay_sec": float(self._fast_block_delay)
                }
            })
            self._last_dbg = dbg
            if self._dbg:
                self._log(f"detect: faces={face_count} objs={object_count} susp={suspicious_count} "
                          f"state={self._state} armed={armed} warmup={in_warmup} att={attention:.2f}")

            return {
                "faces": faces,
                "objects": objects,
                "suspicious_objects": suspicious,
                "face_count": face_count,
                "object_count": object_count,
                "suspicious_count": len(suspicious),
                "attention_score": float(attention),
                "attention_score_smooth": float(self._att_ema) if getattr(self, "_att_ema", None) is not None else None,
                "attention_alert": bool(attention_alert),
                "looking_away": bool(look_away),
                "eyes_closed": bool(eyes_closed),
                "mouth_open": bool(mouth_open),
                "head_pose": pose,
                "state": self._state,
                "armed": bool(armed),
                "should_warn": bool(should_warn),
                "should_block": bool(should_block),
                "policy_level": policy_level,
                "cheating_detected": bool(cheating_detected),
                "cheating_reason": cheating_reason,
                "debug": dbg
            }
        except Exception as e:
            if self._dbg:
                import traceback; traceback.print_exc()
            return self._empty_result(str(e), alert=True)
        
        

    def _vote_pick(self):
        """
        Quyết định gian lận dựa trên votes
        Ưu tiên: suspicious objects > multiple faces > no face
        """
        c = Counter(self._votes)
        # Ưu tiên 1: Suspicious objects (phone, book, etc.)
        if c.get("susp",0) >= self._req_susp: 
            return True, "suspicious near-face object"
        # Ưu tiên 2: Multiple faces (chỉ khi không có suspicious objects)
        if c.get("mf",0) >= self._req_mf:   
            return True, "multiple faces detected"
        # Ưu tiên 3: No face (chỉ khi không có suspicious objects và multiple faces)
        if c.get("nf",0) >= self._req_nf:   
            return True, "no face detected"
        return False, None

    def _coerce_to_bgr(self, image_input):
        if isinstance(image_input, np.ndarray):
            return image_input
        if isinstance(image_input, (bytes, bytearray)):
            try:
                nparr = np.frombuffer(image_input, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None and img.size>0: return img
            except Exception: pass
            try:
                s = image_input.decode("utf-8", errors="ignore").strip()
                if s.startswith("data:image"): s = s.split(",",1)[-1]
                s = "".join(s.split())
                raw = base64.b64decode(s, validate=False)
                nparr = np.frombuffer(raw, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None and img.size>0: return img
            except Exception: pass
            try:
                with Image.open(BytesIO(image_input)) as im:
                    im = im.convert("RGB")
                    return np.array(im)[:, :, ::-1]
            except Exception:
                return None
        if isinstance(image_input, list):
            try:
                return self._coerce_to_bgr(bytes(bytearray(image_input)))
            except Exception:
                return None
        if isinstance(image_input, str):
            try:
                return self._coerce_to_bgr(image_input.encode("utf-8"))
            except Exception:
                return None
        return None

    def _enhance_for_detection(self, img):
        try:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l,a,b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            img2 = cv2.merge([l,a,b])
            img2 = cv2.cvtColor(img2, cv2.COLOR_LAB2BGR)
            img2 = cv2.bilateralFilter(img2, d=9, sigmaColor=75, sigmaSpace=75)
            g = cv2.GaussianBlur(img2, (0,0), 2.0)
            return cv2.addWeighted(img2, 1.5, g, -0.5, 0)
        except Exception:
            return img

    def _detect_faces(self, img) -> List[Tuple[int,int,int,int]]:
        faces: List[Tuple[int,int,int,int]] = []
        H, W = img.shape[:2]

        def add(x,y,w,h):
            if w<8 or h<8: return
            b = (x,y,x+w,y+h)
            for (fx,fy,fw,fh) in faces:
                if self._iou(b,(fx,fy,fx+fw,fy+fh))>0.5:
                    return
            faces.append((int(x),int(y),int(w),int(h)))

        if _HAS_MP and _mp_face_det is not None:
            try:
                rs = _mp_face_det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                if rs.detections:
                    for d in rs.detections:
                        sc = d.score[0] if d.score else 0.0
                        if sc >= 0.20:
                            loc = d.location_data.relative_bounding_box
                            x = int(max(0.0,loc.xmin)*W)
                            y = int(max(0.0,loc.ymin)*H)
                            w = int(min(1.0,loc.width)*W)
                            h = int(min(1.0,loc.height)*H)
                            add(x,y,w,h)
            except Exception:
                pass

        try:
            if self._yolo_face_net is not None:
                blob = cv2.dnn.blobFromImage(img, 1/255.0, (640,640), swapRB=True, crop=False)
                self._yolo_face_net.setInput(blob)
                out = np.squeeze(self._yolo_face_net.forward())
                if out.ndim == 1: out = out[np.newaxis,:]
                if out.ndim == 2 and out.shape[0] in (84,16,15) and out.shape[0] < out.shape[1]:
                    out = out.T
                boxes, scores = [], []
                for d in out:
                    if d.shape[0] < 5: continue
                    cx,cy,bw,bh = float(d[0])*W, float(d[1])*H, float(d[2])*W, float(d[3])*H
                    conf = float(d[4]) * (float(d[5]) if (self._yolo_face_backend=="yolov8-face" and d.shape[0]>5) else 1.0)
                    if conf < 0.25: continue
                    x1 = int(max(0,cx-bw/2)); y1=int(max(0,cy-bh/2))
                    bw = int(min(W-x1,bw)); bh=int(min(H-y1,bh))
                    boxes.append([x1,y1,bw,bh]); scores.append(conf)
                if boxes:
                    idx = cv2.dnn.NMSBoxes(boxes, scores, 0.25, 0.40)
                    keep = idx.flatten().tolist() if hasattr(idx,"flatten") else list(idx) if isinstance(idx,(list,tuple)) else []
                    for i in keep:
                        x,y,w,h = boxes[int(i)]
                        add(x,y,w,h)
        except Exception:
            pass

        try:
            if self._haar is not None:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                det = self._haar.detectMultiScale(gray, scaleFactor=1.05, minNeighbors=3, minSize=(24,24))
                for (x,y,w,h) in det:
                    add(int(x),int(y),int(w),int(h))
        except Exception:
            pass

        try:
            if self._dnn_face is not None:
                blob = cv2.dnn.blobFromImage(img, 1.0, (300,300), (104.0,177.0,123.0), swapRB=False, crop=False)
                self._dnn_face.setInput(blob)
                det = self._dnn_face.forward()
                for i in range(det.shape[2]):
                    conf = float(det[0,0,i,2])
                    if conf < 0.30: continue
                    x1=int(det[0,0,i,3]*W); y1=int(det[0,0,i,4]*H)
                    x2=int(det[0,0,i,5]*W); y2=int(det[0,0,i,6]*H)
                    x1=max(0,min(W-1,x1)); y1=max(0,min(H-1,y1))
                    x2=max(0,min(W-1,x2)); y2=max(0,min(H-1,y2))
                    add(x1,y1,max(0,x2-x1),max(0,y2-y1))
        except Exception:
            pass

        if faces:
            ms = int(min(H,W) * self._env_float("FACE_MIN_SIDE_RATIO",0.026))
            faces = [(x,y,w,h) for (x,y,w,h) in faces if (w>=ms and h>=ms) or (w>=int(ms*0.8) and h>=int(ms*0.8))]
        return faces

    def _detect_objects(self, img):
        res: List[Dict] = []
        suspicious_pre: List[Dict] = []

        H, W = img.shape[:2]
        # Giảm threshold để phát hiện tốt hơn các vật thể gian lận
        conf_thr = self._env_float("CHEAT_OBJ_CONF", 0.10)  # Giảm từ 0.15 xuống 0.10 để phát hiện nhiều hơn
        min_side = max(6, int(min(W,H)*self._env_float("OBJ_MIN_SIDE_RATIO",0.010)))  # Giảm từ 0.015 xuống 0.010 để phát hiện objects nhỏ hơn

        def _canon(name: str) -> str:
            n = (name or "").strip().lower()
            alias = {
                "cell phone":{"phone","cellphone","mobile phone","smartphone"},
                "laptop":{"notebook","computer"},
                "book":{"paper","sheet of paper","cheat sheet"},
                "keyboard":{"key board"},
                "mouse":{"computer mouse"},
                "tv":{"tvmonitor","monitor"},
                "person":{"human","people"},
            }
            for k,v in alias.items():
                if n==k or n in v: return k
            return n

        def _letterbox(im, new_shape=(640,640), color=(114,114,114)):
            h,w = im.shape[:2]
            r = min(new_shape[0]/h, new_shape[1]/w)
            new_unpad = (int(round(w*r)), int(round(h*r)))
            dw, dh = new_shape[1]-new_unpad[0], new_shape[0]-new_unpad[1]
            dw/=2; dh/=2
            im2 = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
            im2 = cv2.copyMakeBorder(im2, int(round(dh)), int(round(dh)),
                                     int(round(dw)), int(round(dw)),
                                     cv2.BORDER_CONSTANT, value=color)
            return im2, r, (dw, dh)

        def _map_xyxy(x1,y1,x2,y2, r,dw,dh):
            x1 = (x1-dw)/r; y1=(y1-dh)/r
            x2 = (x2-dw)/r; y2=(y2-dh)/r
            x1 = max(0,min(W-1,int(x1))); y1=max(0,min(H-1,int(y1)))
            x2 = max(0,min(W-1,int(x2))); y2=max(0,min(H-1,int(y2)))
            return x1, y1, x2-x1, y2-y1

        try:
            if self._obj_ort is not None and self._obj_backend in ("yolo_ort","onnx_runtime","ort"):
                sess = self._obj_ort
                inp_name = sess.get_inputs()[0].name
                lb, r, (dw,dh) = _letterbox(img, (640,640))
                inp = lb[:,:,::-1].transpose(2,0,1).astype(np.float32)/255.0
                inp = np.expand_dims(inp,0)
                outs = sess.run(None, {inp_name: inp})

                boxes, scores, names = [], [], []
                if len(outs) >= 3:
                    b = np.squeeze(outs[0]); s=np.squeeze(outs[1]); l=np.squeeze(outs[2])
                    if b.ndim==3: b=b.reshape(-1,4)
                    s=s.reshape(-1); l=l.reshape(-1)
                    if (s.min()<0.0 or s.max()>1.0): s=_sigmoid(s)
                    N=min(len(b),len(s),len(l))
                    for i in range(N):
                        x1,y1,x2,y2 = map(float,b[i])
                        if max(x1,y1,x2,y2) <= 2.0:
                            x1*=640; y1*=640; x2*=640; y2*=640
                        x,y,w,h = _map_xyxy(x1,y1,x2,y2,r,dw,dh)
                        if w<=0 or h<=0 or min(w,h)<min_side: continue
                        sc=float(s[i]); 
                        if sc < conf_thr: continue
                        cid=int(round(float(l[i])))
                        raw=self._obj_names[cid] if 0<=cid<len(self._obj_names) else str(cid)
                        boxes.append([x,y,w,h]); scores.append(sc); names.append(_canon(raw))
                else:
                    pred = np.array(outs[0]).squeeze()
                    if pred.ndim == 3: pred = pred.reshape(-1, pred.shape[-1])
                    if pred.ndim == 2 and pred.shape[0] in (84,85) and pred.shape[1]>pred.shape[0]:
                        pred = pred.T
                    if pred.size and (pred[:,4].max()>1.0 or pred[:,4].min()<0.0 or pred[:,5:].max()>1.0 or pred[:,5:].min()<0.0):
                        pred[:,4]=_sigmoid(pred[:,4]); pred[:,5:]=_sigmoid(pred[:,5:])
                    for d in pred:
                        if d.shape[0] < 6: continue
                        obj=float(d[4]); cls=d[5:]
                        if cls.size==0: continue
                        cid=int(np.argmax(cls)); sc=obj*float(cls[cid])
                        if sc < conf_thr: continue
                        a,b0,c,d0 = map(float, d[:4])
                        if max(a,b0,c,d0) <= 2.0:
                            cx,cy,bw,bh = a*640, b0*640, c*640, d0*640
                            x1,y1,x2,y2 = cx-bw/2, cy-bh/2, cx+bw/2, cy+bh/2
                        else:
                            x1,y1,x2,y2 = a,b0,c,d0
                        x,y,w,h = _map_xyxy(x1,y1,x2,y2,r,dw,dh)
                        if w<=0 or h<=0 or min(w,h)<min_side: continue
                        raw=self._obj_names[cid] if 0<=cid<len(self._obj_names) else str(cid)
                        boxes.append([x,y,w,h]); scores.append(sc); names.append(_canon(raw))

                if boxes:
                    idx = cv2.dnn.NMSBoxes(boxes, scores, max(conf_thr,0.15), 0.45)
                    keep = idx.flatten().tolist() if hasattr(idx,"flatten") else list(idx) if isinstance(idx,(list,tuple)) else []
                    for i in keep:
                        x,y,w,h = boxes[i]
                        res.append({"type":names[i], "position":(int(x),int(y),int(w),int(h)),
                                    "score":float(scores[i]), "source":"ort"})
        except Exception:
            pass

        try:
            if self._obj_dnn is not None and self._obj_backend == "yolo":
                blob = cv2.dnn.blobFromImage(img, 1/255.0, (640,640), swapRB=True, crop=False)
                self._obj_dnn.setInput(blob)
                out = np.squeeze(self._obj_dnn.forward())
                if out.ndim == 1: out = out[np.newaxis,:]
                boxes, scores, names = [], [], []
                for d in out:
                    if d.shape[0] < 6: continue
                    conf=float(d[4]); 
                    if conf < conf_thr: continue
                    cls=d[5:]; 
                    if cls.size==0: continue
                    cid=int(np.argmax(cls)); cls_sc=float(cls[cid]); sc=conf*cls_sc
                    if sc < conf_thr: continue
                    cx,cy,bw,bh = d[0]*W, d[1]*H, d[2]*W, d[3]*H
                    x1=int(max(0,cx-bw/2)); y1=int(max(0,cy-bh/2))
                    bw=int(min(W-x1,bw)); bh=int(min(H-y1,bh))
                    if min(bw,bh) < min_side: continue
                    raw=self._obj_names[cid] if 0<=cid<len(self._obj_names) else str(cid)
                    boxes.append([x1,y1,bw,bh]); scores.append(sc); names.append(_canon(raw))
                if boxes:
                    idx = cv2.dnn.NMSBoxes(boxes, scores, max(conf_thr,0.15), 0.45)
                    keep = idx.flatten().tolist() if hasattr(idx,"flatten") else list(idx) if isinstance(idx,(list,tuple)) else []
                    for i in keep:
                        x,y,w,h = boxes[i]
                        res.append({"type":names[i], "position":(int(x),int(y),int(w),int(h)),
                                    "score":float(scores[i]), "source":"dnn"})
            elif self._obj_dnn is not None and self._obj_backend == "ssd":
                classes, scores, boxes = self._obj_dnn.detect(img, confThreshold=conf_thr, nmsThreshold=0.45)
                if classes is not None and len(classes):
                    for cid, sc, (x,y,w,h) in zip(classes.flatten(), scores.flatten(), boxes):
                        if float(sc) < conf_thr or min(w,h) < min_side: continue
                        raw=self._obj_names[int(cid)] if 0<=int(cid)<len(self._obj_names) else str(cid)
                        res.append({"type":_canon(raw), "position":(int(x),int(y),int(w),int(h)),
                                    "score":float(sc), "source":"dnn"})
        except Exception:
            pass

        # Shape heuristic (paper/device-like rectangles) to augment COCO
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.equalizeHist(gray)
            edges = cv2.Canny(gray, int(self._env_float("RECT_CANNY_LOW", 40)), int(self._env_float("RECT_CANNY_HIGH", 160)))
            edges = cv2.dilate(edges, np.ones((3,3),np.uint8), iterations=1)
            edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8), iterations=1)
            cnts,_ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            MIN_AREA = int(self._env_float("RECT_MIN_AREA", 150))
            MIN_EXTENT = float(self._env_float("RECT_MIN_EXTENT", 0.30))
            MAX_COVER = float(self._env_float("RECT_MAX_COVERAGE", 70.0))
            AR_MIN = float(self._env_float("RECT_AR_MIN", 0.2))
            AR_MAX = float(self._env_float("RECT_AR_MAX", 6.0))
            for c in cnts:
                area=cv2.contourArea(c)
                if area < MIN_AREA: continue
                x,y,w,h = cv2.boundingRect(c)
                if min(w,h) < min_side: continue
                rect_area = w*h
                if rect_area <= 0: continue
                extent = area/float(rect_area)
                ar = w/float(h+1e-6)
                coverage = (area/float(W*H))*100.0
                if not (AR_MIN < ar < AR_MAX and extent > MIN_EXTENT and coverage < MAX_COVER):
                    continue
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.04*peri, True)
                hull = cv2.convexHull(c)
                solidity = area / (cv2.contourArea(hull)+1e-6)
                if len(approx) >= 4 and solidity > 0.85:
                    score = 0.50 + 0.20*min(1.0, extent/0.8)
                    res.append({"type":"rectangular_device_or_paper",
                                "position":(int(x),int(y),int(w),int(h)),
                                "score":float(score), "source":"heuristic"})
        except Exception:
            pass

        # Suspicious classes filtering - NHƯNG sẽ được kiểm tra lại ở trên dựa trên near_face
        # Ở đây chỉ lọc person để không đánh dấu person là suspicious
        susc = set(self._env_list("SUSPICIOUS_CLASSES")) or set(self._env_list("CHEAT_CLASSES"))
        susc = {s.strip().lower() for s in susc}
        def _is_susp(n):
            # Bỏ qua person - không đánh dấu person là suspicious
            if n == "person":
                return False
            mode = (os.getenv("SUS_MODE","cheat_tools") or "").strip().lower()
            if mode == "cheat_tools":
                # Nếu có class set, chỉ lọc theo set. Nếu không có, lấy tất cả (trừ person)
                return (not susc) or (n in susc)
            if mode == "non_person":
                return n != "person"
            # Mặc định: lấy tất cả trừ person
            return n != "person"

        for o in res:
            name = (o["type"] or "object").lower()
            # Bỏ qua person
            if name == "person":
                continue
            if _is_susp(name):
                x,y,w,h = o["position"]
                suspicious_pre.append({"type": name, "position": (x,y,w,h), "score": float(o.get("score",0.0)), "source": o.get("source","dnn")})

        return res, suspicious_pre

    def _roi_near_faces(self, img, faces_xywh: List[Tuple[int,int,int,int]]) -> List[Dict]:
        faces = [(int(x),int(y),int(w),int(h)) for (x,y,w,h) in (faces_xywh or []) if w>0 and h>0]
        if not faces: return []
        if self._obj_backend not in ("yolo","yolo_ort"): return []

        H, W = img.shape[:2]
        scale   = (self._autoboost_scale if getattr(self,"_roi_autoboost_active",False)
           else self._env_float("OBJ_EXTRA_SCALE", 4.0))  # Tăng từ 3.0 lên 4.0 để scan rộng hơn nhiều
        conf_lo = (self._autoboost_conf if getattr(self,"_roi_autoboost_active",False)
           else self._env_float("CHEAT_OBJ_CONF_ROI", self._env_float("CHEAT_OBJ_CONF",0.04)))  # Giảm từ 0.06 xuống 0.04 để phát hiện nhiều hơn
        min_ratio = self._env_float("OBJ_MIN_SIDE_RATIO_ROI", self._env_float("OBJ_MIN_SIDE_RATIO",0.008))  # Giảm từ 0.010 xuống 0.008

        outs: List[Dict] = []
        for (fx,fy,fw,fh) in faces:
            cx,cy = fx+fw/2.0, fy+fh/2.0
            rw,rh = fw*scale, fh*scale
            x1 = max(0,int(cx-rw/2)); y1=max(0,int(cy-rh/2))
            x2 = min(W,int(cx+rw/2)); y2=min(H,int(cy+rh/2))
            if x2<=x1 or y2<=y1: continue
            crop = img[y1:y2, x1:x2]
            if crop.size == 0: continue
            min_side_px = max(8, int(min(crop.shape[0], crop.shape[1]) * min_ratio))

            if self._obj_backend == "yolo" and self._obj_dnn is not None:
                try:
                    blob = cv2.dnn.blobFromImage(crop, 1/255.0, (640,640), swapRB=True, crop=False)
                    self._obj_dnn.setInput(blob)
                    raw = np.squeeze(self._obj_dnn.forward())
                    if raw.ndim == 1: raw = raw[np.newaxis,:]
                    boxes, scores, cids = [], [], []
                    for d in raw:
                        if d.shape[0] < 6: continue
                        conf=float(d[4]); 
                        if conf < conf_lo: continue
                        cls=d[5:]; 
                        if cls.size==0: continue
                        cid=int(np.argmax(cls)); cls_sc=float(cls[cid]); sc=conf*cls_sc
                        if sc < conf_lo: continue
                        bw, bh = d[2]*crop.shape[1], d[3]*crop.shape[0]
                        xx, yy = int(d[0]*crop.shape[1]-bw/2), int(d[1]*crop.shape[0]-bh/2)
                        if min(bw,bh) < min_side_px: continue
                        boxes.append([xx,yy,int(bw),int(bh)]); scores.append(sc); cids.append(cid)
                    if boxes:
                        idx = cv2.dnn.NMSBoxes(boxes, scores, max(conf_lo,0.15), 0.45)
                        keep = idx.flatten().tolist() if hasattr(idx,"flatten") else list(idx) if isinstance(idx,(list,tuple)) else []
                        for i in keep:
                            bx,by,bw,bh = boxes[i]; cid=cids[i]
                            name = self._obj_names[cid] if 0<=cid<len(self._obj_names) else str(cid)
                            if self._coco_classes and name not in self._coco_classes: continue
                            outs.append({"type":name, "position":(x1+bx, y1+by, int(bw), int(bh)),
                                         "score":float(scores[i]), "source":"dnn_roi"})
                except Exception:
                    pass

            if self._obj_backend in ("yolo_ort","ort") and self._obj_ort is not None:
                try:
                    sess = self._obj_ort
                    inp_name = sess.get_inputs()[0].name
                    def _letterbox(im, new_shape=(640,640), color=(114,114,114)):
                        ih,iw = im.shape[:2]
                        r = min(new_shape[0]/ih, new_shape[1]/iw)
                        new_unpad = (int(round(iw*r)), int(round(ih*r)))
                        dw, dh = new_shape[1]-new_unpad[0], new_shape[0]-new_unpad[1]
                        dw/=2; dh/=2
                        im2 = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
                        im2 = cv2.copyMakeBorder(im2, int(round(dh)), int(round(dh)),
                                                 int(round(dw)), int(round(dw)),
                                                 cv2.BORDER_CONSTANT, value=color)
                        return im2, r, (dw, dh)
                    lb, r, (dw,dh) = _letterbox(crop, (640,640))
                    inp = lb[:,:,::-1].transpose(2,0,1).astype(np.float32)/255.0
                    inp = np.expand_dims(inp,0)
                    pred = np.squeeze(sess.run(None, {inp_name: inp})[0])
                    if pred.ndim == 1: pred = pred[np.newaxis,:]
                    boxes, scores, cids = [], [], []
                    for d in pred:
                        if d.shape[0] < 6: continue
                        conf=float(d[4]); 
                        if conf < conf_lo: continue
                        cls=d[5:]; 
                        if cls.size==0: continue
                        cid=int(np.argmax(cls)); cls_sc=float(cls[cid]); sc=conf*cls_sc
                        if sc < conf_lo: continue
                        a,b,c0,d0 = map(float, d[:4])
                        maybe_norm = max(a,b,c0,d0) <= 2.0
                        if c0>a and d0>b:
                            x0,y0,x1p,y1p = a,b,c0,d0
                            if maybe_norm: x0*=640; y0*=640; x1p*=640; y1p*=640
                        else:
                            cx0,cy0,bw0,bh0 = a,b,c0,d0
                            if maybe_norm: cx0*=640; cy0*=640; bw0*=640; bh0*=640
                            x0,y0,x1p,y1p = cx0-bw0/2, cy0-bh0/2, cx0+bw0/2, cy0+bh0/2
                        x0 = int(max(0,(x0-dw)/r)); y0=int(max(0,(y0-dh)/r))
                        x1p= int(min(crop.shape[1]-1,(x1p-dw)/r)); y1p=int(min(crop.shape[0]-1,(y1p-dh)/r))
                        bw, bh = x1p-x0, y1p-y0
                        if bw<=0 or bh<=0 or min(bw,bh) < min_side_px: continue
                        boxes.append([x0,y0,bw,bh]); scores.append(sc); cids.append(cid)
                    if boxes:
                        idx = cv2.dnn.NMSBoxes(boxes, scores, max(conf_lo,0.15), 0.45)
                        keep = idx.flatten().tolist() if hasattr(idx,"flatten") else list(idx) if isinstance(idx,(list,tuple)) else []
                        for i in keep:
                            bx,by,bw,bh = boxes[i]; cid=cids[i]
                            name = self._obj_names[cid] if 0<=cid<len(self._obj_names) else str(cid)
                            if self._coco_classes and name not in self._coco_classes: continue
                            outs.append({"type":name, "position":(x1+bx, y1+by, int(bw), int(bh)),
                                         "score":float(scores[i]), "source":"ort_roi"})
                except Exception:
                    pass
        return outs

    @staticmethod
    def _iou(a, b) -> float:
        x1=max(a[0],b[0]); y1=max(a[1],b[1])
        x2=min(a[2],b[2]); y2=min(a[3],b[3])
        w=max(0,x2-x1); h=max(0,y2-y1)
        inter=w*h
        if inter==0: return 0.0
        aa=(a[2]-a[0])*(a[3]-a[1]); bb=(b[2]-b[0])*(b[3]-b[1])
        return inter/float(aa+bb-inter+1e-6)

    def _near_face(self, box_xyxy, face_xyxy, expand, iou_min, dist_ratio) -> bool:
        """
        Kiểm tra object có gần mặt không
        Cải thiện để phát hiện tốt hơn các object trước mặt và cạnh mặt
        """
        x1,y1,x2,y2 = face_xyxy
        fw,fh = x2-x1, y2-y1
        cx,cy = x1+fw/2, y1+fh/2
        ex,ey = fw*expand/2, fh*expand/2
        rx1,ry1 = int(max(0,cx-ex)), int(max(0,cy-ey))
        rx2,ry2 = int(cx+ex), int(cy+ey)
        roi = (rx1,ry1,rx2,ry2)
        
        # Kiểm tra IoU với ROI mở rộng
        iou_val = self._iou(box_xyxy, roi)
        if iou_val >= iou_min:
            return True
        
        # Kiểm tra khoảng cách từ tâm object đến tâm mặt
        ox1,oy1,ox2,oy2 = box_xyxy
        ocx,ocy = (ox1+ox2)/2, (oy1+oy2)/2
        fdiag = (fw*fw + fh*fh)**0.5
        dist  = ((ocx-cx)**2 + (ocy-cy)**2)**0.5
        dist_normalized = dist / float(fdiag + 1e-6)
        
        # Nếu object ở phía trước mặt (y nhỏ hơn - object ở trên/trước)
        # hoặc ở cạnh mặt (x gần với cx), coi là gần mặt
        is_in_front = ocy < cy + fh*0.5  # Object ở phía trên/trước mặt (mở rộng vùng)
        is_at_side = abs(ocx - cx) < fw * 1.5  # Object ở cạnh mặt (trái/phải)
        is_below = ocy < cy + fh * 1.2  # Object ở phía dưới mặt nhưng không quá xa
        
        # Nếu object ở phía trước mặt, tăng threshold lên 50%
        if is_in_front:
            return dist_normalized <= dist_ratio * 1.5
        
        # Nếu object ở cạnh mặt, tăng threshold lên 30%
        if is_at_side and is_below:
            return dist_normalized <= dist_ratio * 1.3
        
        # Kiểm tra khoảng cách thông thường
        return dist_normalized <= dist_ratio

    # ---------- Risk scoring helpers (v3.6) ----------
    def _near_ear(self, face_xywh, obj_xywh) -> bool:
        if not face_xywh or not obj_xywh:
            return False
        fx,fy,fw,fh = map(int, face_xywh)
        ox,oy,ow,oh = map(int, obj_xywh)
        # Define two ear zones left/right of face
        pad = int(fw * (self._ear_zone_scale-1.0)/2)
        left  = (fx - pad - fw//3, fy + fh//5, fx + fw//3, fy + 4*fh//5)
        right = (fx + 2*fw//3, fy + fh//5, fx + fw + pad + fw//3, fy + 4*fh//5)
        ob = (ox,oy,ox+ow,oy+oh)
        return self._iou(ob, left) > 0.02 or self._iou(ob, right) > 0.02

    def _risk_score(self, label: str, near_face: bool, size_frac: float, hits: int, conf: float, att: float, near_ear: bool, occl_frac: float) -> float:
        base = self._risk_class_base.get(label.lower(), 0.40)
        # size_frac is sqrt(area_frac) in [0..1]
        s_size   = min(1.0, max(0.0, size_frac))
        # Nếu gần mặt, tăng s_near lên cao để ưu tiên
        s_near   = 1.0 if near_face else 0.15  # Giảm từ 0.25 xuống 0.15 khi không gần mặt
        s_stable = min(1.0, hits/5.0)  # >=5 frames => 1.0
        s_att    = 1.0 - float(max(0.0, min(1.0, att)))
        s_conf   = float(max(0.0, min(1.0, conf)))
        
        # Nếu object gần mặt, tăng base risk lên cao hơn
        if near_face:
            base = min(1.0, base + 0.50)  # Tăng base risk thêm 50% nếu gần mặt (từ 0.30 lên 0.50)
        # ear proximity strongly boosts phones/tablets
        if near_ear and label.lower() in {"cell phone","mobile phone","phone","smartphone","tablet"}:
            base = min(1.0, base + 0.20)  # Tăng từ 0.15 lên 0.20
        # occlusion of face boosts risk for book/paper/rectangular objects
        if label.lower() in {"book","paper","sheet of paper","rectangular_device_or_paper"}:
            base = min(1.0, base + 0.15 * min(1.0, occl_frac/0.20))  # Tăng từ 0.10 lên 0.15 và giảm threshold từ 0.25 xuống 0.20
        
        # Nếu object gần mặt, tăng weight của s_near lên
        if near_face:
            # Tăng weight của near_face khi object gần mặt
            score = (
                self._risk_w_class  * base * 0.8 +  # Giảm weight của class khi gần mặt
                self._risk_w_near   * s_near * 1.5 +  # Tăng weight của near lên 50%
                self._risk_w_size   * s_size +
                self._risk_w_stable * s_stable +
                self._risk_w_att    * s_att
            )
        else:
            score = (
                self._risk_w_class  * base +
                self._risk_w_near   * s_near +
                self._risk_w_size   * s_size +
                self._risk_w_stable * s_stable +
                self._risk_w_att    * s_att
            )
        
        # small bonus for high detector confidence
        score = score * (0.85 + 0.30 * s_conf)
        return float(max(0.0, min(1.0, score)))

    # ---------- Attention via FaceMesh ----------
    def _compute_attention_with_facemesh(self, img_bgr, face_xywh):
        """
        Returns: (attention_score 0..1, looking_away, eyes_closed, mouth_open, head_pose dict|None)
        """
        if not (_HAS_MP and _mp_face_mesh):
            # fallback: if face exists, return high attention
            return (0.9 if face_xywh else 0.0), False, False, False, None

        H, W = img_bgr.shape[:2]
        x,y,w,h = map(int, face_xywh)
        x0 = max(0, x); y0 = max(0, y)
        x1 = min(W, x+w); y1 = min(H, y+h)
        if x1 <= x0 or y1 <= y0:
            return 0.5, False, False, False, None

        crop = img_bgr[y0:y1, x0:x1]
        if crop.size == 0:
            return 0.5, False, False, False, None

        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        res = _mp_face_mesh.process(crop_rgb)
        if not res.multi_face_landmarks:
            return 0.6, False, False, False, None
        lms = res.multi_face_landmarks[0].landmark

        def P(i):
            return np.array([ (x0 + lms[i].x * (x1-x0)),
                              (y0 + lms[i].y * (y1-y0)) ], dtype=np.float32)

        # EAR
        L_left, L_right, L_top, L_bot = P(33), P(133), P(159), P(145)
        R_left, R_right, R_top, R_bot = P(263), P(362), P(386), P(374)
        def ear(l, r, t, b):
            eye_w = np.linalg.norm(l - r) + 1e-6
            eye_h = (np.linalg.norm(t - b))
            return eye_h / eye_w
        EAR_L = ear(L_left,L_right,L_top,L_bot)
        EAR_R = ear(R_left,R_right,R_top,R_bot)
        EAR = (EAR_L + EAR_R)/2.0
        eyes_closed = (EAR < float(os.getenv("ATTN_EAR_CLOSED", "0.19")))

        # MAR
        M_left, M_right, M_top, M_bot = P(61), P(291), P(13), P(14)
        MAR = np.linalg.norm(M_top - M_bot) / (np.linalg.norm(M_left - M_right) + 1e-6)
        mouth_open = MAR > float(os.getenv("ATTN_MAR_OPEN", "0.34"))

        # Head pose (yaw/pitch/roll)
        model_3d = np.array([
            [0.0,   0.0,    0.0],   # nose tip (1)
            [0.0,  -63.6, -12.5],   # chin (152)
            [-43.3, 32.7, -26.0],   # left eye outer (33)
            [ 43.3, 32.7, -26.0],   # right eye outer (263)
            [-28.9,-28.9, -24.1],   # left mouth (61)
            [ 28.9,-28.9, -24.1],   # right mouth (291)
        ], dtype=np.float32)
        image_2d = np.stack([P(1), P(152), P(33), P(263), P(61), P(291)], axis=0)

        f = 1.5 * max(W, H)
        cam_mtx = np.array([[f,0,W/2],[0,f,H/2],[0,0,1]], dtype=np.float32)
        dist = np.zeros((4,1), dtype=np.float32)

        yaw=pitch=roll=0.0
        try:
            ok, rvec, tvec = cv2.solvePnP(model_3d, image_2d, cam_mtx, dist, flags=cv2.SOLVEPNP_ITERATIVE)
            if ok:
                R,_ = cv2.Rodrigues(rvec)
                sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
                pitch = np.degrees(np.arctan2(-R[2,0], sy))
                yaw   = np.degrees(np.arctan2(R[1,0], R[0,0]))
                roll  = np.degrees(np.arctan2(R[2,1], R[2,2]))
        except Exception:
            pass

        yaw_max   = float(os.getenv("ATTN_YAW_MAX", "30"))
        pitch_max = float(os.getenv("ATTN_PITCH_MAX","20"))
        looking_away = (abs(yaw) > yaw_max) or (abs(pitch) > pitch_max)

        # Attention score 0..1
        yaw_n   = min(1.0, abs(yaw)/40.0)
        pitch_n = min(1.0, abs(pitch)/25.0)
        blink_n = 1.0 if eyes_closed else 0.0
        mouth_n = 1.0 if mouth_open else 0.0
        att = 1.0 - (0.45*yaw_n + 0.35*pitch_n + 0.15*blink_n + 0.05*mouth_n)
        att = float(max(0.0, min(1.0, att)))
        pose = {"yaw": float(yaw), "pitch": float(pitch), "roll": float(roll)}
        return att, looking_away, bool(eyes_closed), bool(mouth_open), pose

    def _empty_result(self, err: Optional[str] = None, alert: bool = False) -> Dict:
        self._last_dbg = {"error": err}
        return {
            "faces": [], "objects": [], "suspicious_objects": [],
            "face_count": 0, "object_count": 0, "suspicious_count": 0,
            "attention_score": 0.0, "attention_alert": bool(alert),
            "looking_away": False, "eyes_closed": False, "mouth_open": False, "head_pose": None,
            "state": self._state, "armed": False,
            "should_warn": False, "should_block": False, "policy_level": "warmup",
            "cheating_detected": False, "cheating_reason": err, "error": err,
            "debug": self.debug_status()
        }


# Lazy singleton để tránh load nặng khi Flask reload
_face_recognition_service_instance = None

def get_face_recognition_service() -> FaceRecognitionService:
    global _face_recognition_service_instance
    if _face_recognition_service_instance is None:
        _face_recognition_service_instance = FaceRecognitionService()
    return _face_recognition_service_instance

def is_face_recognition_available() -> bool:
    return get_face_recognition_service().is_available()


# Build: v3.7 • gating start-up reliably • generated 2025-11-09T15:55:00+0700
