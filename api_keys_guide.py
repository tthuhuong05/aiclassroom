#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Keys Setup Guide
Hướng dẫn thiết lập API Keys cho hệ thống tạo video
"""

import os
import sys
from pathlib import Path

def print_header():
    """In header"""
    print("=" * 60)
    print("HUONG DAN THIET LAP API KEYS CHO HE THONG TAO VIDEO")
    print("=" * 60)

def print_api_guide():
    """In huong dan lay API keys"""
    print("\nDANH SACH API KEYS CAN THIET:")
    print("-" * 40)
    
    apis = [
        {
            "name": "PEXELS API",
            "description": "Tìm hình ảnh chất lượng cao (QUAN TRỌNG NHẤT)",
            "website": "https://www.pexels.com/api/",
            "steps": [
                "1. Truy cập https://www.pexels.com/api/",
                "2. Click 'Request API Key'",
                "3. Đăng ký tài khoản miễn phí",
                "4. Copy API key",
                "5. Thêm vào file .env: PEXELS_API_KEY=your_key_here"
            ],
            "required": True
        },
        {
            "name": "ELEVENLABS API", 
            "description": "Tạo giọng người thật tự nhiên",
            "website": "https://elevenlabs.io/",
            "steps": [
                "1. Truy cập https://elevenlabs.io/",
                "2. Đăng ký tài khoản",
                "3. Vào Profile → API Key",
                "4. Copy API key",
                "5. Thêm vào file .env: ELEVENLABS_API_KEY=your_key_here"
            ],
            "required": True
        },
        {
            "name": "GOOGLE GEMINI API",
            "description": "Phân tích nội dung và tạo cấu trúc bài giảng",
            "website": "https://aistudio.google.com/app/apikey",
            "steps": [
                "1. Truy cập https://aistudio.google.com/app/apikey",
                "2. Đăng nhập Google account",
                "3. Click 'Create API Key'",
                "4. Copy API key",
                "5. Thêm vào file .env: GEMINI_API_KEY=your_key_here"
            ],
            "required": True
        },
        {
            "name": "UNSPLASH API",
            "description": "Backup cho tìm hình ảnh",
            "website": "https://unsplash.com/developers",
            "steps": [
                "1. Truy cập https://unsplash.com/developers",
                "2. Click 'Register as a developer'",
                "3. Tạo ứng dụng mới",
                "4. Copy Access Key",
                "5. Thêm vào file .env: UNSPLASH_ACCESS_KEY=your_key_here"
            ],
            "required": False
        },
        {
            "name": "OPENAI DALL-E API",
            "description": "Tạo hình ảnh bằng AI (tùy chọn)",
            "website": "https://platform.openai.com/api-keys",
            "steps": [
                "1. Truy cập https://platform.openai.com/api-keys",
                "2. Đăng nhập OpenAI account",
                "3. Click 'Create new secret key'",
                "4. Copy API key",
                "5. Thêm vào file .env: OPENAI_API_KEY=your_key_here"
            ],
            "required": False
        },
        {
            "name": "STABILITY AI API",
            "description": "Tạo hình ảnh bằng AI (tùy chọn)",
            "website": "https://platform.stability.ai/",
            "steps": [
                "1. Truy cập https://platform.stability.ai/",
                "2. Đăng ký tài khoản",
                "3. Vào API Keys section",
                "4. Tạo API key mới",
                "5. Thêm vào file .env: STABILITY_API_KEY=your_key_here"
            ],
            "required": False
        }
    ]
    
    for i, api in enumerate(apis, 1):
        status = "🔴 BẮT BUỘC" if api["required"] else "🟡 TÙY CHỌN"
        print(f"\n{i}. {api['name']} - {status}")
        print(f"   📝 {api['description']}")
        print(f"   🌐 Website: {api['website']}")
        print("   📋 Các bước:")
        for step in api["steps"]:
            print(f"      {step}")

def check_current_keys():
    """Kiểm tra API keys hiện tại"""
    print("\n🔍 KIỂM TRA API KEYS HIỆN TẠI:")
    print("-" * 40)
    
    # Load .env file if exists
    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            keys = {
                "PEXELS_API_KEY": "Pexels (Hình ảnh)",
                "ELEVENLABS_API_KEY": "ElevenLabs (Giọng nói)",
                "GEMINI_API_KEY": "Gemini (Phân tích nội dung)",
                "UNSPLASH_ACCESS_KEY": "Unsplash (Hình ảnh backup)",
                "OPENAI_API_KEY": "OpenAI DALL-E (Tạo hình ảnh)",
                "STABILITY_API_KEY": "Stability AI (Tạo hình ảnh)"
            }
            
            for key, description in keys.items():
                if key in content:
                    # Extract the key value
                    lines = content.split('\n')
                    for line in lines:
                        if line.startswith(f"{key}="):
                            value = line.split('=', 1)[1].strip()
                            if value:
                                masked_value = value[:10] + "..." if len(value) > 10 else value
                                print(f"   ✅ {description}: {masked_value}")
                            else:
                                print(f"   ❌ {description}: Chưa có giá trị")
                            break
                    else:
                        print(f"   ❌ {description}: Không tìm thấy")
                else:
                    print(f"   ❌ {description}: Chưa có")
        except Exception as e:
            print(f"   ❌ Lỗi đọc file .env: {e}")
    else:
        print("   ❌ File .env chưa tồn tại")

def create_env_template():
    """Tạo template file .env"""
    print("\n📝 TẠO TEMPLATE FILE .ENV:")
    print("-" * 40)
    
    template = """# API Keys for Video Generation System
# Copy this file to .env and fill in your API keys

# REQUIRED APIs
PEXELS_API_KEY=your_pexels_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# OPTIONAL APIs (for better image generation)
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here
OPENAI_API_KEY=your_openai_api_key_here
STABILITY_API_KEY=your_stability_api_key_here

# Settings
REQUIRE_HUMAN_VOICE=1
"""
    
    try:
        with open(".env.template", "w", encoding="utf-8") as f:
            f.write(template)
        print("   ✅ Đã tạo file .env.template")
        print("   📋 Hướng dẫn:")
        print("      1. Copy .env.template thành .env")
        print("      2. Điền API keys vào file .env")
        print("      3. Chạy lại hệ thống")
    except Exception as e:
        print(f"   ❌ Lỗi tạo template: {e}")

def print_priority_guide():
    """In hướng dẫn ưu tiên"""
    print("\n🎯 HƯỚNG DẪN ƯU TIÊN:")
    print("-" * 40)
    print("1. 🔴 BẮT BUỘC (Cần có để hệ thống hoạt động):")
    print("   - PEXELS_API_KEY: Tìm hình ảnh phù hợp với nội dung")
    print("   - ELEVENLABS_API_KEY: Tạo giọng người thật")
    print("   - GEMINI_API_KEY: Phân tích nội dung và tạo cấu trúc")
    print()
    print("2. 🟡 TÙY CHỌN (Cải thiện chất lượng):")
    print("   - UNSPLASH_ACCESS_KEY: Backup cho hình ảnh")
    print("   - OPENAI_API_KEY: Tạo hình ảnh bằng AI")
    print("   - STABILITY_API_KEY: Tạo hình ảnh bằng AI")
    print()
    print("3. 💡 LƯU Ý:")
    print("   - Bắt đầu với 3 API bắt buộc")
    print("   - Thêm API tùy chọn để cải thiện chất lượng")
    print("   - Pexels miễn phí, ElevenLabs có free tier")
    print("   - Gemini có free tier với giới hạn")

def main():
    """Main function"""
    print_header()
    print_api_guide()
    check_current_keys()
    create_env_template()
    print_priority_guide()
    
    print("\n" + "=" * 60)
    print("🎉 HOÀN THÀNH!")
    print("=" * 60)
    print("Sau khi có đủ API keys:")
    print("1. Chạy: python setup_api_keys.py")
    print("2. Test: python test_image_matching.py")
    print("3. Tạo video từ ứng dụng web")

if __name__ == "__main__":
    main()
