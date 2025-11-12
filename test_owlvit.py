# test_owlvit.py  — Kiểm tra OWL-ViT phát hiện vật thể "lạ" (book/phone/paper/hand/…)
import os, glob
from PIL import Image
import torch
from transformers import OwlViTProcessor, OwlViTForObjectDetection

# Lấy ảnh mới nhất bạn đã lưu từ camera (VirtualRoom đã lưu ở đây)
IMG_DIR = r"static\camera_captures"
imgs = sorted(glob.glob(os.path.join(IMG_DIR, "*.jpg")), key=os.path.getmtime)
if not imgs:
    raise FileNotFoundError(f"Không tìm thấy ảnh trong {IMG_DIR}. Hãy mở trang thi để camera chụp ít nhất 1 ảnh.")
img_path = imgs[-1]

image = Image.open(img_path).convert("RGB")

# Tải model OWL-ViT (tự động tải weights lần đầu)
processor = OwlViTProcessor.from_pretrained("google/owlvit-base-patch32")
model = OwlViTForObjectDetection.from_pretrained("google/owlvit-base-patch32")

# Danh sách vật thể “lạ” cần dò (bạn có thể thêm/bớt)
queries = [["phone", "cell phone", "book", "paper", "hand", "glasses", "mask", "headset", "person"]]

inputs = processor(text=queries, images=image, return_tensors="pt")
with torch.no_grad():
    outputs = model(**inputs)

# Hậu xử lý: trả box theo pixel ảnh gốc, lọc theo threshold
target_sizes = torch.tensor([image.size[::-1]])  # (H, W)
results = processor.post_process_object_detection(
    outputs=outputs, target_sizes=target_sizes, threshold=0.25
)[0]

print(f"Image: {img_path}")
if not len(results['scores']):
    print("=> Không phát hiện gì với ngưỡng 0.25. Thử hạ ngưỡng hoặc thêm từ khóa.")
else:
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        name = queries[0][label]
        b = [round(v, 1) for v in box.tolist()]  # [x_min, y_min, x_max, y_max]
        print(f"{name:10s}  conf={float(score):.2f}  box={b}")
