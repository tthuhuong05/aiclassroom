# test_owlvit_v2.py
import os, glob, torch
from PIL import Image, ImageDraw, ImageFont
from transformers import OwlViTProcessor, OwlViTForObjectDetection

# ❶ Ảnh mới nhất bạn đã lưu từ camera
IMG_DIR = r"static\camera_captures"
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*.jpg")), key=os.path.getmtime)
if not imgs:
    raise FileNotFoundError(f"Không thấy ảnh trong {IMG_DIR}. Mở trang thi để camera chụp 1 ảnh trước.")
img_path = imgs[-1]

# ❷ Hạ ngưỡng (0.15 ~ 0.20 thường nhạy hơn)
THRESH = float(os.getenv("OVD_THRESHOLD", "0.15"))

# ❸ Danh sách từ khóa tiếng Anh + nhiều biến thể
QUERIES = [
    # near-face / hand / paper / phone …
    "hand", "fingers", "hand covering face",
    "phone", "cell phone", "smartphone", "phone screen",
    "book", "notebook", "paper", "sheet of paper", "cheat sheet",
    "pen", "pencil", "calculator",
    "glasses", "mask", "headset", "earbuds",
    "laptop", "tablet", "monitor",
    "person", "face"
]

image = Image.open(img_path).convert("RGB")

# ❹ Dùng GPU nếu có
device = "cuda" if torch.cuda.is_available() else "cpu"
processor = OwlViTProcessor.from_pretrained("google/owlvit-base-patch32")
model = OwlViTForObjectDetection.from_pretrained("google/owlvit-base-patch32").to(device)

inputs = processor(text=[QUERIES], images=image, return_tensors="pt").to(device)
with torch.no_grad():
    outputs = model(**inputs)

# ❺ Hậu xử lý + vẽ box
target_sizes = torch.tensor([image.size[::-1]], device=device)
results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=THRESH)[0]

print(f"Image: {img_path}")
if not len(results['scores']):
    print(f"=> Không phát hiện gì với ngưỡng {THRESH}. Thử hạ ngưỡng hoặc thêm biến thể từ khóa.")
else:
    draw = ImageDraw.Draw(image)
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        name = QUERIES[int(label)]
        x0, y0, x1, y1 = [float(v) for v in box.tolist()]
        draw.rectangle([x0, y0, x1, y1], outline="red", width=3)
        draw.text((x0, max(0, y0-12)), f"{name} {float(score):.2f}", fill="red")
        print(f"{name:15s}  conf={float(score):.2f}  box={[round(v,1) for v in [x0,y0,x1,y1]]}")

    os.makedirs("outputs", exist_ok=True)
    out_path = os.path.join("outputs", "annotated_owlvit.jpg")
    image.save(out_path)
    print(f"=> Đã lưu ảnh gắn nhãn: {out_path}")
