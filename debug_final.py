#!/usr/bin/env python3
"""
Script debug cuối cùng
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

def open_debug_pages():
    """Mở các trang debug"""
    debug_urls = [
        "file://" + os.path.abspath("test_quiz_subtitles.html"),
        "http://localhost:5000/course"
    ]
    
    print("\n🌐 Đang mở các trang debug...")
    for url in debug_urls:
        print(f"📖 Mở: {url}")
        webbrowser.open(url)
        time.sleep(1)

def show_debug_instructions():
    """Hiển thị hướng dẫn debug"""
    print("\n" + "="*60)
    print("🔧 DEBUG CUỐI CÙNG - QUIZ VÀ SUBTITLES")
    print("="*60)
    print("\n📋 CÁC LỖI ĐÃ SỬA:")
    print("✅ Quiz logic đơn giản hóa")
    print("✅ Subtitle logic riêng biệt")
    print("✅ Console log chi tiết")
    print("✅ Xử lý DOM loading đúng cách")
    print("\n🎯 CÁCH DEBUG:")
    print("1. Mở Developer Tools (F12)")
    print("2. Chuyển sang tab Console")
    print("3. Refresh trang (F5)")
    print("4. Tìm các log sau:")
    print("   • 🎯 Quiz logic đang được khởi tạo...")
    print("   • 📝 Subtitle logic đang được khởi tạo...")
    print("   • ✅ Video player found")
    print("   • ⏰ Video reached 50 seconds, showing quiz")
    print("\n🔍 TEST MANUAL:")
    print("Trong Console, chạy:")
    print("• testQuiz() - Test quiz thủ công")
    print("• testSubtitles() - Test subtitles thủ công")
    print("\n📁 FILES DEBUG:")
    print("• test_quiz_subtitles.html - Test đơn giản")
    print("• templates/course_detail.html - File chính đã sửa")
    print("• http://localhost:5000/course - Trang chính")
    print("\n🛠️  TROUBLESHOOTING:")
    print("Nếu vẫn lỗi:")
    print("1. Kiểm tra Console có lỗi JavaScript không")
    print("2. Thử với video khác")
    print("3. Kiểm tra network connection")
    print("4. Thử trên browser khác")
    print("\n" + "="*60)

def main():
    """Hàm chính"""
    print("🔧 DEBUG CUỐI CÙNG - QUIZ VÀ SUBTITLES")
    print("="*50)
    
    if not Path("app.py").exists():
        print("❌ Không tìm thấy file app.py")
        return
    
    if check_flask_app():
        print("✅ Flask app đã đang chạy!")
        open_debug_pages()
    else:
        print("🔄 Flask app chưa chạy, đang khởi động...")
        process = start_flask_app()
        if process:
            open_debug_pages()
        else:
            print("❌ Không thể khởi động Flask app")
            return
    
    show_debug_instructions()
    
    print("\n🎉 Debug đã sẵn sàng!")
    print("   Nhấn Ctrl+C để dừng debug")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Debug đã kết thúc.")

if __name__ == "__main__":
    main()

