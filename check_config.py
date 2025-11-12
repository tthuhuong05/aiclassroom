#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra cấu hình ElevenLabs và các cải tiến
"""

import os
import sys
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent))

# Load biến môi trường từ file .env
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def check_elevenlabs_config():
    """Kiểm tra cấu hình ElevenLabs"""
    print("🔍 Kiểm tra cấu hình ElevenLabs...")
    
    # Kiểm tra API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ ELEVENLABS_API_KEY chưa được thiết lập!")
        print("📖 Vui lòng xem hướng dẫn trong VOICE_SETUP_GUIDE.md")
        return False
    
    print(f"✅ ELEVENLABS_API_KEY đã được thiết lập: {api_key[:10]}...")
    
    # Kiểm tra import
    try:
        from services.human_voice_service import is_human_voice_available, human_voice_service
        print("✅ Human voice service import thành công")
        
        if is_human_voice_available():
            print("✅ ElevenLabs service khả dụng")
            
            # Test synthesis
            try:
                test_text = "Xin chào! Đây là test giọng người thật."
                result = human_voice_service.synthesize_speech(test_text)
                if result.get("success"):
                    print("✅ Test synthesis thành công!")
                    print(f"   File: {result.get('file_path')}")
                    print(f"   Duration: {result.get('duration')}s")
                    return True
                else:
                    print(f"❌ Test synthesis thất bại: {result.get('error')}")
            except Exception as e:
                print(f"❌ Lỗi test synthesis: {e}")
        else:
            print("❌ ElevenLabs service không khả dụng")
            
    except ImportError as e:
        print(f"❌ Lỗi import human voice service: {e}")
    
    return False

def check_gemini_config():
    """Kiểm tra cấu hình Gemini"""
    print("\n🔍 Kiểm tra cấu hình Gemini...")
    
    # Kiểm tra API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY chưa được thiết lập!")
        print("📖 Cần thiết lập để có nội dung chuyên sâu")
        return False
    
    print(f"✅ GEMINI_API_KEY đã được thiết lập: {api_key[:10]}...")
    
    # Kiểm tra import
    try:
        from ai_gemini import _ensure
        if _ensure():
            print("✅ Gemini service khả dụng")
            return True
        else:
            print("❌ Gemini service không khả dụng")
    except ImportError as e:
        print(f"❌ Lỗi import Gemini service: {e}")
    
    return False

def check_video_service():
    """Kiểm tra video service"""
    print("\n🔍 Kiểm tra video service...")
    
    try:
        from services.doc_video_service import make_gemini_lecture_video, synth_voice
        print("✅ Video service import thành công")
        
        # Kiểm tra hàm synth_voice
        print("✅ Hàm synth_voice có sẵn")
        
        return True
    except ImportError as e:
        print(f"❌ Lỗi import video service: {e}")
        return False

def main():
    """Hàm main"""
    print("🚀 Kiểm tra cấu hình hệ thống")
    print("=" * 50)
    
    elevenlabs_ok = check_elevenlabs_config()
    gemini_ok = check_gemini_config()
    video_ok = check_video_service()
    
    print("\n📊 Tóm tắt cấu hình:")
    print(f"   ElevenLabs: {'✅ OK' if elevenlabs_ok else '❌ Cần cấu hình'}")
    print(f"   Gemini: {'✅ OK' if gemini_ok else '❌ Cần cấu hình'}")
    print(f"   Video Service: {'✅ OK' if video_ok else '❌ Lỗi'}")
    
    if elevenlabs_ok and gemini_ok and video_ok:
        print("\n🎉 Tất cả cấu hình đã OK!")
        print("   - Giọng người thật sẽ được sử dụng")
        print("   - Nội dung sẽ được phân tích chuyên sâu")
        print("   - Hình ảnh sẽ phù hợp với nội dung")
    else:
        print("\n⚠️ Cần cấu hình thêm:")
        if not elevenlabs_ok:
            print("   - Thiết lập ELEVENLABS_API_KEY để có giọng người thật")
        if not gemini_ok:
            print("   - Thiết lập GEMINI_API_KEY để có nội dung chuyên sâu")
        if not video_ok:
            print("   - Kiểm tra lỗi import video service")
        
        print("\n📖 Xem hướng dẫn chi tiết trong VOICE_SETUP_GUIDE.md")

if __name__ == "__main__":
    main()
