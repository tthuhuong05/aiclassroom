# 🤖 SETUP AI QUIZ VỚI GEMINI

## Vấn đề đã sửa
- ✅ Video dừng tại giây 50
- ✅ Câu hỏi hiển thị từ phụ đề
- ✅ AI Gemini tạo câu hỏi thông minh
- ✅ Fallback nếu AI không hoạt động

## Cài đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Gemini API Key
```bash
# Tạo file .env
echo "GEMINI_API_KEY=your_api_key_here" > .env

# Hoặc set environment variable
export GEMINI_API_KEY=your_api_key_here
```

### 3. Lấy Gemini API Key
1. Truy cập: https://makersuite.google.com/app/apikey
2. Tạo API key mới
3. Copy API key vào file .env

## Cách hoạt động

### 1. Frontend (templates/course_detail.html)
- Video dừng tại giây 50
- Trích xuất phụ đề từ 0-50 giây
- Gọi API `/api/ai-quiz/generate-from-subtitles`
- Hiển thị câu hỏi từ AI Gemini

### 2. Backend (app.py)
- API endpoint: `POST /api/ai-quiz/generate-from-subtitles`
- Sử dụng AI Gemini để tạo câu hỏi
- Fallback nếu AI không hoạt động

### 3. AI Gemini Integration
- Phân tích nội dung phụ đề
- Tạo câu hỏi trắc nghiệm phù hợp
- Trả về JSON format chuẩn

## Test

### 1. Chạy Flask app
```bash
python app.py
```

### 2. Test API
```bash
python test_ai_quiz.py
```

### 3. Test trên browser
- Mở: http://localhost:5000/course
- Phát video đến giây 50
- Kiểm tra câu hỏi có hiển thị không

## Debug

### 1. Console Logs
Tìm các log sau trong Developer Tools:
```
🎯 Quiz logic đang được khởi tạo...
📝 Subtitle logic đang được khởi tạo...
🤖 Fetching question from subtitles using AI Gemini...
📝 Subtitle text (0-50s): [nội dung phụ đề]
✅ AI Gemini generated question: [câu hỏi]
```

### 2. API Test
```bash
curl -X POST http://localhost:5000/api/ai-quiz/generate-from-subtitles \
  -H "Content-Type: application/json" \
  -d '{
    "subtitle_text": "It is like the loudspeaker of JavaScript...",
    "time_range": "0-50 seconds",
    "language": "vi"
  }'
```

### 3. Troubleshooting
- **API Key không hoạt động**: Kiểm tra GEMINI_API_KEY
- **Không có phụ đề**: Video cần có track subtitles
- **Câu hỏi không hiển thị**: Kiểm tra Console logs
- **AI không hoạt động**: Sử dụng fallback question

## Features

### ✅ Đã hoàn thành
- Video pause tại giây 50
- Trích xuất phụ đề từ video
- AI Gemini tạo câu hỏi thông minh
- Fallback question nếu AI lỗi
- Console logging chi tiết

### 🔄 Có thể cải thiện
- Thêm nhiều loại câu hỏi
- Cải thiện AI prompt
- Thêm error handling
- Cache câu hỏi đã tạo

## Kết quả mong đợi

Khi video đến giây 50:
1. ✅ Video tự động dừng
2. ✅ Quiz modal hiển thị
3. ✅ Câu hỏi từ AI Gemini xuất hiện
4. ✅ 4 lựa chọn A, B, C, D
5. ✅ Giải thích khi trả lời

## Liên hệ hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra Console logs
2. Test API endpoint
3. Kiểm tra GEMINI_API_KEY
4. Thử với video có phụ đề

