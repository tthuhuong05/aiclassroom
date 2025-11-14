

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


def _format_object_labels(objs: List[Dict[str, Any]]) -> str | None:
    """
    Trả về chuỗi mô tả danh sách vật thể đáng ngờ (loại bỏ person, giữ tối đa 3 loại)
    """
    if not objs:
        return None
    names: List[str] = []
    for obj in objs:
        label = (
            obj.get("type")
            or obj.get("label")
            or obj.get("class")
            or obj.get("cls")
            or ""
        )
        label = str(label).strip().lower()
        if not label or label == "person":
            continue
        label = label.replace("_", " ")
        conf = obj.get("confidence") or obj.get("conf") or obj.get("score")
        if isinstance(conf, (int, float)) and conf > 0:
            label = f"{label} ({conf:.0%})"
        names.append(label)
    if not names:
        return None
    unique = list(dict.fromkeys(names))[:3]
    return ", ".join(unique)

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
        # Dùng _Calib: nếu attention_calibration import được -> dùng model đã train
        # Nếu không -> dùng fallback heuristic ở trên
        self.cal = _Calib()
        self._ema_att: float | None = None
        self._ema_alpha: float = 0.3     # trọng số cho frame mới

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
        objs: List[Dict[str, Any]] = []
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
        face_count = int(r.get("face_count") or 0)

        # KIỂM TRA KHÔNG CÓ MẶT - CẢNH BÁO NGAY
        if face_count == 0:
            # Không có mặt = rất nghi vấn
            r["should_warn"] = True
            r.setdefault("cheating_reason", "Không phát hiện khuôn mặt trong camera - Vui lòng điều chỉnh camera")
            # Nếu không có mặt quá lâu thì block
            if not r.get("should_block"):
                # Có thể thêm logic block nếu cần
                pass
        
        # Attention probability (0..1) từ model đã train / heuristic
        # Chỉ tính nếu có mặt
        if face_count > 0:
            p_att = self.cal.attentive_proba(yaw, pitch, att)
            # EMA cho mượt bớt dao động
            if self._ema_att is None:
                self._ema_att = p_att
            else:
                self._ema_att = self._ema_alpha * p_att + (1.0 - self._ema_alpha) * self._ema_att

            r["attention_proba"] = float(self._ema_att)
            r["attention_alert"] = (r["attention_proba"] < self.cal.att_thr)

            label, conf = self.cal.pose_label_and_conf(yaw, pitch)
            r["pose_label"] = label
            r["pose_conf"] = conf
            
            # LƯU Ý: Không set looking_away/looking_down ở đây
            # Sẽ được xử lý sau khi kiểm tra objects để ưu tiên objects hơn
        else:
            # Không có mặt: attention = 0, alert = True
            r["attention_proba"] = 0.0
            r["attention_alert"] = True
            r["pose_label"] = "no_face"
            r["pose_conf"] = 0.0
            if self._ema_att is not None:
                # Decay EMA khi không có mặt
                self._ema_att = self._ema_att * 0.9

        # Cheat probability - extract object types và pose features từ suspicious_objects
        suspicious_objs = r.get("suspicious_objects") or []
        object_summary = _format_object_labels(suspicious_objs)
        if object_summary:
            r["suspicious_summary"] = object_summary
        detected_classes = [obj.get("type", "").lower() or obj.get("label", "").lower() 
                           for obj in suspicious_objs]
        
        # Phát hiện objects với độ chính xác cao hơn
        phone_keywords = ["cell phone", "mobile phone", "phone", "smartphone", "iphone", "android"]
        book_keywords = ["book", "paper", "sheet of paper", "notebook", "textbook"]
        tablet_keywords = ["tablet", "laptop", "notebook computer", "ipad"]
        
        has_phone = 1.0 if any(any(kw in cls for kw in phone_keywords) for cls in detected_classes) else 0.0
        has_book = 1.0 if any(any(kw in cls for kw in book_keywords) for cls in detected_classes) else 0.0
        has_tablet = 1.0 if any(any(kw in cls for kw in tablet_keywords) for cls in detected_classes) else 0.0
        
        # Extract pose-based features với độ chính xác cao hơn
        pose_label = r.get("pose_label", "").lower()
        pose_cheat_indicators = ["look_down", "look_left", "look_right", "look_out", 
                                "cheating", "self_camera", "call", "phone_near", "book_near"]
        pose_suspicious = 1.0 if any(ind in pose_label for ind in pose_cheat_indicators) else 0.0
        pose_deviation = max(abs(yaw) / max(1.0, self.cal.yaw_max), 
                            abs(pitch) / max(1.0, self.cal.pitch_max))
        
        if hasattr(self.cal, "cheat_proba"):
            # Sử dụng model với đầy đủ features (9 features)
            p_cheat = self.cal.cheat_proba(yaw, pitch, att, susp, has_phone, has_book, has_tablet, 
                                          pose_suspicious, pose_deviation)
        else:
            # fallback đơn giản: cheat nếu có nhiều vật thể nghi vấn
            p_cheat = 1.0 if susp >= 1 else 0.0

        r["cheat_proba"] = float(p_cheat)
        
        # Dự đoán loại gian lận cụ thể (multi-class)
        # ƯU TIÊN: Objects được phát hiện > Pose-based detection (looking_away/looking_down)
        
        # BƯỚC 1: Kiểm tra objects TRƯỚC (ưu tiên cao nhất)
        # Giảm threshold để phát hiện sớm hơn (từ 0.5 xuống 0.3)
        if has_phone > 0.3:
            r["cheat_type"] = "phone"
            r["cheat_type_confidence"] = min(0.95, 0.7 + (has_phone - 0.3) * 0.5)  # Confidence động
            r["cheating_reason"] = "⚠️ PHÁT HIỆN ĐIỆN THOẠI - Có thể đang tra cứu đáp án hoặc nhận hỗ trợ từ bên ngoài"
        elif has_book > 0.3:
            r["cheat_type"] = "book"
            r["cheat_type_confidence"] = min(0.95, 0.7 + (has_book - 0.3) * 0.5)
            r["cheating_reason"] = "⚠️ PHÁT HIỆN SÁCH/TÀI LIỆU - Có thể đang tra cứu đáp án"
        elif has_tablet > 0.3:
            r["cheat_type"] = "tablet"
            r["cheat_type_confidence"] = min(0.95, 0.7 + (has_tablet - 0.3) * 0.5)
            r["cheating_reason"] = "⚠️ PHÁT HIỆN TABLET/LAPTOP - Có thể đang tra cứu tài liệu"
        elif susp > 0 or len(suspicious_objs) > 0:
            # Có suspicious objects nhưng không xác định được loại cụ thể
            if hasattr(self.cal, "predict_cheat_type"):
                cheat_type, type_confidence = self.cal.predict_cheat_type(
                    yaw, pitch, att, susp, has_phone, has_book, has_tablet, 
                    pose_suspicious, pose_deviation
                )
                # Chỉ sử dụng nếu không phải "normal" hoặc "unknown"
                if cheat_type not in ["normal", "unknown"]:
                    r["cheat_type"] = cheat_type
                    r["cheat_type_confidence"] = float(type_confidence)
                else:
                    r["cheat_type"] = "cheating_generic"
                    r["cheat_type_confidence"] = 0.6
                    message_detail = f" ({object_summary})" if object_summary else ""
                    r["cheating_reason"] = f"⚠️ PHÁT HIỆN VẬT THỂ ĐÁNG NGỜ{message_detail} - Vui lòng tập trung vào bài thi"
            else:
                r["cheat_type"] = "cheating_generic"
                r["cheat_type_confidence"] = 0.6
                message_detail = f" ({object_summary})" if object_summary else ""
                r["cheating_reason"] = f"⚠️ PHÁT HIỆN VẬT THỂ ĐÁNG NGỜ{message_detail} - Vui lòng tập trung vào bài thi"
        # BƯỚC 2: Nếu không có objects, mới kiểm tra pose-based detection
        elif hasattr(self.cal, "predict_cheat_type"):
            cheat_type, type_confidence = self.cal.predict_cheat_type(
                yaw, pitch, att, susp, has_phone, has_book, has_tablet, 
                pose_suspicious, pose_deviation
            )
            r["cheat_type"] = cheat_type
            r["cheat_type_confidence"] = float(type_confidence)
            
            # Tạo thông báo cụ thể dựa trên loại gian lận với ngữ cảnh phù hợp
            # Thông báo chi tiết và cụ thể cho từng loại gian lận
            type_messages = {
                "phone": "⚠️ PHÁT HIỆN ĐIỆN THOẠI - Có thể đang tra cứu đáp án hoặc nhận hỗ trợ từ bên ngoài",
                "phone_call": "⚠️ PHÁT HIỆN ĐANG GỌI ĐIỆN - Có thể đang nhận hỗ trợ từ bên ngoài",
                "phone_selfie": "⚠️ PHÁT HIỆN SELFIE/CAMERA - Có thể đang chụp màn hình bài thi",
                "phone_screenshot": "⚠️ PHÁT HIỆN CHỤP MÀN HÌNH - Có thể đang lưu đề thi",
                "book": "⚠️ PHÁT HIỆN SÁCH/TÀI LIỆU - Có thể đang tra cứu đáp án",
                "tablet": "⚠️ PHÁT HIỆN TABLET/LAPTOP - Có thể đang tra cứu tài liệu",
                "glasses_suspicious": "⚠️ PHÁT HIỆN HÀNH VI ĐÁNG NGỜ VỚI KÍNH - Có thể đang sử dụng thiết bị hỗ trợ",
                "looking_away": "⚠️ PHÁT HIỆN NHÌN RA NGOÀI MÀN HÌNH - Có thể đang xem tài liệu hoặc nhận hỗ trợ",
                "looking_down": "⚠️ PHÁT HIỆN CÚI XUỐNG - Có thể đang xem tài liệu gian lận dưới bàn",
                "cheating_generic": "⚠️ PHÁT HIỆN HÀNH VI GIAN LẬN - Vui lòng tập trung vào bài thi",
                "unknown_cheat": "⚠️ PHÁT HIỆN HÀNH VI ĐÁNG NGỜ - Vui lòng điều chỉnh tư thế và tập trung"
            }
            cheat_message = type_messages.get(cheat_type, f"⚠️ PHÁT HIỆN HÀNH VI GIAN LẬN: {cheat_type}")
            r["cheating_reason"] = cheat_message
        # BƯỚC 3: Fallback - kiểm tra pose-based detection nếu không có model
        else:
            # Kiểm tra cúi xuống và nhìn ra ngoài
            pitch_down_threshold = float(os.getenv("PITCH_DOWN_THRESHOLD", "20.0"))
            yaw_away_threshold = float(os.getenv("YAW_AWAY_THRESHOLD", "30.0"))
            pitch_away_threshold = float(os.getenv("PITCH_AWAY_THRESHOLD", "25.0"))
            
            is_looking_down = pitch > pitch_down_threshold
            is_looking_away = abs(yaw) > yaw_away_threshold or abs(pitch) > pitch_away_threshold
            
            if is_looking_down:
                r["cheat_type"] = "looking_down"
                r["cheat_type_confidence"] = min(1.0, abs(pitch) / 45.0)
                r["cheating_reason"] = "⚠️ PHÁT HIỆN CÚI XUỐNG - Có thể đang xem tài liệu gian lận dưới bàn"
            elif is_looking_away:
                r["cheat_type"] = "looking_away"
                r["cheat_type_confidence"] = min(1.0, max(abs(yaw) / 60.0, abs(pitch) / 45.0))
                r["cheating_reason"] = "⚠️ PHÁT HIỆN NHÌN RA NGOÀI MÀN HÌNH - Có thể đang xem tài liệu hoặc nhận hỗ trợ"
            elif pose_suspicious > 0.5 or pose_deviation > 0.6:
                r["cheat_type"] = "cheating_generic"
                r["cheat_type_confidence"] = 0.5
                r["cheating_reason"] = "⚠️ PHÁT HIỆN HÀNH VI GIAN LẬN - Vui lòng tập trung vào bài thi"
            else:
                r["cheat_type"] = "unknown"
                r["cheat_type_confidence"] = 0.0
        
        # Nếu nhìn xuống nhưng mặt vẫn thấy rõ -> không coi là gian lận
        if r.get("cheat_type") == "looking_down":
            if face_count > 0:
                # Vẫn thấy mặt trong khung -> không coi là gian lận
                r["cheat_type"] = "normal"
                r["cheat_type_confidence"] = 0.0
                r["cheating_reason"] = None
                r["cheating_note"] = "lookdown_face_present"
            else:
                # Không có mặt mới coi là gian lận
                r["cheating_reason"] = r.get("cheating_reason") or "⚠️ KHÔNG THẤY KHUÔN MẶT - Có thể đang cúi tránh camera"
        
        # QUAN TRỌNG: Nếu cheat_type = "normal" thì KHÔNG được coi là gian lận
        if r.get("cheat_type") == "normal":
            # Reset các flag gian lận
            r["should_block"] = False
            r["should_warn"] = False
            r["cheating_detected"] = False
            r["cheating_reason"] = None  # Không có lý do gian lận
            r["cheat_proba"] = 0.0  # Reset cheat probability
            return r  # Trả về ngay, không xử lý thêm
        
        # Giảm threshold để phát hiện sớm hơn (từ 0.80 xuống 0.65, từ 0.55 xuống 0.45)
        block_threshold = getattr(self.cal, "block_p", 0.65)  # Giảm từ 0.80
        warn_threshold = getattr(self.cal, "warn_p", 0.45)   # Giảm từ 0.55
        
        # CHỈ set should_block/should_warn khi:
        # 1. cheat_type KHÔNG phải "normal"
        # 2. Có suspicious objects HOẶC cheat_proba cao
        # 3. Hoặc không có mặt (face_count = 0)
        if r.get("cheat_type") != "normal":
            # ƯU TIÊN 1: Nếu có objects được phát hiện (phone, book, tablet) -> chắc chắn block
            if r.get("cheat_type") in ["phone", "book", "tablet"]:
                r["should_block"] = True
                r["cheating_detected"] = True
                # cheating_reason đã được set ở trên
            # ƯU TIÊN 2: Nếu có suspicious objects (không xác định được loại) -> block hoặc warn
            elif susp > 0 or len(suspicious_objs) > 0:
                r["should_block"] = True
                r["cheating_detected"] = True
                if not r.get("cheating_reason"):
                    message_detail = f" ({object_summary})" if object_summary else ""
                    r["cheating_reason"] = f"Phát hiện vật thể đáng ngờ{message_detail} - Vui lòng tập trung vào bài thi"
            # ƯU TIÊN 3: Nếu có looking_down/looking_away -> warn hoặc block tùy độ nghiêm trọng
            elif r.get("cheat_type") in ["looking_down", "looking_away"]:
                # Kiểm tra độ nghiêm trọng
                pitch_down_threshold = float(os.getenv("PITCH_DOWN_THRESHOLD", "20.0"))
                yaw_away_threshold = float(os.getenv("YAW_AWAY_THRESHOLD", "30.0"))
                pitch_away_threshold = float(os.getenv("PITCH_AWAY_THRESHOLD", "25.0"))
                
                is_looking_down = pitch > pitch_down_threshold
                is_looking_away = abs(yaw) > yaw_away_threshold or abs(pitch) > pitch_away_threshold
                
                # Nếu cúi xuống hoặc nhìn ra ngoài quá nhiều thì block
                if (is_looking_down and pitch > 30.0) or (is_looking_away and (abs(yaw) > 40.0 or abs(pitch) > 35.0)):
                    r["should_block"] = True
                    r["cheating_detected"] = True
                else:
                    r["should_warn"] = True
            # ƯU TIÊN 4: Dựa trên cheat_proba từ model
            elif p_cheat >= block_threshold:
                r["should_block"] = True
                r["cheating_detected"] = True
                if not r.get("cheating_reason"):
                    r["cheating_reason"] = "Phát hiện hành vi gian lận - Xác suất cao"
            elif p_cheat >= warn_threshold:
                r["should_warn"] = True
                if not r.get("cheating_reason"):
                    r["cheating_reason"] = "Phát hiện hành vi gian lận - Cảnh báo"

        return r




