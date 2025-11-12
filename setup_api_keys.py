#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script cấu hình API keys cho các cải tiến video bài giảng
"""

import os
import sys
from pathlib import Path

def setup_elevenlabs():
    """Thiết lập ElevenLabs API key"""
    print("🎤 Thiết lập ElevenLabs API Key")
    print("=" * 40)
    
    print("1. Truy cập: https://elevenlabs.io/")
    print("2. Đăng ký tài khoản miễn phí")
    print("3. Vào Profile > API Keys")
    print("4. Tạo API Key mới")
    print("5. Copy API Key")
    
    api_key = input("\nNhập ElevenLabs API Key: ").strip()
    
    if not api_key:
        print("❌ API Key không được để trống!")
        return False
    
    # Lưu vào file .env
    env_file = Path(".env")
    env_content = ""
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # Cập nhật hoặc thêm ELEVENLABS_API_KEY
    lines = env_content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('ELEVENLABS_API_KEY='):
            lines[i] = f'ELEVENLABS_API_KEY={api_key}'
            updated = True
            break
    
    if not updated:
        lines.append(f'ELEVENLABS_API_KEY={api_key}')
    
    # Ghi file
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Đã lưu ElevenLabs API Key vào {env_file}")
    
    # Test
    os.environ['ELEVENLABS_API_KEY'] = api_key
    
    try:
        from services.human_voice_service import is_human_voice_available
        if is_human_voice_available():
            print("✅ ElevenLabs đã được cấu hình thành công!")
            return True
        else:
            print("❌ ElevenLabs chưa hoạt động đúng")
            return False
    except Exception as e:
        print(f"❌ Lỗi test ElevenLabs: {e}")
        return False

def setup_gemini():
    """Thiết lập Gemini API key"""
    print("\n🤖 Thiết lập Gemini API Key")
    print("=" * 40)
    
    print("1. Truy cập: https://makersuite.google.com/app/apikey")
    print("2. Đăng nhập Google account")
    print("3. Tạo API Key mới")
    print("4. Copy API Key")
    
    api_key = input("\nNhập Gemini API Key: ").strip()
    
    if not api_key:
        print("❌ API Key không được để trống!")
        return False
    
    # Lưu vào file .env
    env_file = Path(".env")
    env_content = ""
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # Cập nhật hoặc thêm GEMINI_API_KEY
    lines = env_content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('GEMINI_API_KEY='):
            lines[i] = f'GEMINI_API_KEY={api_key}'
            updated = True
            break
    
    if not updated:
        lines.append(f'GEMINI_API_KEY={api_key}')
    
    # Ghi file
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Đã lưu Gemini API Key vào {env_file}")
    
    # Test
    os.environ['GEMINI_API_KEY'] = api_key
    
    try:
        from ai_gemini import _ensure
        if _ensure():
            print("✅ Gemini đã được cấu hình thành công!")
            return True
        else:
            print("❌ Gemini chưa hoạt động đúng")
            return False
    except Exception as e:
        print(f"❌ Lỗi test Gemini: {e}")
        return False

def setup_luna_ai():
    """Thiết lập LunaAI API key"""
    print("\n🎨 Thiết lập LunaAI API Key")
    print("=" * 40)
    
    print("1. Truy cập: https://luna.ai/")
    print("2. Đăng ký tài khoản")
    print("3. Vào Dashboard > API Keys")
    print("4. Tạo API Key mới")
    print("5. Copy API Key")
    
    api_key = input("\nNhập LunaAI API Key: ").strip()
    
    if not api_key:
        print("❌ API Key không được để trống!")
        return False
    
    # Lưu vào file .env
    env_file = Path(".env")
    env_content = ""
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
    
    # Cập nhật hoặc thêm LUNA_AI_KEY
    lines = env_content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.startswith('LUNA_AI_KEY='):
            lines[i] = f'LUNA_AI_KEY={api_key}'
            updated = True
            break
    
    if not updated:
        lines.append(f'LUNA_AI_KEY={api_key}')
    
    # Ghi file
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Đã lưu LunaAI API Key vào {env_file}")
    
    # Test
    os.environ['LUNA_AI_KEY'] = api_key
    
    try:
        from services.luna_ai_service import is_luna_ai_available
        if is_luna_ai_available():
            print("✅ LunaAI đã được cấu hình thành công!")
            return True
        else:
            print("❌ LunaAI chưa hoạt động đúng")
            return False
    except Exception as e:
        print(f"❌ Lỗi test LunaAI: {e}")
        return False

def setup_optional():
    print("\n⚙️ Thiết lập tùy chọn")
    print("=" * 40)
    
    # Bắt buộc giọng người thật
    require_human = input("Bắt buộc chỉ sử dụng giọng người thật? (y/n): ").strip().lower()
    
    if require_human == 'y':
        # Lưu vào file .env
        env_file = Path(".env")
        env_content = ""
        
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                env_content = f.read()
        
        # Cập nhật hoặc thêm REQUIRE_HUMAN_VOICE
        lines = env_content.split('\n')
        updated = False
        
        for i, line in enumerate(lines):
            if line.startswith('REQUIRE_HUMAN_VOICE='):
                lines[i] = 'REQUIRE_HUMAN_VOICE=1'
                updated = True
                break
        
        if not updated:
            lines.append('REQUIRE_HUMAN_VOICE=1')
        
        # Ghi file
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print("✅ Đã bật chế độ bắt buộc giọng người thật")
    else:
        print("ℹ️ Sẽ fallback về giọng máy nếu ElevenLabs không khả dụng")

def main():
    """Hàm main"""
    print("🚀 Cấu hình API Keys cho Video Bài Giảng AI")
    print("=" * 50)
    
    print("Các API keys cần thiết:")
    print("1. ElevenLabs - Để có giọng người thật")
    print("2. Gemini - Để có nội dung chuyên sâu")
    print("3. LunaAI - Để có hình ảnh chân thật")
    print("")
    
    elevenlabs_ok = False
    gemini_ok = False
    luna_ok = False
    
    # Thiết lập ElevenLabs
    try_elevenlabs = input("Thiết lập ElevenLabs? (y/n): ").strip().lower()
    if try_elevenlabs == 'y':
        elevenlabs_ok = setup_elevenlabs()
    
    # Thiết lập Gemini
    try_gemini = input("\nThiết lập Gemini? (y/n): ").strip().lower()
    if try_gemini == 'y':
        gemini_ok = setup_gemini()
    
    # Thiết lập LunaAI
    try_luna = input("\nThiết lập LunaAI? (y/n): ").strip().lower()
    if try_luna == 'y':
        luna_ok = setup_luna_ai()
    
    # Thiết lập tùy chọn
    setup_optional()
    
    print("\n📊 Tóm tắt cấu hình:")
    print(f"   ElevenLabs: {'✅ OK' if elevenlabs_ok else '❌ Chưa cấu hình'}")
    print(f"   Gemini: {'✅ OK' if gemini_ok else '❌ Chưa cấu hình'}")
    print(f"   LunaAI: {'✅ OK' if luna_ok else '❌ Chưa cấu hình'}")
    
    if elevenlabs_ok and gemini_ok and luna_ok:
        print("\n🎉 Cấu hình hoàn tất!")
        print("   - Giọng người thật sẽ được sử dụng")
        print("   - Nội dung sẽ được phân tích chuyên sâu")
        print("   - Hình ảnh chân thật sẽ được tạo bởi LunaAI")
        
        print("\n🚀 Bây giờ bạn có thể:")
        print("   1. Chạy: python test_luna_ai.py")
        print("   2. Chạy: python test_improvements.py")
        print("   3. Chạy: python demo_improvements.py")
        print("   4. Sử dụng tính năng tạo video trong ứng dụng")
    else:
        print("\n⚠️ Cần cấu hình thêm:")
        if not elevenlabs_ok:
            print("   - ElevenLabs để có giọng người thật")
        if not gemini_ok:
            print("   - Gemini để có nội dung chuyên sâu")
        if not luna_ok:
            print("   - LunaAI để có hình ảnh chân thật")
        
        print("\n📖 Xem hướng dẫn chi tiết trong VOICE_SETUP_GUIDE.md")

if __name__ == "__main__":
    main()
