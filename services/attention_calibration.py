# -*- coding: utf-8 -*-
import json, os, math

def _sigmoid(x): return 1.0/(1.0+math.exp(-x))

def load_calibration():
    path = os.getenv("ATTN_CALIB_PATH", "attention_calibration.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

class AttentionCalibrator:
    def __init__(self):
        data = load_calibration()
        env = (data.get("suggest_env") or {})
        self.yaw_max   = float(os.getenv("ATTN_YAW_MAX",   env.get("ATTN_YAW_MAX", 35)))
        self.pitch_max = float(os.getenv("ATTN_PITCH_MAX", env.get("ATTN_PITCH_MAX", 28)))
        self.att_thr   = float(os.getenv("ATTENTION_ALERT_THRESHOLD", env.get("ATTENTION_ALERT_THRESHOLD", 0.62)))
        self.lr = (data.get("logreg") or {}).get("weights")  # {"yaw":..., "pitch":..., "att":..., "bias":...}
        self.lr_cheat  = (data.get("cheat_logreg") or {}).get("weights")
        self.warn_p    = float(os.getenv("CHEAT_WARN_PROBA", "0.60"))
        self.block_p   = float(os.getenv("CHEAT_BLOCK_PROBA","0.75"))
        
    def attentive_proba(self, yaw, pitch, att):
        # 1) nếu có logistic regression → dùng xác suất
        if self.lr:
            z = (self.lr["bias"]
                 + self.lr["yaw"]*yaw
                 + self.lr["pitch"]*pitch
                 + self.lr["att"]*att)
            return float(_sigmoid(z))
        # 2) fallback heuristic (chuẩn hoá theo ngưỡng)
        ny = max(0.0, 1.0 - abs(yaw)/max(1.0, self.yaw_max))
        np = max(0.0, 1.0 - abs(pitch)/max(1.0, self.pitch_max))
        return float(0.4*att + 0.3*ny + 0.3*np)

    def pose_label_and_conf(self, yaw, pitch):
        # forward / left / right / up / down từ yaw/pitch + độ tự tin
        ay, ap = abs(yaw), abs(pitch)
        # khoảng “forward”
        fwd = (ay < self.yaw_max*0.45 and ap < self.pitch_max*0.45)
        if fwd:
            d = max(ay/self.yaw_max, ap/self.pitch_max)
            return "forward", float(1.0 - d)

        # xác định hướng lệch mạnh hơn
        if ay/ap >= 1.2:  # nghiêng ngang
            if yaw > 0:  # nghiêng phải (người nhìn sang phải)
                conf = min(1.0, ay/self.yaw_max)
                return "look_right", float(conf)
            else:
                conf = min(1.0, ay/self.yaw_max)
                return "look_left", float(conf)
        else:  # nghiêng dọc
            if pitch > 0:
                conf = min(1.0, ap/self.pitch_max)
                return "look_down", float(conf)
            else:
                conf = min(1.0, ap/self.pitch_max)
                return "look_up", float(conf)
    
    
    def cheat_proba(self, yaw, pitch, att, susp_count):
        if self.lr_cheat:
            z = (self.lr_cheat["bias"]
                 + self.lr_cheat["yaw"]*yaw
                 + self.lr_cheat["pitch"]*pitch
                 + self.lr_cheat["att"]*att
                 + self.lr_cheat["susp"]*susp_count)
            return float(_sigmoid(z))
        # fallback heuristic nếu chưa train:
        # nhiều đồ gần mặt + attention thấp + lệch pose => tăng xác suất
        import math
        base = 0.5*min(1.0, susp_count/2.0) + 0.3*(1.0-att) + 0.2*max(abs(yaw)/max(1,self.yaw_max), abs(pitch)/max(1,self.pitch_max))
        return float(max(0.0, min(1.0, base)))
