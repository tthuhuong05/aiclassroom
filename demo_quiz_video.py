#!/usr/bin/env python3
"""
Demo script để test tính năng Video Quiz - Dừng tại giây 50
"""

import webbrowser
import time
import subprocess
import sys
import os
from pathlib import Path

def check_flask_app():
    """Kiểm tra xem Flask app có đang chạy không"""
    try:
        import requests
        response = requests.get("http://localhost:5000", timeout=5)
        return response.status_code == 200
    except:
        return False

def start_flask_app():
    """Khởi động Flask app"""
    print("🚀 Đang khởi động Flask app...")
    try:
        # Chạy Flask app trong background
        process = subprocess.Popen([
            sys.executable, "app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Đợi một chút để app khởi động
        time.sleep(3)
        
        # Kiểm tra xem app có chạy không
        if check_flask_app():
            print("✅ Flask app đã khởi động thành công!")
            return process
        else:
            print("❌ Không thể khởi động Flask app")
            return None
    except Exception as e:
        print(f"❌ Lỗi khi khởi động Flask app: {e}")
        return None

def open_demo_pages():
    """Mở các trang demo"""
    demo_urls = [
        "http://localhost:5000/test-quiz-video",
        "http://localhost:5000/course"
    ]
    
    print("\n🌐 Đang mở các trang demo...")
    for url in demo_urls:
        print(f"📖 Mở: {url}")
        webbrowser.open(url)
        time.sleep(1)

def show_instructions():
    """Hiển thị hướng dẫn sử dụng"""
    print("\n" + "="*60)
    print("🎥 DEMO TÍNH NĂNG VIDEO QUIZ - DỪNG TẠI GIÂY 50")
    print("="*60)
    print("\n📋 HƯỚNG DẪN SỬ DỤNG:")
    print("1. Video sẽ tự động dừng tại giây thứ 50")
    print("2. Hệ thống hiển thị câu hỏi trắc nghiệm")
    print("3. Nếu trả lời SAI → Video tua lại từ đầu")
    print("4. Nếu trả lời ĐÚNG → Video tiếp tục phát")
    print("\n🎯 CÁC TRANG DEMO:")
    print("• /test-quiz-video - Demo với video mẫu")
    print("• /course - Danh sách khóa học")
    print("• /lesson/<course_id> - Xem bài học với quiz")
    print("\n⚙️  CẤU HÌNH:")
    print("• Thay đổi thời điểm dừng: sửa QUIZ_INTERVAL_SEC trong app.py")
    print("• Thay đổi câu hỏi: sửa video_script_quiz_service.py")
    print("\n🛠️  TROUBLESHOOTING:")
    print("• Nếu video không dừng: kiểm tra console browser")
    print("• Nếu câu hỏi không hiển thị: kiểm tra API endpoint")
    print("• Nếu video không tua lại: kiểm tra JavaScript logic")
    print("\n" + "="*60)

def main():
    """Hàm chính"""
    print("🎬 DEMO TÍNH NĂNG VIDEO QUIZ")
    print("="*40)
    
    # Kiểm tra xem có file app.py không
    if not Path("app.py").exists():
        print("❌ Không tìm thấy file app.py")
        print("   Vui lòng chạy script này trong thư mục gốc của project")
        return
    
    # Kiểm tra xem Flask app có đang chạy không
    if check_flask_app():
        print("✅ Flask app đã đang chạy!")
        open_demo_pages()
    else:
        print("🔄 Flask app chưa chạy, đang khởi động...")
        process = start_flask_app()
        if process:
            open_demo_pages()
        else:
            print("❌ Không thể khởi động Flask app")
            print("   Vui lòng chạy thủ công: python app.py")
            return
    
    show_instructions()
    
    print("\n🎉 Demo đã sẵn sàng!")
    print("   Nhấn Ctrl+C để dừng demo")
    
    try:
        # Giữ script chạy
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Tạm biệt! Demo đã kết thúc.")

if __name__ == "__main__":
    main()
