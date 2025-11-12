# services/fewshot_action_classifier.py
import os, csv, cv2, numpy as np

CHEAT_NAMES = {"call","phone_near","screenshot","book_near", "lookout",
               "glasses_down","glasses_left","glasses_right","self_camera"}

class FewShotActions:
    def __init__(self, root="attention_dataset", csv_path=os.getenv("ATTN_ANNOTATIONS", "attention_dataset/annotations.csv"), min_score=0.62):
        self.root = root
        self.csv = csv_path or os.path.join(root, "annotations.csv")
        self.min_score = float(min_score)
        self.hog = cv2.HOGDescriptor(_winSize=(64,64),
                                     _blockSize=(16,16),
                                     _blockStride=(8,8),
                                     _cellSize=(8,8),
                                     _nbins=9)
        self.centroids = {}  # {label: (feat_mean, count)}
        if os.path.exists(self.csv):
            self._train()

    def _embed(self, bgr):
        if bgr is None or bgr.size == 0:
            return None
        g = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (64,64), interpolation=cv2.INTER_AREA)
        f = self.hog.compute(g)  # (N,1)
        f = f.reshape(-1).astype("float32")
        n = np.linalg.norm(f) + 1e-6
        return f / n

    def _train(self):
        rows = []
        with open(self.csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                fn = r.get("filename","").strip()
                cheat = (r.get("cheat_label","").strip().lower() in ("yes","1","true"))
                pose = (r.get("pose_label") or "").strip().lower().replace(" ","_")
                label = pose if cheat and pose else None
                rows.append((fn, label, cheat))
        feats = {}
        for fn, label, cheat in rows:
            path = os.path.join(self.root, fn.replace("\\","/"))
            if not os.path.exists(path):  # cho phép ảnh để trong attention_dataset/images/...
                path2 = os.path.join(self.root, "images", fn)
                path = path2 if os.path.exists(path2) else path
            img = cv2.imread(path)
            if img is None: continue
            feat = self._embed(img)
            if feat is None: continue
            if label and label in CHEAT_NAMES:
                feats.setdefault(label, []).append(feat)
            else:
                feats.setdefault("_negative", []).append(feat)
        for k, arr in feats.items():
            if len(arr) == 0: continue
            M = np.stack(arr, 0).mean(0)
            M = M / (np.linalg.norm(M)+1e-6)
            self.centroids[k] = (M, len(arr))

    def predict(self, bgr_roi):
        """Trả: {label, score, is_cheat}"""
        if not self.centroids:
            return {"label": None, "score": 0.0, "is_cheat": False}
        q = self._embed(bgr_roi)
        if q is None: return {"label": None, "score": 0.0, "is_cheat": False}
        best_label, best = None, 0.0
        for lb, (C,_n) in self.centroids.items():
            s = float(np.dot(q, C))
            if s > best:
                best, best_label = s, lb
        is_cheat = (best_label in CHEAT_NAMES) and (best >= self.min_score)
        return {"label": best_label, "score": best, "is_cheat": is_cheat}
