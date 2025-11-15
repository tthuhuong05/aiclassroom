# AIClassroom

## Tổng quan

AIClassroom là nền tảng hỗ trợ giảng dạy và giám sát lớp học bằng trí tuệ nhân tạo. Dự án cung cấp các công cụ tạo nội dung, sinh câu hỏi từ transcript, giám sát thi cử, phân tích hình ảnh/video và đánh giá tiến độ học tập cho học viên.

## Tính năng chính

- **Tạo nội dung AI**: Sinh bài giảng, câu hỏi trắc nghiệm và kịch bản video trực tiếp từ transcript hoặc tài liệu tải lên.
- **Giám sát thi cử**: Phát hiện gian lận qua camera, phân tích hành vi chú ý và nhận diện khuôn mặt.
- **Quản lý khóa học**: Theo dõi tiến độ học viên, điểm số và quản trị nội dung trên giao diện web hiện đại.
- **Tích hợp đa dịch vụ AI**: Hỗ trợ OpenAI, Google Generative AI, Whisper và các mô hình thị giác (ONNX, OWL-ViT, YOLO).

## Yêu cầu hệ thống

- Python 3.10 hoặc 3.11 (khuyến nghị dùng 64-bit)
- Windows 10/11, macOS, hoặc Linux
- Git, FFmpeg (phục vụ xử lý audio/video)

## Chuẩn bị môi trường

### 1. Sao chép mã nguồn

```powershell
git clone https://github.com/<your-org>/AIClassroom.git
cd AIClassroom
```

### 2. Tạo môi trường ảo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
# Trên macOS/Linux: source .venv/bin/activate
```

### 3. Cài đặt thư viện bắt buộc

Sử dụng `requirements.txt` để đảm bảo đầy đủ phụ thuộc:

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

Các thư viện quan trọng gồm: Flask, OpenAI, Google Generative AI, OpenCV, Mediapipe, ONNXRuntime, Whisper, gTTS, PyPDF2, python-docx, python-pptx.

**Lưu ý:** Với các tính năng xử lý âm thanh/video, hãy cài FFmpeg:

```powershell
winget install Gyan.FFmpeg
# hoặc tải từ https://ffmpeg.org/download.html
```

## Thiết lập biến môi trường

1. Sao chép mẫu `.env` (nếu có) hoặc tạo file `.env` ở thư mục gốc.
2. Khai báo các khóa API cần thiết:
   - `OPENAI_API_KEY`
   - `GOOGLE_API_KEY`
   - Các endpoint/dịch vụ nội bộ (nếu sử dụng).

Tham khảo thêm ở `setup_api_keys.py` và `api_keys_guide.py`.

## Cấu trúc thư mục nổi bật

- `app.py`: Điểm vào chính của ứng dụng Flask.
- `services/`: Chứa logic cho xử lý hình ảnh, giám sát thi, sinh nội dung AI.
- `controller/` và `view/`: Định nghĩa API và xử lý yêu cầu.
- `templates/` & `static/`: Giao diện web (HTML/CSS/JS) và tài nguyên tĩnh.
- `attention_dataset/`: Dữ liệu huấn luyện chú ý cho mô hình thị giác.
- `models/` & `services/models/`: Trọng số mô hình ONNX, Whisper.

## Bằng chứng gian lận

- Mỗi lần phát hiện gian lận hoặc vật thể đáng ngờ, hệ thống lưu ảnh minh chứng tại `static/camera_captures/evidence/<ten-hoc-vien>/`.
- Tên file chứa thời gian (`YYYYMMDD-HHMMSS`), khóa học, `attempt_id`, số frame và lý do giúp tra cứu nhanh.
- Bảng `proctor_frames` và `proctor_events` cũng ghi lại `snapshot_url`, thời gian, khóa học và lý do để hiển thị trong dashboard hoặc báo cáo.

## Chạy ứng dụng

Sau khi kích hoạt môi trường và cấu hình `.env`:

```powershell
python app.py
```

Mặc định ứng dụng chạy trên `http://localhost:5000`. Các script phụ trợ như `app_transcript_quiz.py`, `automatic_video_system.py` có thể chạy độc lập để thử nghiệm từng mô-đun.

## Tài liệu bổ sung

- `SETUP_AI_QUIZ.md`: Hướng dẫn cấu hình hệ thống quiz đơn giản.
- `attention_dataset/README.md`: Giải thích dữ liệu chú ý.
- `api/` & `services/`: Có docstring mô tả thêm từng endpoint và dịch vụ.

Để cập nhật README khi bổ sung tính năng mới, hãy thêm yêu cầu cài đặt và hướng dẫn chạy tương ứng nhằm giữ quy trình triển khai nhất quán cho cả nhóm.
