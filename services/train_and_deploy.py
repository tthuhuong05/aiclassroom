#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Train models từ attention_dataset và deploy vào production
Chạy: python services/train_and_deploy.py
"""

import os
import sys
import json
import csv
import math
import numpy as np
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent
DS = ROOT / "attention_dataset"
CSV_PATH = DS / "annotations.csv"
OUT_PATH = ROOT / "attention_calibration.json"

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))

def load_dataset():
    """Đọc dataset và extract features với cải thiện mapping YOLO classes
    Hỗ trợ multi-class classification cho các loại gian lận khác nhau
    """
    from services.face_recognition_service import get_face_recognition_service
    
    print("🔄 Loading FaceRecognitionService...")
    svc = get_face_recognition_service()
    
    X_att, y_att = [], []  # Attention data
    X_cheat, y_cheat = [], []  # Cheat detection data (binary)
    X_cheat_type, y_cheat_type = [], []  # Cheat type classification (multi-class)
    
    print(f"📂 Reading annotations from: {CSV_PATH}")
    
    if not CSV_PATH.exists():
        print(f"❌ ERROR: {CSV_PATH} not found!")
        return None, None, None, None, None, None
    
    # Mapping từ CSV labels sang YOLO classes
    cheat_object_mapping = {
        "book": ["book", "paper", "sheet of paper"],
        "phone": ["cell phone", "mobile phone", "phone", "smartphone"],
        "tablet": ["tablet", "laptop", "notebook"],
        "call": ["cell phone", "mobile phone", "phone", "smartphone"],
        "screenshot": ["cell phone", "mobile phone", "phone", "smartphone", "laptop", "tablet"],
        "self-camera": ["cell phone", "mobile phone", "phone", "smartphone"],
        "phone_near": ["cell phone", "mobile phone", "phone", "smartphone"],
        "book_near": ["book", "paper", "sheet of paper"]
    }
    
    # Mapping từ pose_label sang cheat_type (multi-class)
    def map_pose_to_cheat_type(pose_label, cheat_label):
        """Map pose_label và cheat_label thành loại gian lận cụ thể"""
        if cheat_label != "yes":
            return "normal"
        
        pose_lower = pose_label.lower()
        
        # Phone-related (ưu tiên cao nhất - kiểm tra cụ thể trước)
        if "call" in pose_lower:
            return "phone_call"
        if "self_camera" in pose_lower or "self-camera" in pose_lower or "selfcamera" in pose_lower:
            return "phone_selfie"
        if "screenshot" in pose_lower:
            return "phone_screenshot"
        if "phone_near" in pose_lower or ("phone" in pose_lower and "near" in pose_lower):
            return "phone"
        if "phone" in pose_lower:
            return "phone"
        
        # Book-related
        if "book_near" in pose_lower or ("book" in pose_lower and "near" in pose_lower):
            return "book"
        if "takebook" in pose_lower or "take_book" in pose_lower or "take book" in pose_lower:
            return "book"
        if "book" in pose_lower:
            return "book"
        
        # Tablet/Laptop
        if "tablet" in pose_lower or "laptop" in pose_lower:
            return "tablet"
        
        # Glasses (có thể che giấu)
        if "glasses" in pose_lower:
            return "glasses_suspicious"
        
        # Look away (có thể đang nhìn tài liệu)
        if "look_out" in pose_lower or "lookout" in pose_lower:
            return "looking_away"
        if "look_down" in pose_lower or "lookdown" in pose_lower:
            return "looking_down"
        
        # Generic cheating
        if "cheating" in pose_lower:
            return "cheating_generic"
        
        return "unknown_cheat"
    
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        print(f"📊 Found {len(rows)} annotated images")
        
        for idx, row in enumerate(rows, 1):
            fn = row["filename"]
            att_label = (row.get("attention_label") or "").strip().lower()
            cheat_label = (row.get("cheat_label") or "").strip().lower()
            pose_label = (row.get("pose_label") or "").strip().lower()
            
            # Tìm file ảnh
            img_path = None
            for candidate in [
                DS / fn,
                DS / "images" / fn,
                DS / fn.replace("\\", "/")
            ]:
                if candidate.exists():
                    img_path = candidate
                    break
            
            if not img_path or not img_path.exists():
                print(f"⚠️  Skip {fn}: file not found")
                continue
            
            # Phân tích ảnh với độ nhạy cao hơn
            try:
                with open(img_path, "rb") as f:
                    raw = f.read()
                
                # Tạm thời giảm threshold để phát hiện tốt hơn trong training
                import os
                old_conf = os.getenv("CHEAT_OBJ_CONF", "0.10")
                old_conf_roi = os.getenv("CHEAT_OBJ_CONF_ROI", "0.04")
                old_min_side = os.getenv("OBJ_MIN_SIDE_RATIO", "0.010")
                # Giảm threshold khi training để phát hiện nhiều objects hơn
                os.environ["CHEAT_OBJ_CONF"] = "0.08"  # Giảm từ 0.10 xuống 0.08
                os.environ["CHEAT_OBJ_CONF_ROI"] = "0.03"  # Giảm từ 0.04 xuống 0.03
                os.environ["OBJ_MIN_SIDE_RATIO"] = "0.008"  # Giảm từ 0.010 xuống 0.008
                os.environ["OBJ_EXTRA_SCALE"] = "4.0"  # Tăng vùng scan
                os.environ["NEAR_FACE_EXPAND"] = "4.0"  # Mở rộng vùng near_face
                
                result = svc.detect_faces_and_objects(raw)
                
                # Khôi phục threshold
                os.environ["CHEAT_OBJ_CONF"] = old_conf
                os.environ["CHEAT_OBJ_CONF_ROI"] = old_conf_roi
                os.environ["OBJ_MIN_SIDE_RATIO"] = old_min_side
                
                if result.get("error"):
                    print(f"⚠️  Skip {fn}: {result['error']}")
                    continue
                
                pose = result.get("head_pose") or {}
                yaw = float(pose.get("yaw", 0.0))
                pitch = float(pose.get("pitch", 0.0))
                att = float(result.get("attention_score", 0.0))
                susp = int(result.get("suspicious_count", 0))
                
                # Kiểm tra objects được phát hiện có khớp với label không
                suspicious_objs = result.get("suspicious_objects", [])
                detected_classes = [obj.get("type", "").lower() or obj.get("label", "").lower() 
                                   for obj in suspicious_objs]
                
                # Mở rộng danh sách keywords để phát hiện tốt hơn
                phone_keywords = ["cell phone", "mobile phone", "phone", "smartphone", "iphone", "android"]
                book_keywords = ["book", "paper", "sheet of paper", "notebook", "textbook"]
                tablet_keywords = ["tablet", "laptop", "notebook computer", "ipad"]
                
                # Kiểm tra với keywords mở rộng
                has_phone_detected = any(any(kw in cls for kw in phone_keywords) for cls in detected_classes)
                has_book_detected = any(any(kw in cls for kw in book_keywords) for cls in detected_classes)
                has_tablet_detected = any(any(kw in cls for kw in tablet_keywords) for cls in detected_classes)
                
                # Nếu cheat_label=yes nhưng không phát hiện object, có thể cần điều chỉnh
                if cheat_label == "yes" and susp == 0:
                    # Kiểm tra xem pose_label có gợi ý về object không
                    expected_classes = []
                    for key, classes in cheat_object_mapping.items():
                        if key in pose_label.lower():
                            expected_classes.extend(classes)
                    
                    if expected_classes:
                        print(f"⚠️  [{idx}/{len(rows)}] {fn}: Labeled as cheat but no objects detected. Expected: {expected_classes}")
                        # Vẫn tiếp tục training với pose-based features
                
                # Attention features
                if att_label in ("attentive", "not_attentive"):
                    X_att.append([yaw, pitch, att])
                    y_att.append(1 if att_label == "attentive" else 0)
                
                # Cheat features - cải thiện với thông tin objects và pose-based features
                if cheat_label in ("yes", "no"):
                    # Thêm thông tin về loại object nếu có (sử dụng keywords mở rộng)
                    has_phone = 1.0 if has_phone_detected else 0.0
                    has_book = 1.0 if has_book_detected else 0.0
                    has_tablet = 1.0 if has_tablet_detected else 0.0
                    
                    # Nếu không phát hiện được object nhưng label là "yes", 
                    # có thể object bị che hoặc không rõ, vẫn train với pose features
                    if cheat_label == "yes" and not (has_phone or has_book or has_tablet):
                        # Tăng weight cho pose_suspicious nếu có pose_label gợi ý
                        if any(key in pose_label.lower() for key in ["phone", "book", "tablet", "call", "screenshot"]):
                            pose_suspicious = 1.0  # Force suspicious nếu có gợi ý từ label
                    
                    # Thêm pose-based features từ pose_label
                    # Các pose có thể liên quan đến gian lận: look_down, look_left, look_right, look_out
                    pose_cheat_indicators = ["look_down", "look_left", "look_right", "look_out", 
                                            "cheating", "self_camera", "call", "phone_near", "book_near"]
                    pose_suspicious = 1.0 if any(ind in pose_label for ind in pose_cheat_indicators) else 0.0
                    
                    # Tính độ lệch pose (càng lệch càng nghi)
                    pose_deviation = max(abs(yaw) / 60.0, abs(pitch) / 45.0)  # Normalize
                    
                    # Feature vector mở rộng: [yaw, pitch, attention, suspicious_count, has_phone, has_book, has_tablet, pose_suspicious, pose_deviation]
                    X_cheat.append([
                        yaw, pitch, att, susp, 
                        has_phone, 
                        has_book, 
                        has_tablet,
                        pose_suspicious,
                        pose_deviation
                    ])
                    y_cheat.append(1 if cheat_label == "yes" else 0)
                    
                    # Multi-class classification: Xác định loại gian lận cụ thể
                    cheat_type = map_pose_to_cheat_type(pose_label, cheat_label)
                    
                    # Nếu có objects được phát hiện, ưu tiên sử dụng thông tin đó
                    if has_phone > 0.5:
                        cheat_type = "phone"
                    elif has_book > 0.5:
                        cheat_type = "book"
                    elif has_tablet > 0.5:
                        cheat_type = "tablet"
                    # Nếu không có objects nhưng label là "yes", giữ nguyên cheat_type từ pose_label
                    
                    # Train với tất cả samples (bao gồm cả "normal" để model học phân biệt)
                    X_cheat_type.append([
                        yaw, pitch, att, susp,
                        has_phone,
                        has_book,
                        has_tablet,
                        pose_suspicious,
                        pose_deviation
                    ])
                    y_cheat_type.append(cheat_type)
                
                # Log chi tiết hơn để debug
                cheat_type_labeled = map_pose_to_cheat_type(pose_label, cheat_label)
                print(f"✅ [{idx}/{len(rows)}] {fn}: yaw={yaw:.1f}° pitch={pitch:.1f}° att={att:.2f} susp={susp} "
                      f"detected={detected_classes} cheat_type={cheat_type_labeled} "
                      f"has_phone={has_phone_detected} has_book={has_book_detected} has_tablet={has_tablet_detected}")
                
            except Exception as e:
                print(f"⚠️  Skip {fn}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    print(f"\n📊 Dataset summary:")
    print(f"   - Attention samples: {len(X_att)}")
    print(f"   - Cheat samples (binary): {len(X_cheat)}")
    print(f"   - Cheat type samples (multi-class): {len(X_cheat_type)}")
    
    # Thống kê các loại gian lận
    if y_cheat_type:
        from collections import Counter
        type_counts = Counter(y_cheat_type)
        print(f"   - Cheat type distribution:")
        for cheat_type, count in type_counts.most_common():
            print(f"     * {cheat_type}: {count}")
    
    return (np.array(X_att, dtype=np.float32), np.array(y_att, dtype=np.int32),
            np.array(X_cheat, dtype=np.float32), np.array(y_cheat, dtype=np.int32),
            np.array(X_cheat_type, dtype=np.float32), np.array(y_cheat_type))

def train_attention_model(X, y):
    """Train LogisticRegression cho attention"""
    if len(X) == 0:
        print("⚠️  No attention data, skipping")
        return None
    
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, f1_score, classification_report
        
        print("\n🧠 Training Attention Model...")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, 
            stratify=y if len(set(y)) > 1 else None
        )
        
        # Train với tối ưu hóa
        clf = LogisticRegression(
            max_iter=1000,  # Tăng từ 500 lên 1000
            class_weight='balanced', 
            random_state=42,
            C=1.5,  # Tăng độ nhạy
            solver='lbfgs'  # Sử dụng solver tốt hơn
        )
        clf.fit(X_train, y_train)
        
        # Evaluate
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='binary')
        
        print(f"✅ Attention Model trained:")
        print(f"   - Accuracy: {acc:.3f}")
        print(f"   - F1-Score: {f1:.3f}")
        print(f"   - Training samples: {len(X_train)}")
        print(f"   - Test samples: {len(X_test)}")
        print("\n📊 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['Not Attentive', 'Attentive']))
        
        # Extract weights
        coef = clf.coef_[0].tolist()
        bias = float(clf.intercept_[0])
        
        return {
            "weights": {
                "yaw": coef[0],
                "pitch": coef[1],
                "att": coef[2],
                "bias": bias
            },
            "acc": float(acc),
            "f1": float(f1),
            "n_train": len(X_train),
            "n_test": len(X_test)
        }
        
    except ImportError:
        print("⚠️  sklearn not installed, using heuristic thresholds")
        return compute_heuristic_thresholds(X, y)

def compute_heuristic_thresholds(X, y):
    """Fallback: tính threshold từ phân bố dữ liệu"""
    yaw = np.abs(X[:, 0])
    pitch = np.abs(X[:, 1])
    att = X[:, 2]
    
    yaw_att = yaw[y == 1]
    yaw_not = yaw[y == 0]
    pitch_att = pitch[y == 1]
    pitch_not = pitch[y == 0]
    att_att = att[y == 1]
    
    def mid(a, b):
        if len(a) == 0 or len(b) == 0:
            return 30.0
        return float((np.percentile(a, 90) + np.percentile(b, 10)) / 2.0)
    
    yaw_max = mid(yaw_att, yaw_not)
    pitch_max = mid(pitch_att, pitch_not)
    att_thr = float(np.percentile(att_att if len(att_att) else att, 15))
    
    print(f"✅ Heuristic thresholds:")
    print(f"   - YAW_MAX: {yaw_max:.1f}°")
    print(f"   - PITCH_MAX: {pitch_max:.1f}°")
    print(f"   - ATT_THRESHOLD: {att_thr:.2f}")
    
    return {
        "ATTN_YAW_MAX": round(yaw_max, 1),
        "ATTN_PITCH_MAX": round(pitch_max, 1),
        "ATTENTION_ALERT_THRESHOLD": round(att_thr, 2)
    }

def train_cheat_type_model(X, y):
    """Train multi-class classifier cho các loại gian lận khác nhau"""
    if len(X) == 0:
        print("⚠️  No cheat type data, skipping")
        return None
    
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, f1_score, classification_report
        
        print("\n🧠 Training Cheat Type Classification Model (Multi-class)...")
        
        # Kiểm tra số features
        n_features = X.shape[1] if len(X.shape) > 1 else 1
        print(f"   - Input features: {n_features}")
        
        # Get unique classes
        unique_classes = list(set(y))
        print(f"   - Classes: {unique_classes}")
        
        if len(unique_classes) < 2:
            print("⚠️  Not enough classes for multi-class classification")
            return None
        
        # Split data - kiểm tra số lượng samples mỗi class trước khi stratify
        from collections import Counter
        class_counts = Counter(y)
        min_class_count = min(class_counts.values()) if class_counts else 0
        
        # Chỉ stratify nếu mỗi class có ít nhất 2 samples (cần cho train/test split)
        use_stratify = len(unique_classes) > 1 and min_class_count >= 2
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42,
            stratify=y if use_stratify else None
        )
        
        # Train multi-class LogisticRegression với tối ưu hóa
        # Tăng max_iter và điều chỉnh C để học tốt hơn
        clf = LogisticRegression(
            max_iter=2000,  # Tăng từ 1000 lên 2000 để học tốt hơn
            class_weight='balanced', 
            random_state=42, 
            C=1.5,  # Tăng từ 1.0 lên 1.5 để nhạy hơn
            multi_class='multinomial',
            solver='lbfgs'  # Sử dụng solver tốt hơn cho multi-class
        )
        clf.fit(X_train, y_train)
        
        # Evaluate
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        
        print(f"✅ Cheat Type Model trained:")
        print(f"   - Accuracy: {acc:.3f}")
        print(f"   - F1-Score (weighted): {f1:.3f}")
        print(f"   - Training samples: {len(X_train)}")
        print(f"   - Test samples: {len(X_test)}")
        print("\n📊 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=unique_classes))
        
        # Save model và class mapping
        return {
            "model": clf,
            "classes": unique_classes,
            "acc": float(acc),
            "f1": float(f1),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": n_features
        }
        
    except ImportError:
        print("⚠️  sklearn not installed, skipping cheat type model")
        return None
    except Exception as e:
        print(f"⚠️  Error training cheat type model: {e}")
        import traceback
        traceback.print_exc()
        return None

def train_cheat_model(X, y):
    """Train LogisticRegression cho cheat detection với features mở rộng"""
    if len(X) == 0:
        print("⚠️  No cheat data, skipping")
        return None
    
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, f1_score, classification_report
        
        print("\n🧠 Training Cheat Detection Model...")
        
        # Kiểm tra số features
        n_features = X.shape[1] if len(X.shape) > 1 else 1
        print(f"   - Input features: {n_features}")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42,
            stratify=y if len(set(y)) > 1 else None
        )
        
        # Train với regularization tốt hơn và tối ưu hóa
        clf = LogisticRegression(
            max_iter=2000,  # Tăng từ 1000 lên 2000
            class_weight='balanced', 
            random_state=42, 
            C=1.5,  # Tăng từ 1.0 lên 1.5 để nhạy hơn
            solver='lbfgs'  # Sử dụng solver tốt hơn
        )
        clf.fit(X_train, y_train)
        
        # Evaluate
        y_pred = clf.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='binary')
        
        print(f"✅ Cheat Model trained:")
        print(f"   - Accuracy: {acc:.3f}")
        print(f"   - F1-Score: {f1:.3f}")
        print(f"   - Training samples: {len(X_train)}")
        print(f"   - Test samples: {len(X_test)}")
        print("\n📊 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=['Normal', 'Cheating']))
        
        # Extract weights - hỗ trợ 4, 7, hoặc 9 features
        coef = clf.coef_[0].tolist()
        bias = float(clf.intercept_[0])
        
        weights_dict = {
            "yaw": coef[0],
            "pitch": coef[1],
            "att": coef[2],
            "susp": coef[3],
            "bias": bias
        }
        
        # Nếu có thêm features (has_phone, has_book, has_tablet, pose_suspicious, pose_deviation)
        if len(coef) > 4:
            weights_dict["has_phone"] = coef[4] if len(coef) > 4 else 0.0
        if len(coef) > 5:
            weights_dict["has_book"] = coef[5] if len(coef) > 5 else 0.0
        if len(coef) > 6:
            weights_dict["has_tablet"] = coef[6] if len(coef) > 6 else 0.0
        if len(coef) > 7:
            weights_dict["pose_suspicious"] = coef[7] if len(coef) > 7 else 0.0
        if len(coef) > 8:
            weights_dict["pose_deviation"] = coef[8] if len(coef) > 8 else 0.0
        
        return {
            "weights": weights_dict,
            "acc": float(acc),
            "f1": float(f1),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": n_features
        }
        
    except ImportError:
        print("⚠️  sklearn not installed, skipping cheat model")
        return None
    except Exception as e:
        print(f"⚠️  Error training cheat model: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_calibration(att_model, cheat_model, cheat_type_model, X_att, X_cheat):
    """Lưu calibration file với multi-class model"""
    calibration = {
        "suggest_env": compute_heuristic_thresholds(X_att, np.array([1]*len(X_att))) if len(X_att) > 0 else {},
        "logreg": att_model,
        "cheat_logreg": cheat_model,
        "n_samples": int(len(X_att)),
        "n_cheat": int(len(X_cheat)),
        "trained_at": str(Path(__file__).stat().st_mtime)
    }
    
    # Lưu model weights cho cheat_type (nếu có) - CHỈ lưu base64, không lưu model object
    if cheat_type_model and "model" in cheat_type_model:
        try:
            import pickle
            import base64
            model_bytes = pickle.dumps(cheat_type_model["model"])
            model_b64 = base64.b64encode(model_bytes).decode("utf-8")
            calibration["cheat_type_model_b64"] = model_b64
            calibration["cheat_type_classes"] = cheat_type_model["classes"]
            # Lưu metadata (không lưu model object)
            calibration["cheat_type_classifier"] = {
                "classes": cheat_type_model["classes"],
                "acc": cheat_type_model.get("acc", 0.0),
                "f1": cheat_type_model.get("f1", 0.0),
                "n_train": cheat_type_model.get("n_train", 0),
                "n_test": cheat_type_model.get("n_test", 0),
                "n_features": cheat_type_model.get("n_features", 0)
            }
            print(f"✅ Saved cheat type classifier with {len(cheat_type_model['classes'])} classes")
        except Exception as e:
            print(f"⚠️  Failed to serialize cheat type model: {e}")
            import traceback
            traceback.print_exc()
    
    OUT_PATH.write_text(json.dumps(calibration, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✅ Calibration saved to: {OUT_PATH}")
    print(f"📝 Suggested .env settings:")
    
    if att_model and "weights" not in att_model:
        for k, v in att_model.items():
            print(f"   {k}={v}")

def main():
    print("="*60)
    print("🚀 TRAINING ATTENTION & CHEAT DETECTION MODELS")
    print("   (Including Multi-class Cheat Type Classification)")
    print("="*60)
    
    # Load dataset
    dataset_result = load_dataset()
    if dataset_result[0] is None:
        print("\n❌ Failed to load dataset. Exiting.")
        return 1
    
    X_att, y_att, X_cheat, y_cheat, X_cheat_type, y_cheat_type = dataset_result
    
    # Train models
    att_model = train_attention_model(X_att, y_att) if len(X_att) > 0 else None
    cheat_model = train_cheat_model(X_cheat, y_cheat) if len(X_cheat) > 0 else None
    cheat_type_model = train_cheat_type_model(X_cheat_type, y_cheat_type) if len(X_cheat_type) > 0 else None
    
    # Save
    save_calibration(att_model, cheat_model, cheat_type_model, X_att, X_cheat)
    
    print("\n" + "="*60)
    print("✅ TRAINING COMPLETED!")
    print("="*60)
    print("\n📌 Next steps:")
    print("   1. Restart your Flask app")
    print("   2. Models will be loaded automatically from attention_calibration.json")
    print("   3. Check AI_DEBUG=1 logs to verify model is being used")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())