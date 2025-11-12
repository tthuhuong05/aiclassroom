# quiz_config.py
"""
Cấu hình cho tính năng Video Quiz
"""

# Thời điểm dừng video (giây)
QUIZ_INTERVAL_SEC = 50

# Thông báo hiển thị cho người dùng
QUIZ_NOTIFICATION = "Hệ thống sẽ tạm dừng tại giây thứ 50 để kiểm tra nhanh nội dung đã học."

# Cấu hình modal quiz
QUIZ_MODAL_CONFIG = {
    "title": "📝 Câu hỏi kiểm tra",
    "continue_button": "Tiếp tục học ▶",
    "correct_message": "✅ Chính xác!",
    "wrong_message": "❌ Chưa đúng. Đáp án đúng là",
    "rewatch_message": "Bạn cần xem lại đoạn video từ đầu để hiểu rõ hơn."
}

# Cấu hình câu hỏi
QUESTION_CONFIG = {
    "time_limit_ms": 10000,
    "difficulty": "easy",
    "language": "vi"
}

# Cấu hình video
VIDEO_CONFIG = {
    "auto_pause": True,
    "auto_rewind_on_wrong": True,
    "rewind_to_seconds": 0
}

# Cấu hình API
API_CONFIG = {
    "endpoint_question": "/api/ai-quiz/question",
    "endpoint_grade": "/api/ai-quiz/grade",
    "timeout": 5000
}

# Cấu hình giao diện
UI_CONFIG = {
    "modal_backdrop": "rgba(0,0,0,.45)",
    "modal_border_radius": "16px",
    "button_border_radius": "12px",
    "badge_color": "#e3f2fd",
    "badge_text_color": "#1976d2"
}

def get_quiz_interval():
    """Lấy thời điểm dừng video"""
    return QUIZ_INTERVAL_SEC

def get_notification_text():
    """Lấy thông báo cho người dùng"""
    return QUIZ_NOTIFICATION

def get_modal_config():
    """Lấy cấu hình modal"""
    return QUIZ_MODAL_CONFIG

def get_question_config():
    """Lấy cấu hình câu hỏi"""
    return QUESTION_CONFIG

def get_video_config():
    """Lấy cấu hình video"""
    return VIDEO_CONFIG

def get_api_config():
    """Lấy cấu hình API"""
    return API_CONFIG

def get_ui_config():
    """Lấy cấu hình giao diện"""
    return UI_CONFIG

# Hàm để thay đổi cấu hình động
def update_quiz_interval(seconds):
    """Thay đổi thời điểm dừng video"""
    global QUIZ_INTERVAL_SEC
    QUIZ_INTERVAL_SEC = seconds
    return QUIZ_INTERVAL_SEC

def update_notification_text(text):
    """Thay đổi thông báo"""
    global QUIZ_NOTIFICATION
    QUIZ_NOTIFICATION = text
    return QUIZ_NOTIFICATION

