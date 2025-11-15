# -*- coding: utf-8 -*-
"""
Attention Calibrator - Sử dụng model LogisticRegression đã train từ dataset
"""
import json
import os
import math
import numpy as np

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def load_calibration():
    """Load calibration từ file JSON"""
    path = os.getenv("ATTN_CALIB_PATH", "services/attention_calibration.json")
    
    # Thử nhiều vị trí
    candidates = [
        path,
        os.path.join("services", "attention_calibration.json"),
        "attention_calibration.json"
    ]
    
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"✅ Loaded calibration from: {p}")
                    return data
            except Exception as e:
                print(f"⚠️  Failed to load {p}: {e}")
    
    print("⚠️  No calibration file found, using defaults")
    return {}

class AttentionCalibrator:
    """
    Calibrator sử dụng LogisticRegression đã train từ dataset.
    Fallback về heuristic nếu model chưa được train.
    """
    
    def __init__(self):
        data = load_calibration()
        env = data.get("suggest_env") or {}
        
        # Load thresholds (fallback về env hoặc defaults)
        self.yaw_max = float(os.getenv("ATTN_YAW_MAX", env.get("ATTN_YAW_MAX", 35)))
        self.pitch_max = float(os.getenv("ATTN_PITCH_MAX", env.get("ATTN_PITCH_MAX", 28)))
        self.att_thr = float(os.getenv("ATTENTION_ALERT_THRESHOLD", env.get("ATTENTION_ALERT_THRESHOLD", 0.62)))
        
        # Load LogisticRegression weights
        self.lr = (data.get("logreg") or {}).get("weights")
        self.lr_cheat = (data.get("cheat_logreg") or {}).get("weights")
        
        # Load multi-class cheat type classifier
        self.cheat_type_model = None
        self.cheat_type_classes = []
        cheat_type_data = data.get("cheat_type_classifier") or {}
        if "model" in cheat_type_data:
            self.cheat_type_model = cheat_type_data["model"]
            self.cheat_type_classes = cheat_type_data.get("classes", [])
        elif "cheat_type_model_b64" in data:
            try:
                import pickle
                import base64
                model_bytes = base64.b64decode(data["cheat_type_model_b64"])
                self.cheat_type_model = pickle.loads(model_bytes)
                self.cheat_type_classes = data.get("cheat_type_classes", [])
            except Exception as e:
                print(f"⚠️  Failed to load cheat type model: {e}")
        
        # Cheat thresholds - giảm để phát hiện sớm hơn
        self.warn_p = float(os.getenv("CHEAT_WARN_PROBA", "0.45"))   # Giảm từ 0.60
        self.block_p = float(os.getenv("CHEAT_BLOCK_PROBA", "0.65"))  # Giảm từ 0.75
        
        # Log thông tin model
        if self.lr:
            print(f"✅ Using trained LogisticRegression for attention (weights: {list(self.lr.keys())})")
        else:
            print(f"⚠️  No trained model, using heuristic with thresholds: yaw_max={self.yaw_max}°, pitch_max={self.pitch_max}°, att_thr={self.att_thr}")
        
        if self.lr_cheat:
            print(f"✅ Using trained LogisticRegression for cheat detection")
        else:
            print(f"⚠️  No cheat model, using heuristic")
        
        if self.cheat_type_model:
            print(f"✅ Using multi-class cheat type classifier with {len(self.cheat_type_classes)} classes: {self.cheat_type_classes}")
        else:
            print(f"⚠️  No cheat type classifier, using binary classification only")
    
    def attentive_proba(self, yaw, pitch, att):
        """
        Tính xác suất tập trung (0.0 = không tập trung, 1.0 = tập trung hoàn toàn)
        
        QUAN TRỌNG: Ưu tiên model đã train từ dataset!
        """
        # 1) Nếu có model LogisticRegression → dùng ngay
        if self.lr:
            try:
                z = (self.lr["bias"] +
                     self.lr["yaw"] * yaw +
                     self.lr["pitch"] * pitch +
                     self.lr["att"] * att)
                proba = float(_sigmoid(z))
                
                # Clamp về [0, 1]
                return max(0.0, min(1.0, proba))
            except Exception as e:
                print(f"⚠️  Model inference error: {e}, falling back to heuristic")
        
        # 2) Fallback: heuristic chuẩn hóa theo threshold
        ny = max(0.0, 1.0 - abs(yaw) / max(1.0, self.yaw_max))
        np_val = max(0.0, 1.0 - abs(pitch) / max(1.0, self.pitch_max))
        
        # Weighted average
        heuristic = 0.4 * att + 0.3 * ny + 0.3 * np_val
        return float(max(0.0, min(1.0, heuristic)))
    
    def pose_label_and_conf(self, yaw, pitch):
        """
        Phân loại hướng nhìn từ yaw/pitch
        Returns: (label, confidence)
        """
        ay, ap = abs(yaw), abs(pitch)
        
        # Forward zone
        fwd = (ay < self.yaw_max * 0.45 and ap < self.pitch_max * 0.45)
        if fwd:
            d = max(ay / max(1.0, self.yaw_max), ap / max(1.0, self.pitch_max))
            return "forward", float(1.0 - d)
        
        # Horizontal vs Vertical
        if ay / (ap + 1e-6) >= 1.2:  # Nghiêng ngang
            if yaw > 0:
                conf = min(1.0, ay / max(1.0, self.yaw_max))
                return "look_right", float(conf)
            else:
                conf = min(1.0, ay / max(1.0, self.yaw_max))
                return "look_left", float(conf)
        else:  # Nghiêng dọc
            if pitch > 0:
                conf = min(1.0, ap / max(1.0, self.pitch_max))
                return "look_down", float(conf)
            else:
                conf = min(1.0, ap / max(1.0, self.pitch_max))
                return "look_up", float(conf)
    
    def cheat_proba(self, yaw, pitch, att, susp_count, has_phone=0.0, has_book=0.0, has_tablet=0.0, pose_suspicious=0.0, pose_deviation=0.0):
        """
        Tính xác suất gian lận (0.0 = bình thường, 1.0 = gian lận rõ ràng)
        Hỗ trợ 4, 7, hoặc 9 features tùy theo model đã train
        """
        # 1) Nếu có model LogisticRegression → dùng ngay
        if self.lr_cheat:
            try:
                z = (self.lr_cheat["bias"] +
                     self.lr_cheat["yaw"] * yaw +
                     self.lr_cheat["pitch"] * pitch +
                     self.lr_cheat["att"] * att +
                     self.lr_cheat["susp"] * susp_count)
                
                # Nếu model có thêm features về object types
                if "has_phone" in self.lr_cheat:
                    z += self.lr_cheat["has_phone"] * float(has_phone)
                if "has_book" in self.lr_cheat:
                    z += self.lr_cheat["has_book"] * float(has_book)
                if "has_tablet" in self.lr_cheat:
                    z += self.lr_cheat["has_tablet"] * float(has_tablet)
                if "pose_suspicious" in self.lr_cheat:
                    z += self.lr_cheat["pose_suspicious"] * float(pose_suspicious)
                if "pose_deviation" in self.lr_cheat:
                    z += self.lr_cheat["pose_deviation"] * float(pose_deviation)
                
                proba = float(_sigmoid(z))
                return max(0.0, min(1.0, proba))
            except Exception as e:
                print(f"⚠️  Cheat model error: {e}, using heuristic")
        
        # 2) Fallback heuristic với object types và pose
        # Nhiều đồ gần mặt + attention thấp + lệch pose + có object gian lận => tăng xác suất
        object_penalty = 0.0
        if has_phone > 0.5:
            object_penalty += 0.25
        if has_book > 0.5:
            object_penalty += 0.20
        if has_tablet > 0.5:
            object_penalty += 0.20
        
        # Tính pose_deviation nếu chưa có
        if pose_deviation == 0.0:
            pose_deviation = max(abs(yaw) / max(1.0, self.yaw_max),
                                abs(pitch) / max(1.0, self.pitch_max))
        
        base = (0.30 * min(1.0, susp_count / 2.0) +
                0.20 * (1.0 - att) +
                0.15 * pose_deviation +
                0.20 * min(1.0, object_penalty) +
                0.15 * float(pose_suspicious))
        return float(max(0.0, min(1.0, base)))
    
    def predict_cheat_type(self, yaw, pitch, att, susp_count, has_phone=0.0, has_book=0.0, has_tablet=0.0, pose_suspicious=0.0, pose_deviation=0.0):
        """
        Dự đoán loại gian lận cụ thể (multi-class) với logic ưu tiên rõ ràng
        Returns: (cheat_type, confidence)
        
        Thứ tự ưu tiên:
        1. Objects được phát hiện (phone, book, tablet) - chính xác nhất
        2. Pose-based detection (looking_down, looking_away)
        3. Model prediction (nếu có)
        4. Fallback heuristic
        """
        # ƯU TIÊN 1: Objects được phát hiện - chính xác nhất
        # Giảm threshold để phát hiện sớm hơn (từ 0.5 xuống 0.3)
        if has_phone > 0.3:
            return "phone", min(0.95, 0.7 + (has_phone - 0.3) * 0.5)
        if has_book > 0.3:
            return "book", min(0.95, 0.7 + (has_book - 0.3) * 0.5)
        if has_tablet > 0.3:
            return "tablet", min(0.95, 0.7 + (has_tablet - 0.3) * 0.5)
        
        # ƯU TIÊN 2: Pose-based detection (cúi xuống, nhìn ra ngoài)
        pitch_abs = abs(pitch)
        yaw_abs = abs(yaw)
        
        # Cúi xuống (pitch dương = cúi xuống)
        if pitch > 20.0:
            # Cúi xuống nhiều = có thể đang xem tài liệu
            confidence = min(0.9, 0.5 + (pitch - 20.0) / 30.0)
            return "looking_down", confidence
        
        # Nhìn ra ngoài (yaw hoặc pitch lớn)
        if yaw_abs > 30.0 or pitch_abs > 25.0:
            # Nhìn ra ngoài nhiều = có thể đang gian lận
            max_deviation = max(yaw_abs / 60.0, pitch_abs / 45.0)
            confidence = min(0.9, 0.5 + max_deviation * 0.4)
            return "looking_away", confidence
        
        # ƯU TIÊN 3: Model prediction (nếu có)
        if self.cheat_type_model and len(self.cheat_type_classes) > 0:
            try:
                # Tạo feature vector giống như training
                features = np.array([[
                    yaw, pitch, att, susp_count,
                    float(has_phone),
                    float(has_book),
                    float(has_tablet),
                    float(pose_suspicious),
                    float(pose_deviation)
                ]])
                
                # Predict
                prediction = self.cheat_type_model.predict(features)[0]
                probabilities = self.cheat_type_model.predict_proba(features)[0]
                
                # Tìm class có xác suất cao nhất
                if prediction in self.cheat_type_classes:
                    class_idx = list(self.cheat_type_classes).index(prediction)
                    confidence = float(probabilities[class_idx]) if class_idx < len(probabilities) else 0.0
                    
                    # Chỉ trả về nếu confidence đủ cao và không phải "normal"
                    if confidence > 0.5 and prediction != "normal":
                        return str(prediction), confidence
            except Exception as e:
                print(f"⚠️  Cheat type prediction error: {e}")
        
        # ƯU TIÊN 4: Fallback heuristic dựa trên pose và suspicious count
        if susp_count > 0:
            # Có suspicious objects nhưng không xác định được loại
            return "cheating_generic", min(0.7, 0.4 + susp_count * 0.1)
        
        if pose_suspicious > 0.5 or pose_deviation > 0.6:
            # Pose đáng ngờ nhưng không có objects
            return "cheating_generic", 0.5
        
        # Không có dấu hiệu gian lận
        return "normal", 0.0