#!/usr/bin/env python3
"""
Script test phiên bản đã sửa lỗi
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
        process = subprocess.Popen([
            sys.executable, "app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(3)
        
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
        "file://" + os.path.abspath("fix_quiz_and_subtitles.html"),
        "file://" + os.path.abspath("templates/course_detail_fixed.html")
    ]
    
    print("\n🌐 Đang mở các trang test...")
    for url in test_urls:
        print(f"📖 Mở: {url}")
        webbrowser.open(url)
        time.sleep(1)

def show_test_instructions():
    """Hiển thị hướng dẫn test"""
    print("\n" + "="*60)
    print("🔧 TEST PHIÊN BẢN ĐÃ SỬA LỖI")
    print("="*60)
    print("\n📋 CÁC LỖI ĐÃ SỬA:")
    print("✅ Quiz logic đơn giản hóa và ổn định")
    print("✅ Đảm bảo video player sẵn sàng trước khi thêm quiz")
    print("✅ Xử lý DOM loading đúng cách")
    print("✅ Console log chi tiết để debug")
    print("✅ Subtitle logic riêng biệt để tránh conflict")
    print("\n🎯 CÁCH TEST:")
    print("1. Mở Developer Tools (F12)")
    print("2. Chuyển sang tab Console")
    print("3. Phát video và đợi đến giây 50")
    print("4. Kiểm tra xem quiz modal có hiển thị không")
    print("5. Kiểm tra xem phụ đề có hiển thị không")
    print("\n🔍 DEBUG STEPS:")
    print("• Tìm log: '🎯 Quiz logic đang được khởi tạo...'")
    print("• Tìm log: '✅ Video player found'")
    print("• Tìm log: '⏰ Video reached 50 seconds, showing quiz'")
    print("• Tìm log: '📝 Subtitle logic đang được khởi tạo...'")
    print("\n📁 FILES TEST:")
    print("• fix_quiz_and_subtitles.html - Test đơn giản")
    print("• templates/course_detail_fixed.html - Phiên bản đã sửa")
    print("• http://localhost:5000/course - Trang chính")
    print("\n" + "="*60)

def main():
    """Hàm chính"""
    print("🔧 TEST PHIÊN BẢN ĐÃ SỬA LỖI")
    print("="*50)
    
    if not Path("app.py").exists():
        print("❌ Không tìm thấy file app.py")
        return
    
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
            return
    
    show_test_instructions()
    
    print("\n🎉 Test đã sẵn sàng!")
    print("   Nhấn Ctrl+C để dừng test")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Test đã kết thúc.")

if __name__ == "__main__":
    main()

