#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để kiểm tra tạo video AI
"""

import os
import sys
from pathlib import Path

# Load environment variables
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def test_video_creation():
    """Test tạo video từ file PDF mẫu"""
    print("=" * 60)
    print("TEST TAO VIDEO AI")
    print("=" * 60)
    
    # Check if .env exists
    env_file = Path(".env")
    if not env_file.exists():
        print("[ERROR] File .env khong ton tai!")
        print("   Vui long chay: python setup_api_keys.py")
        return False
    
    print("[OK] File .env ton tai")
    
    # Check API keys
    gemini_key = os.getenv('GEMINI_API_KEY')
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    
    if gemini_key:
        print(f"[OK] GEMINI_API_KEY: {gemini_key[:10]}...")
    else:
        print("[ERROR] GEMINI_API_KEY chua duoc thiet lap")
    
    if elevenlabs_key:
        print(f"[OK] ELEVENLABS_API_KEY: {elevenlabs_key[:10]}...")
    else:
        print("[WARNING] ELEVENLABS_API_KEY chua duoc thiet lap (khong bat buoc)")
    
    # Check if doc_video_service can be imported
    try:
        from services.doc_video_service import make_video_from_file
        print("[OK] Video service import thanh cong")
    except ImportError as e:
        print(f"[ERROR] Khong the import video service: {e}")
        return False
    
    # Check if sample PDF exists
    test_files = [
        "machine learning.pdf",
        "test.pdf",
        "sample.pdf"
    ]
    
    test_file = None
    for f in test_files:
        if os.path.exists(f):
            test_file = f
            break
    
    if not test_file:
        print("\n⚠️  Không tìm thấy file PDF test")
        print("   Tạo file test đơn giản...")
        
        # Create a simple test PDF
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Test Document", ln=1, align="C")
            pdf.ln(10)
            pdf.cell(200, 10, txt="This is a test document for AI video creation.", ln=1)
            pdf.cell(200, 10, txt="It contains multiple lines of content to test the system.", ln=1)
            pdf.cell(200, 10, txt="Machine learning is an important topic.", ln=1)
            pdf.cell(200, 10, txt="It involves training models on data.", ln=1)
            
            test_file = "test_video.pdf"
            pdf.output(test_file)
            print(f"✅ Đã tạo file test: {test_file}")
        except Exception as e:
            print(f"❌ Không thể tạo file test: {e}")
            return False
    
    # Test video creation
    print(f"\n📹 Tạo video từ file: {test_file}")
    print("   (Quá trình này có thể mất 1-3 phút...)")
    
    try:
        out_dir = os.path.join("static", "uploads", "test_output")
        os.makedirs(out_dir, exist_ok=True)
        
        result = make_video_from_file(test_file, out_dir, title="Test Video")
        
        if result and "video_path" in result:
            video_path = result["video_path"]
            if os.path.exists(video_path):
                size_mb = os.path.getsize(video_path) / (1024 * 1024)
                print(f"\n✅ Video tạo thành công!")
                print(f"   File: {video_path}")
                print(f"   Size: {size_mb:.2f} MB")
                print(f"   Caption: {result.get('caption_path', 'N/A')}")
                return True
            else:
                print(f"\n❌ Video file không tồn tại: {video_path}")
                return False
        else:
            print(f"\n❌ Không có video_path trong kết quả")
            return False
            
    except Exception as e:
        print(f"\n❌ Lỗi khi tạo video: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_video_creation()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TEST THÀNH CÔNG - Hệ thống hoạt động bình thường!")
        print("\n💡 Hướng dẫn:")
        print("   1. Truy cập: http://localhost:5000/create-course")
        print("   2. Chọn file PDF/Word/PowerPoint")
        print("   3. Nhấn 'Tạo video AI từ tài liệu'")
        print("   4. Đợi 1-3 phút để hoàn thành")
    else:
        print("❌ TEST THẤT BẠI - Vui lòng kiểm tra lỗi ở trên")
    print("=" * 60)

