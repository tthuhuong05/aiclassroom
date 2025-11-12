

from __future__ import annotations
import os
from typing import Any, Dict, List, Tuple
from services.attention_calibration import AttentionCalibrator

# ------- helpers to read env safely -------

def _get_float(k: str, d: float) -> float:
    try:
        return float(os.getenv(k, d))
    except Exception:
        return d

def _get_int(k: str, d: int) -> int:
    try:
        return int(os.getenv(k, d))
    except Exception:
        return d

# Thresholds (defaults are fairly strict; override via .env)
YAW_THR      = _get_float("ATT_YAW_THR", 30.0)
PITCH_THR    = _get_float("ATT_PITCH_THR", 25.0)
YAW_MAX      = _get_float("ATT_YAW_MAX", 60.0)
PITCH_MAX    = _get_float("ATT_PITCH_MAX", 45.0)
ATT_MIN_PROB = _get_float("ATTENTION_MIN_PROBA", 55.0)  # percent for alert only (not used in engine strikes)
OBJ_CONF_THR = _get_float("CHEAT_OBJ_CONF", 0.40)


def _parse_sus(val: str) -> List[str]:
    s = (val or "").strip()
    if not s:
        s = "cell phone,phone,laptop,book,keyboard,mouse,earphone,earbud,headphones,smartwatch,hand,tablet,rectangular_device_or_paper"
    out: List[str] = []
    for tok in s.split(","):
        t = tok.strip().strip("'").strip('"')
        if t:
            out.append(t.lower())
    return out

SUS_CLASSES = _parse_sus(os.getenv("CHEAT_CLASSES", ""))

# ------- calibration (with safe fallback) -------
try:
    from services.attention_calibration import AttentionCalibrator as _Calib  # type: ignore
except Exception:
    # Fallback heuristic calibrator if the module is missing
    class _Calib:  # type: ignore
        def __init__(self):
            self.yaw_max = YAW_MAX
            self.pitch_max = PITCH_MAX
            self.att_thr = 0.60
            self.lr = None

        def attentive_proba(self, yaw: float, pitch: float, att: float) -> float:
            ny = max(0.0, 1.0 - abs(yaw)/max(1.0, self.yaw_max))
            np = max(0.0, 1.0 - abs(pitch)/max(1.0, self.pitch_max))
            return float(0.4*att + 0.3*ny + 0.3*np)

        def pose_label_and_conf(self, yaw: float, pitch: float) -> Tuple[str, float]:
            ay, ap = abs(yaw), abs(pitch)
            fwd = (ay < self.yaw_max*0.45 and ap < self.pitch_max*0.45)
            if fwd:
                d = max(ay/max(1.0, self.yaw_max), ap/max(1.0, self.pitch_max))
                return "forward", float(1.0 - d)
            if ay/ap >= 1.2:
                if yaw > 0:
                    return "look_right", float(min(1.0, ay/max(1.0, self.yaw_max)))
                else:
                    return "look_left", float(min(1.0, ay/max(1.0, self.yaw_max)))
            else:
                if pitch > 0:
                    return "look_down", float(min(1.0, ap/max(1.0, self.pitch_max)))
                else:
                    return "look_up", float(min(1.0, ap/max(1.0, self.pitch_max)))


class ProctorAugmentor:
    """
    Adapter đưa đầu ra từ FaceRecognitionService thành các tín hiệu thống nhất mà
    exam_proctor_service mong đợi: attention_proba, pose_label/conf, looking_away,
    attention_alert (theo phần trăm), suspicious_objects được lọc.
    """
    def __init__(self) -> None:
        self.calib = _Calib()
        self.calib = AttentionCalibrator()

    @staticmethod
    def _get_pose(analysis: Dict[str, Any]) -> Tuple[float, float]:
        pose = (analysis or {}).get("head_pose") or {}
        yaw = float(pose.get("yaw") or 0.0)
        pitch = float(pose.get("pitch") or 0.0)
        return yaw, pitch

    @staticmethod
    def _get_raw_att(analysis: Dict[str, Any]) -> float:
        return float((analysis or {}).get("attention_score") or 0.0)

    @staticmethod
    def _collect_objects(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        objs = []
        # Accept either 'objects' [{'class','conf','bbox'}] or a raw list already filtered
        if isinstance(analysis.get("objects"), list):
            for o in analysis["objects"]:
                cls = str(
                o.get("class") or o.get("cls") or o.get("type") or o.get("label") or ""
                ).lower()
                conf = float(o.get("conf") or o.get("score") or o.get("confidence") or 0.0)
                bbox = o.get("bbox") or o.get("box") or o.get("position")
                objs.append({"class": cls, "conf": conf, "bbox": bbox})
        return objs

    def enrich(self, r: dict) -> dict:
        pose = r.get("head_pose") or {}
        yaw   = float(pose.get("yaw") or 0.0)
        pitch = float(pose.get("pitch") or 0.0)
        att   = float(r.get("attention_score") or 0.0)
        susp  = int(r.get("suspicious_count") or len(r.get("suspicious_objects") or []))

        # attention
        r["attention_proba"] = self.cal.attentive_proba(yaw, pitch, att)
        r["attention_alert"] = (r["attention_proba"] < self.cal.att_thr)
        label, conf = self.cal.pose_label_and_conf(yaw, pitch)
        r["pose_label"] = label

        # cheat
        p_cheat = self.cal.cheat_proba(yaw, pitch, att, susp)
        r["cheat_proba"] = p_cheat
        if p_cheat >= self.cal.block_p:
            r["should_block"] = True
            r.setdefault("cheating_reason", "cheat_logreg")
        elif p_cheat >= self.cal.warn_p:
            r["should_warn"] = True

        return r




