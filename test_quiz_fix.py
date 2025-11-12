#!/usr/bin/env python3
"""
Script test để kiểm tra tính năng quiz video đã được sửa
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

def open_test_pages():
    """Mở các trang test"""
    test_urls = [
        "http://localhost:5000/course",
        "http://localhost:5000/test-quiz-video"
    ]
    
    print("\n🌐 Đang mở các trang test...")
    for url in test_urls:
        print(f"📖 Mở: {url}")
        webbrowser.open(url)
        time.sleep(1)

def show_test_instructions():
    """Hiển thị hướng dẫn test"""
    print("\n" + "="*60)
    print("🔧 TEST TÍNH NĂNG QUIZ VIDEO - ĐÃ SỬA LỖI")
    print("="*60)
    print("\n📋 CÁCH TEST:")
    print("1. Truy cập: http://localhost:5000/course")
    print("2. Chọn một khóa học có video")
    print("3. Phát video và đợi đến giây thứ 50")
    print("4. Kiểm tra xem quiz modal có hiển thị không")
    print("\n🎯 CÁC TRANG TEST:")
    print("• /course - Danh sách khóa học (trang chính)")
    print("• /test-quiz-video - Demo với video mẫu")
    print("• /lesson/<course_id> - Xem bài học với quiz")
    print("\n✅ TÍNH NĂNG ĐÃ SỬA:")
    print("• Thêm quiz logic vào course_detail.html")
    print("• Video sẽ dừng tại giây 50")
    print("• Hiển thị câu hỏi trắc nghiệm")
    print("• Nếu trả lời sai → tua lại từ đầu")
    print("• Nếu trả lời đúng → tiếp tục phát")
    print("\n🛠️  DEBUG:")
    print("• Mở Developer Tools (F12)")
    print("• Kiểm tra Console tab có lỗi JavaScript không")
    print("• Kiểm tra Network tab có request API không")
    print("• Kiểm tra video currentTime có >= 50 không")
    print("\n" + "="*60)

def main():
    """Hàm chính"""
    print("🔧 TEST TÍNH NĂNG QUIZ VIDEO - ĐÃ SỬA LỖI")
    print("="*50)
    
    # Kiểm tra xem có file app.py không
    if not Path("app.py").exists():
        print("❌ Không tìm thấy file app.py")
        print("   Vui lòng chạy script này trong thư mục gốc của project")
        return
    
    # Kiểm tra xem Flask app có đang chạy không
    if check_flask_app():
        print("✅ Flask app đã đang chạy!")
        open_test_pages()
    else:
        print("🔄 Flask app chưa chạy, đang khởi động...")
        process = start_flask_app()
        if process:
            open_test_pages()
        else:
            print("❌ Không thể khởi động Flask app")
            print("   Vui lòng chạy thủ công: python app.py")
            return
    
    show_test_instructions()
    
    print("\n🎉 Test đã sẵn sàng!")
    print("   Nhấn Ctrl+C để dừng test")
    
    try:
        # Giữ script chạy
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Test đã kết thúc.")

if __name__ == "__main__":
    main()

