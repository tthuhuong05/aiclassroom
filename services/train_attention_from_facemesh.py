# -*- coding: utf-8 -*-
"""
Train (calibrate) attention thresholds from labeled images using your existing pipeline.
- Reads attention_dataset/annotations.csv
- Uses FaceRecognitionService.detect_faces_and_objects() to get attention + head pose
- Trains a lightweight LogisticRegression on [yaw, pitch, attention_score] to classify attentive vs not
- Writes "attention_calibration.json" with suggested environment values:
    ATTN_YAW_MAX, ATTN_PITCH_MAX, ATTENTION_ALERT_THRESHOLD
Run:
    python train_attention_from_facemesh.py
Requires: opencv-python, scikit-learn (optional; if missing we'll only compute robust medians)
"""
import os, json, csv, math
from pathlib import Path

import numpy as np
import cv2

# Import your service (run this script from your project root)
from services.face_recognition_service import get_face_recognition_service

ROOT = Path(__file__).resolve().parent
DS = ROOT / "attention_dataset"
CSV_PATH = DS / "annotations.csv"
OUT_PATH = ROOT / "attention_calibration.json"

def _coerce_bytes(path: Path):
    with open(path, "rb") as f:
        return f.read()

def extract_features():
    svc = get_face_recognition_service()
    X, y = [], []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fn = row["filename"]
            lab = (row["attention_label"] or "").strip().lower()
            img_path = (DS / fn).resolve()
            if not img_path.exists(): 
                print(f"Skip missing {img_path}")
                continue
            raw = _coerce_bytes(img_path)
            r = svc.detect_faces_and_objects(raw) or {}
            pose = r.get("head_pose") or {}
            yaw = float(pose.get("yaw") or 0.0)
            pitch = float(pose.get("pitch") or 0.0)
            att = float(r.get("attention_score") or 0.0)
            X.append([yaw, pitch, att])
            y.append(1 if lab == "attentive" else 0)
            print(f"[{img_path.name}] yaw={yaw:.1f} pitch={pitch:.1f} att={att:.2f} -> {lab}")
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)

def robust_suggest(X, y):
    # Heuristics: set yaw/pitch thresholds between attentive and not-attentive clusters
    yaw = X[:,0]; pitch = X[:,1]; att = X[:,2]
    yaw_att   = np.abs(yaw[y==1]); yaw_not = np.abs(yaw[y==0])
    pitch_att = np.abs(pitch[y==1]); pitch_not = np.abs(pitch[y==0])
    att_att   = att[y==1]; att_not = att[y==0]

    def mid(a, b): 
        if len(a)==0 or len(b)==0: 
            return 30.0
        return float((np.percentile(a, 90) + np.percentile(b, 10)) / 2.0)

    yaw_max   = mid(yaw_att, yaw_not)
    pitch_max = mid(pitch_att, pitch_not)
    att_thr   = float(np.percentile(att_att if len(att_att) else att, 10)) if len(att_att) else 0.60
    return {
        "ATTN_YAW_MAX": round(yaw_max, 1),
        "ATTN_PITCH_MAX": round(pitch_max, 1),
        "ATTENTION_ALERT_THRESHOLD": round(att_thr, 2),
    }

def try_train_lr(X, y):
    try:
        import importlib
        lm = importlib.import_module("sklearn.linear_model")
        model_selection = importlib.import_module("sklearn.model_selection")
        metrics = importlib.import_module("sklearn.metrics")
        LogisticRegression = getattr(lm, "LogisticRegression")
        train_test_split = getattr(model_selection, "train_test_split")
        accuracy_score = getattr(metrics, "accuracy_score")
        f1_score = getattr(metrics, "f1_score")
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y if y.sum() not in (0,len(y)) else None)
        clf = LogisticRegression(max_iter=200)
        clf.fit(Xtr, ytr)
        proba = clf.predict_proba(Xte)[:,1]
        yhat = (proba >= 0.5).astype(int)
        acc = accuracy_score(yte, yhat)
        f1  = f1_score(yte, yhat) if len(set(yte))>1 else 1.0
        print(f"[LR] acc={acc:.3f} f1={f1:.3f} on {len(yte)} samples")
        coef = clf.coef_[0].tolist(); bias = float(clf.intercept_[0])
        return {"weights": {"yaw": coef[0], "pitch": coef[1], "att": coef[2], "bias": bias}, "acc": float(acc), "f1": float(f1)}
    except Exception as e:
        print(f"[WARN] sklearn not available or training failed: {e}")
        return None
    
    
    
# --- ADD right below existing imports/functions in train_attention_from_facemesh.py ---
def extract_features_for_cheat():
    svc = get_face_recognition_service()
    Xc, yc = [], []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fn  = row["filename"]
            lab = (row.get("cheat_label") or "").strip().lower()  # "yes"/"no"
            img_path = (DS / fn).resolve()
            if not img_path.exists():
                print(f"Skip missing {img_path}")
                continue
            raw   = _coerce_bytes(img_path)
            r     = svc.detect_faces_and_objects(raw) or {}
            pose  = r.get("head_pose") or {}
            yaw   = float(pose.get("yaw") or 0.0)
            pitch = float(pose.get("pitch") or 0.0)
            att   = float(r.get("attention_score") or 0.0)
            susp  = int(r.get("suspicious_count") or 0)
            Xc.append([yaw, pitch, att, susp])
            yc.append(1 if lab == "yes" else 0)
            print(f"[CHEAT:{img_path.name}] yaw={yaw:.1f} pitch={pitch:.1f} att={att:.2f} susp={susp} -> {lab}")
    return np.array(Xc, dtype=np.float32), np.array(yc, dtype=np.int32)

def try_train_lr_cheat(Xc, yc):
    try:
        import importlib
        lm = importlib.import_module("sklearn.linear_model")
        model_selection = importlib.import_module("sklearn.model_selection")
        metrics = importlib.import_module("sklearn.metrics")
        LogisticRegression = getattr(lm, "LogisticRegression")
        train_test_split = getattr(model_selection, "train_test_split")
        accuracy_score = getattr(metrics, "accuracy_score")
        f1_score = getattr(metrics, "f1_score")
        Xtr, Xte, ytr, yte = train_test_split(Xc, yc, test_size=0.3, random_state=42,
                                              stratify=yc if yc.sum() not in (0,len(yc)) else None)
        clf = LogisticRegression(max_iter=200)
        clf.fit(Xtr, ytr)
        proba = clf.predict_proba(Xte)[:,1]
        yhat  = (proba >= 0.5).astype(int)
        acc = accuracy_score(yte, yhat)
        f1  = f1_score(yte, yhat) if len(set(yte))>1 else 1.0
        print(f"[CHEAT LR] acc={acc:.3f} f1={f1:.3f} on {len(yte)} samples")
        coef = clf.coef_[0].tolist(); bias = float(clf.intercept_[0])
        return {"weights": {"yaw": coef[0], "pitch": coef[1], "att": coef[2], "susp": coef[3], "bias": bias},
                "acc": float(acc), "f1": float(f1)}
    except Exception as e:
        print(f"[WARN] sklearn for cheat failed: {e}")
        return None

# In main(), after existing attention training:
def main():
    X, y = extract_features()
    if X.size == 0:
        print("No features extracted. Are image paths correct?")
        return
    suggest = robust_suggest(X, y)
    lr_att  = try_train_lr(X, y)

    # NEW: cheat model
    Xc, yc  = extract_features_for_cheat()
    lr_cheat = try_train_lr_cheat(Xc, yc) if Xc.size > 0 else None

    out = {"suggest_env": suggest, "logreg": lr_att, "cheat_logreg": lr_cheat, "n_samples": int(len(y)), "n_cheat": int(len(yc))}
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote calibration to {OUT_PATH}")
    print("Add to your .env, e.g.:")
    print(f"ATTN_YAW_MAX={suggest['ATTN_YAW_MAX']}")
    print(f"ATTN_PITCH_MAX={suggest['ATTN_PITCH_MAX']}")
    print(f"ATTENTION_ALERT_THRESHOLD={suggest['ATTENTION_ALERT_THRESHOLD']}")




if __name__ == "__main__":
    main()
