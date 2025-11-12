import time
from typing import Dict, Optional
from services.camera_capture_service import get_camera_capture_service
from services.face_recognition_service import (
    get_face_recognition_service, is_face_recognition_available
)
from services.attention_cheat_monitor import ProctorAugmentor


class ProctorConfig:
    # Ngưỡng & tần suất - NGHIÊM KHẮC HƠN (điều chỉnh nếu quá nhạy)
    SAMPLE_INTERVAL_SEC = 1.5          # nhận frame mỗi ~1.5s (tăng tần suất từ 2.0)
    ATTENTION_MIN = 0.60               # dưới mức này coi là thiếu tập trung (so với attention_proba)
    ATTENTION_STRIKES_TO_WARN = 1      # 1 lần liên tiếp -> cảnh báo
    ATTENTION_STRIKES_TO_FLAG = 2      # 2 lần liên tiếp -> gian lận
    NOFACE_STRIKES_TO_FLAG = 2         # 2 khung liên tiếp không có mặt -> gian lận
    REVERIFY_EVERY_N_FRAMES = 20       # 20 khung thì re-verify avatar 1 lần
    FACE_MATCH_THRESHOLD = 0.55        # đã dùng trong service
    SAVE_EVIDENCE = True
    WARN_COOLDOWN_FRAMES = 3           # cảnh báo không spam


class ProctorEngine:
    """
    Gom logic quyết định gian lận cho mỗi attempt_id
    """
    def __init__(self, attempt_id: str, avatar_bytes: bytes, config: ProctorConfig = ProctorConfig()):
        self.attempt_id = attempt_id
        self.avatar_bytes = avatar_bytes
        self.cfg = config
        self.cam = get_camera_capture_service()
        self.face = get_face_recognition_service()
        self.augment = ProctorAugmentor()
        self.state = {
            "frame_no": 0,
            "attention_strikes": 0,
            "noface_strikes": 0,
            "face_verified_once": False,
            "last_decision": "clear",  # clear | warn | flagged
            "reasons": [],
            "warn_cooldown": 0,
            "violation_counts": {"multi_face":0, "objects":0, "attention":0, "noface":0, "face_mismatch":0}
        }

    def _escalate(self, level: str, reason: str):
        self.state["last_decision"] = level
        if reason and reason not in self.state["reasons"]:
            self.state["reasons"].append(reason)

    def process_base64_frame(self, base64_img: str, save: bool = False) -> Dict:
        """
        Phân tích 1 frame base64 và trả kết quả ngay.
        - Ưu tiên cờ tức thì từ lớp nhận diện (cheating_detected/cheating_reason).
        - Flag ngay: nhiều khuôn mặt / có vật thể đáng ngờ / không khớp avatar.
        - Cộng dồn strike cho: thiếu tập trung, không thấy mặt (có cooldown cảnh báo).
        """
        s = self.state
        s["frame_no"] = s.get("frame_no", 0) + 1
        frame_no = s["frame_no"]
        s.setdefault("violation_counts", {"multi_face":0,"objects":0,"attention":0,"noface":0,"face_mismatch":0})
        s.setdefault("attention_strikes", 0)
        s.setdefault("noface_strikes", 0)
        s.setdefault("last_decision", "clear")
        s.setdefault("face_verified_once", False)
        s.setdefault("warn_cooldown", 0)

        # --- Decode ---
        if save:
            cap = self.cam.capture_frame_from_base64(base64_img, self.attempt_id, frame_no)
            if not cap.get("success"):
                return {"ok": False, "error": cap.get("error", "decode_fail")}
            with open(cap["filepath"], "rb") as f:
                img_bytes = f.read()
        else:
            try:
                from services.camera_capture_service import decode_base64_image
                img_bytes = decode_base64_image(base64_img)
            except Exception:
                # Fallback: try direct decode
                try:
                    import base64
                    if isinstance(base64_img, str):
                        if base64_img.startswith("data:image"):
                            base64_img = base64_img.split(",", 1)[-1]
                        img_bytes = base64.b64decode(base64_img, validate=False)
                    else:
                        img_bytes = base64_img
                except Exception as e:
                    return {"ok": False, "error": f"decode_fail: {e}"}

        if not img_bytes:
            return {"ok": False, "error": "decode_fail"}

        # --- Analyze ---
        analysis = self.face.detect_faces_and_objects(img_bytes) or {}
        analysis = self.augment.enrich(analysis)  # NEW: add proba, pose, suspicious filtering

        faces        = int(analysis.get("face_count") or 0)
        # Prefer calibrated probability if present; fallback to legacy score
        att          = float(analysis.get("attention_proba") if analysis.get("attention_proba") is not None else analysis.get("attention_score") or 0.0)
        looking_away = bool(analysis.get("looking_away"))
        eyes_closed  = bool(analysis.get("eyes_closed"))
        att_alert    = bool(analysis.get("attention_alert"))
        suspicious   = analysis.get("suspicious_objects") or []
        svc_cheat    = bool(analysis.get("cheating_detected"))
        svc_reason   = (analysis.get("cheating_reason") or "").strip()

        decision = "clear"
        reasons: list[str] = []
        evidence_path: Optional[str] = None

        # Cooldown giảm dần
        if s["warn_cooldown"] > 0:
            s["warn_cooldown"] -= 1

        # RULE 0: Ưu tiên cờ tức thì từ service
        if svc_cheat:
            decision = "flagged"
            reasons.append(svc_reason or "Vi phạm tức thì từ bộ nhận diện")
            if "khuôn mặt" in svc_reason.lower():
                s["violation_counts"]["multi_face"] += 1
            if suspicious:
                s["violation_counts"]["objects"] += 1

        # RULE 1: Tức thì nội bộ (nếu chưa flag)
        if decision != "flagged":
            if faces > 1:
                decision = "flagged"; reasons.append(f"Phát hiện {faces} khuôn mặt")
                s["violation_counts"]["multi_face"] += 1
            if suspicious:
                decision = "flagged"; reasons.append("Phát hiện vật thể đáng ngờ (điện thoại/tài liệu)")
                s["violation_counts"]["objects"] += 1

        # RULE 2: Không thấy mặt & Thiếu tập trung (nếu chưa flag)
        if decision != "flagged":
            # không thấy mặt liên tiếp
            if faces == 0:
                s["noface_strikes"] += 1
                if s["noface_strikes"] >= getattr(self.cfg, "NOFACE_STRIKES_TO_FLAG", 3):
                    decision = "flagged"; reasons.append("Không thấy khuôn mặt nhiều khung liên tiếp")
                    s["violation_counts"]["noface"] += 1
            else:
                s["noface_strikes"] = 0

            attention_min = getattr(self.cfg, "ATTENTION_MIN", 0.50)
            low_attention = (att < attention_min) or looking_away or eyes_closed or att_alert
            if faces == 1 and low_attention:
                s["attention_strikes"] += 1
                if s["attention_strikes"] >= getattr(self.cfg, "ATTENTION_STRIKES_TO_FLAG", 4):
                    decision = "flagged"; reasons.append("Thiếu tập trung liên tiếp nhiều lần")
                    s["violation_counts"]["attention"] += 1
                elif s["attention_strikes"] >= getattr(self.cfg, "ATTENTION_STRIKES_TO_WARN", 2):
                    if s["warn_cooldown"] == 0:
                        decision = "warn"; reasons.append("Dấu hiệu thiếu tập trung")
                        s["warn_cooldown"] = getattr(self.cfg, "WARN_COOLDOWN_FRAMES", 5)
            else:
                if not low_attention:
                    s["attention_strikes"] = 0

        # RULE 3: Đối chiếu avatar định kỳ (nếu chưa flag)
        reverify_n = getattr(self.cfg, "REVERIFY_EVERY_N_FRAMES", 30)
        need_verify = (not s["face_verified_once"]) or (frame_no % reverify_n == 0)
        if faces >= 1 and need_verify and decision != "flagged" and getattr(self, "avatar_bytes", None):
            verify = self.face.verify_user_face(img_bytes, self.avatar_bytes) or {}
            conf = float(verify.get("confidence") or 0.0)
            if not bool(verify.get("verified")):
                decision = "flagged"; reasons.append(f"Khuôn mặt không khớp avatar (conf={conf:.2f})")
                s["violation_counts"]["face_mismatch"] += 1
            else:
                s["face_verified_once"] = True

        # Evidence
        if decision in ("warn", "flagged") and getattr(self.cfg, "SAVE_EVIDENCE", True):
            try:
                cap2 = self.cam.capture_frame_from_base64(base64_img, self.attempt_id, frame_no)
                if cap2.get("success"):
                    evidence_path = cap2["filepath"]
            except Exception:
                evidence_path = None

        # Update state
        if decision == "flagged":
            for r in reasons: self._escalate("flagged", r)
        elif decision == "warn":
            for r in reasons: self._escalate("warn", r)
        else:
            s["last_decision"] = "clear"

        return {
            "ok": True,
            "frame_no": frame_no,
            "decision": decision,
            "reasons": reasons,
            "evidence_path": evidence_path,
            "metrics": {
                "faces": faces,
                "attention_score": att,
                "attention_percent": round(att*100.0, 1),
                "looking_away": looking_away,
                "eyes_closed": eyes_closed,
                "suspicious_count": len(suspicious)
            },
            "state": {
                "attention_strikes": s["attention_strikes"],
                "noface_strikes": s["noface_strikes"],
                "last_decision": s["last_decision"],
                "face_verified_once": s["face_verified_once"],
                "violation_counts": s["violation_counts"],
                "warn_cooldown": s["warn_cooldown"]
            }
        }
        
        
    def process_file(self, path: str) -> Dict:
        with open(path, "rb") as f:
            raw = f.read()
        # dùng cùng pipeline như base64
        analysis = self.face.detect_faces_and_objects(raw) or {}
        analysis = self.augment.enrich(analysis)
        # ... (tái sử dụng phần tổng hợp quyết định như trong process_base64_frame)
        # rút gọn: chỉ trả metric chính để test nhanh
        return {
            "faces": int(analysis.get("face_count") or 0),
            "attention_percent": round(float(analysis.get("attention_proba") if analysis.get("attention_proba") is not None else analysis.get("attention_score") or 0.0)*100, 1),
            "suspicious": len(analysis.get("suspicious_objects") or []),
            "should_block": bool(analysis.get("should_block")),
            "should_warn": bool(analysis.get("should_warn")),
            "reasons": analysis.get("cheating_reason")
        }