# test_detect.py (robust)
import os, sys, cv2, json
from services.face_recognition_service import get_face_recognition_service

# ---- chọn ảnh cần test ----
TARGET = r"C:\Users\FPTSHOP\Pictures\Screenshots\test.png"  # thư mục hoặc file cụ thể

# --- resolve ảnh ---
def resolve_image(target):
    exts = (".png", ".jpg", ".jpeg", ".bmp", ".webp")
    if os.path.isdir(target):
        cands = [os.path.join(target, f) for f in os.listdir(target)
                 if os.path.splitext(f)[1].lower() in exts]
        if not cands:
            print(f"[ERROR] Không thấy ảnh trong thư mục: {target}"); sys.exit(1)
        return max(cands, key=os.path.getmtime)
    else:
        root, ext = os.path.splitext(target)
        if not ext:
            for e in exts:
                p = root + e
                if os.path.exists(p): return p
        if os.path.exists(target): return target
        print(f"[ERROR] Không tìm thấy file ảnh. Đã thử: {[root+e for e in exts] if not ext else [target]}")
        sys.exit(1)

IMG_PATH = resolve_image(TARGET)
print(f"[INFO] Dùng ảnh: {IMG_PATH}")
img = cv2.imread(IMG_PATH)
if img is None:
    print(f"[ERROR] cv2.imread() thất bại: {IMG_PATH}"); sys.exit(1)

FR = get_face_recognition_service()
res = FR.detect_faces_and_objects(img)

# ---- in JSON ngắn gọn ----
print(json.dumps({
    "status": FR.debug_status(),
    "faces": len(res.get("faces", [])) if isinstance(res, dict) else 0,
    "objects": len(res.get("objects", [])) if isinstance(res, dict) else 0,
    "suspicious": res.get("suspicious_objects", [])
}, ensure_ascii=False, indent=2))

# ---- helper: chuẩn hoá các kiểu box khác nhau về (x0,y0,x1,y1) ----
def to_xyxy_face(f):
    # có thể là dict hoặc tuple/list
    if isinstance(f, dict):
        if "box" in f:  # tiêu chuẩn mới
            x0,y0,x1,y1 = f["box"]; return int(x0),int(y0),int(x1),int(y1)
        if "position" in f:  # (x,y,w,h)
            x,y,w,h = f["position"]; return int(x),int(y),int(x+w),int(y+h)
        # các biến thể khác
        keys = f.keys()
        if all(k in keys for k in ("x0","y0","x1","y1")):
            return int(f["x0"]),int(f["y0"]),int(f["x1"]),int(f["y1"])
        if all(k in keys for k in ("x","y","w","h")):
            return int(f["x"]),int(f["y"]),int(f["x"]+f["w"]),int(f["y"]+f["h"])
    if isinstance(f, (list, tuple)) and len(f) == 4:
        a,b,c,d = f
        # đoán định dạng: nếu c>a và d>b → (x0,y0,x1,y1) ; ngược lại → (x,y,w,h)
        if c > a and d > b:
            return int(a),int(b),int(c),int(d)
        return int(a),int(b),int(a+c),int(b+d)
    return None

def to_xyxy_obj(o):
    if isinstance(o, dict):
        if "position" in o:
            x,y,w,h = o["position"]; return int(x),int(y),int(x+w),int(y+h)
        if "box" in o:
            x0,y0,x1,y1 = o["box"]; return int(x0),int(y0),int(x1),int(y1)
    return None

# ---- vẽ và lưu ----
vis = img.copy()
for f in res.get("faces", []):
    xyxy = to_xyxy_face(f)
    if xyxy:
        x0,y0,x1,y1 = xyxy
        cv2.rectangle(vis, (x0,y0), (x1,y1), (0,255,0), 2)

for o in res.get("objects", []):
    xyxy = to_xyxy_obj(o)
    if xyxy:
        x0,y0,x1,y1 = xyxy
        cv2.rectangle(vis, (x0,y0), (x1,y1), (0,0,255), 2)
        label = o.get("type","obj")
        score = o.get("score", 0.0)
        cv2.putText(vis, f"{label}:{score:.2f}", (x0, max(0,y0-5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,0,255), 1, cv2.LINE_AA)

out_path = "out_detect.jpg"
cv2.imwrite(out_path, vis)
print(f"[OK] Đã lưu ảnh có khung: {os.path.abspath(out_path)}")
