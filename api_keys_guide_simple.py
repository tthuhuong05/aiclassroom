#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Keys Setup Guide
Huong dan thiet lap API Keys cho he thong tao video
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
            "description": "Tim hinh anh chat luong cao (QUAN TRONG NHAT)",
            "website": "https://www.pexels.com/api/",
            "steps": [
                "1. Truy cap https://www.pexels.com/api/",
                "2. Click 'Request API Key'",
                "3. Dang ky tai khoan mien phi",
                "4. Copy API key",
                "5. Them vao file .env: PEXELS_API_KEY=your_key_here"
            ],
            "required": True
        },
        {
            "name": "ELEVENLABS API", 
            "description": "Tao giong nguoi that tu nhien",
            "website": "https://elevenlabs.io/",
            "steps": [
                "1. Truy cap https://elevenlabs.io/",
                "2. Dang ky tai khoan",
                "3. Vao Profile -> API Key",
                "4. Copy API key",
                "5. Them vao file .env: ELEVENLABS_API_KEY=your_key_here"
            ],
            "required": True
        },
        {
            "name": "GOOGLE GEMINI API",
            "description": "Phan tich noi dung va tao cau truc bai giang",
            "website": "https://aistudio.google.com/app/apikey",
            "steps": [
                "1. Truy cap https://aistudio.google.com/app/apikey",
                "2. Dang nhap Google account",
                "3. Click 'Create API Key'",
                "4. Copy API key",
                "5. Them vao file .env: GEMINI_API_KEY=your_key_here"
            ],
            "required": True
        },
        {
            "name": "UNSPLASH API",
            "description": "Backup cho tim hinh anh",
            "website": "https://unsplash.com/developers",
            "steps": [
                "1. Truy cap https://unsplash.com/developers",
                "2. Click 'Register as a developer'",
                "3. Tao ung dung moi",
                "4. Copy Access Key",
                "5. Them vao file .env: UNSPLASH_ACCESS_KEY=your_key_here"
            ],
            "required": False
        },
        {
            "name": "OPENAI DALL-E API",
            "description": "Tao hinh anh bang AI (tuy chon)",
            "website": "https://platform.openai.com/api-keys",
            "steps": [
                "1. Truy cap https://platform.openai.com/api-keys",
                "2. Dang nhap OpenAI account",
                "3. Click 'Create new secret key'",
                "4. Copy API key",
                "5. Them vao file .env: OPENAI_API_KEY=your_key_here"
            ],
            "required": False
        },
        {
            "name": "STABILITY AI API",
            "description": "Tao hinh anh bang AI (tuy chon)",
            "website": "https://platform.stability.ai/",
            "steps": [
                "1. Truy cap https://platform.stability.ai/",
                "2. Dang ky tai khoan",
                "3. Vao API Keys section",
                "4. Tao API key moi",
                "5. Them vao file .env: STABILITY_API_KEY=your_key_here"
            ],
            "required": False
        }
    ]
    
    for i, api in enumerate(apis, 1):
        status = "BAT BUOC" if api["required"] else "TUY CHON"
        print(f"\n{i}. {api['name']} - {status}")
        print(f"   Mo ta: {api['description']}")
        print(f"   Website: {api['website']}")
        print("   Cac buoc:")
        for step in api["steps"]:
            print(f"      {step}")

def check_current_keys():
    """Kiem tra API keys hien tai"""
    print("\nKIEM TRA API KEYS HIEN TAI:")
    print("-" * 40)
    
    # Load .env file if exists
    env_file = Path(".env")
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            keys = {
                "PEXELS_API_KEY": "Pexels (Hinh anh)",
                "ELEVENLABS_API_KEY": "ElevenLabs (Giong noi)",
                "GEMINI_API_KEY": "Gemini (Phan tich noi dung)",
                "UNSPLASH_ACCESS_KEY": "Unsplash (Hinh anh backup)",
                "OPENAI_API_KEY": "OpenAI DALL-E (Tao hinh anh)",
                "STABILITY_API_KEY": "Stability AI (Tao hinh anh)"
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
                                print(f"   CO: {description}: {masked_value}")
                            else:
                                print(f"   CHUA CO GIA TRI: {description}")
                            break
                    else:
                        print(f"   KHONG TIM THAY: {description}")
                else:
                    print(f"   CHUA CO: {description}")
        except Exception as e:
            print(f"   LOI DOC FILE .env: {e}")
    else:
        print("   CHUA CO FILE .env")

def create_env_template():
    """Tao template file .env"""
    print("\nTAO TEMPLATE FILE .ENV:")
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
        print("   DA TAO FILE .env.template")
        print("   Huong dan:")
        print("      1. Copy .env.template thanh .env")
        print("      2. Dien API keys vao file .env")
        print("      3. Chay lai he thong")
    except Exception as e:
        print(f"   LOI TAO TEMPLATE: {e}")

def print_priority_guide():
    """In huong dan uu tien"""
    print("\nHUONG DAN UU TIEN:")
    print("-" * 40)
    print("1. BAT BUOC (Can co de he thong hoat dong):")
    print("   - PEXELS_API_KEY: Tim hinh anh phu hop voi noi dung")
    print("   - ELEVENLABS_API_KEY: Tao giong nguoi that")
    print("   - GEMINI_API_KEY: Phan tich noi dung va tao cau truc")
    print()
    print("2. TUY CHON (Cai thien chat luong):")
    print("   - UNSPLASH_ACCESS_KEY: Backup cho hinh anh")
    print("   - OPENAI_API_KEY: Tao hinh anh bang AI")
    print("   - STABILITY_API_KEY: Tao hinh anh bang AI")
    print()
    print("3. LUU Y:")
    print("   - Bat dau voi 3 API bat buoc")
    print("   - Them API tuy chon de cai thien chat luong")
    print("   - Pexels mien phi, ElevenLabs co free tier")
    print("   - Gemini co free tier voi gioi han")

def main():
    """Main function"""
    print_header()
    print_api_guide()
    check_current_keys()
    create_env_template()
    print_priority_guide()
    
    print("\n" + "=" * 60)
    print("HOAN THANH!")
    print("=" * 60)
    print("Sau khi co du API keys:")
    print("1. Chay: python setup_api_keys.py")
    print("2. Test: python test_image_matching.py")
    print("3. Tao video tu ung dung web")

if __name__ == "__main__":
    main()
