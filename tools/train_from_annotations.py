import csv, json, os, math, numpy as np

# ---- đọc CSV: cột bắt buộc: filename, attention_label, pose_label, cheat_label
CSV_PATH = os.getenv("ANNOTATIONS_CSV", "attention_dataset/annotations.csv")
OUT_PATH = os.getenv("ATTN_CALIB_PATH_OUT", "attention_calibration.json")

# mapping nhãn -> số (y=1 là attentive / cheat)
ATT_POS = {"attentive","focus","focused"}
CHEAT_POS = {"yes","y","true","1","cheating"}

# nếu bạn có pose theo chữ: look_left/right/up/down/forward
POSE2YAW = {"look_left": -25, "look_right": 25, "forward": 0}
POSE2PITCH = {"look_up": -18, "look_down": 18, "forward": 0}

# ---- gom dữ liệu X/y cho 2 bài toán: (1) attentive, (2) cheat
X_att, y_att = [], []
X_ch,  y_ch  = [], []

with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
    r = csv.DictReader(f)
    for row in r:
        att_lab  = (row.get("attention_label") or "").strip().lower()
        pose_lab = (row.get("pose_label") or "").strip().lower()
        cheat_lab= (row.get("cheat_label") or "").strip().lower()

        yaw   = float(row.get("yaw",  POSE2YAW.get(pose_lab, 0)))
        pitch = float(row.get("pitch",POSE2PITCH.get(pose_lab, 0)))
        # nếu bạn không có cột attention_score thì cho 0.5 (sẽ được học bù bằng yaw/pitch)
        att_score = float(row.get("attention_score", 0.5))
        # nếu có cột suspicious_count thì dùng, không có thì 0
        susp = float(row.get("suspicious_count", 0.0))

        # (1) học xác suất chú ý
        X_att.append([yaw, pitch, att_score, 1.0])           # + bias
        y_att.append(1.0 if att_lab in ATT_POS else 0.0)

        # (2) học xác suất cheat
        X_ch.append([yaw, pitch, att_score, susp, 1.0])      # + bias
        y_ch.append(1.0 if cheat_lab in CHEAT_POS else 0.0)

X_att = np.array(X_att, dtype=float); y_att = np.array(y_att, dtype=float)
X_ch  = np.array(X_ch,  dtype=float); y_ch  = np.array(y_ch,  dtype=float)

def train_logreg(X, y, lr=0.05, steps=1200):
    w = np.zeros(X.shape[1], dtype=float)
    for _ in range(steps):
        z = X @ w
        p = 1.0/(1.0+np.exp(-z))
        g = X.T @ (p - y) / len(y)
        w -= lr * g
    return w

# huấn luyện
w_att = train_logreg(X_att, y_att)
w_ch  = train_logreg(X_ch,  y_ch)

# đề xuất ngưỡng từ dữ liệu (có thể chỉnh trong .env sau)
suggest_env = {
    "ATTN_YAW_MAX": 35, "ATTN_PITCH_MAX": 28,
    "ATTENTION_ALERT_THRESHOLD": 0.62,
    "CHEAT_WARN_PROBA": 0.60, "CHEAT_BLOCK_PROBA": 0.75
}

calib = {
    "logreg":       {"weights": {"yaw": float(w_att[0]), "pitch": float(w_att[1]),
                                 "att": float(w_att[2]), "bias": float(w_att[3])}},
    "cheat_logreg": {"weights": {"yaw": float(w_ch[0]),  "pitch": float(w_ch[1]),
                                 "att": float(w_ch[2]),  "susp": float(w_ch[3]),
                                 "bias": float(w_ch[4])}},
    "suggest_env": suggest_env
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(calib, f, ensure_ascii=False, indent=2)

print("Saved", OUT_PATH)
