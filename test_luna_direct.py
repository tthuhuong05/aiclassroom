#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test LunaAI API đơn giản
"""

import os
import sys
import requests
import json
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent))

# Load biến môi trường từ file .env
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def test_luna_api_direct():
    """Test LunaAI API trực tiếp"""
    print("🔍 Testing LunaAI API directly...")
    
    api_key = os.getenv("LUNA_API_KEY")
    if not api_key:
        print("❌ LUNA_API_KEY not found in environment")
        return False
    
    print(f"✅ Found API key: {api_key[:10]}...")
    
    # Thử các endpoint có thể có
    endpoints = [
        "https://api.luna.ai/v1/images/generations",
        "https://api.luna.ai/v1/generate",
        "https://api.luna.ai/generate",
        "https://lunaai.video/api/generate",
        "https://api.lunaai.video/v1/images/generations"
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    test_data = {
        "prompt": "test image generation",
        "model": "luna-vision",
        "size": "1024x1024",
        "quality": "high",
        "num_images": 1
    }
    
    for endpoint in endpoints:
        print(f"🌐 Trying endpoint: {endpoint}")
        try:
            response = requests.post(
                endpoint,
                json=test_data,
                headers=headers,
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print(f"✅ Success with endpoint: {endpoint}")
                return True
            elif response.status_code == 401:
                print(f"❌ Unauthorized - API key may be invalid")
            elif response.status_code == 404:
                print(f"❌ Not found - Wrong endpoint")
            else:
                print(f"❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    return False

def test_luna_service():
    """Test LunaAI service"""
    print("\n🔍 Testing LunaAI service...")
    
    try:
        from services.luna_ai_service import is_luna_ai_available, luna_ai_service
        
        if is_luna_ai_available():
            print("✅ LunaAI service is available")
            
            # Test simple generation
            result = luna_ai_service.generate_image("test image", style="realistic")
            
            if result and result.get("success"):
                print("✅ Image generation successful!")
                return True
            else:
                print("❌ Image generation failed")
                return False
        else:
            print("❌ LunaAI service not available")
            return False
            
    except Exception as e:
        print(f"❌ LunaAI service error: {e}")
        return False

def main():
    """Hàm main"""
    print("Testing LunaAI API")
    print("=" * 40)
    
    direct_ok = test_luna_api_direct()
    service_ok = test_luna_service()
    
    print("Test Results:")
    print(f"   Direct API: {'✅ OK' if direct_ok else '❌ Failed'}")
    print(f"   Service: {'✅ OK' if service_ok else '❌ Failed'}")
    
    if not direct_ok and not service_ok:
        print("\n⚠️ LunaAI is not working. Possible issues:")
        print("   1. Wrong API key")
        print("   2. Wrong endpoint URL")
        print("   3. API service down")
        print("   4. Wrong API format")
        
        print("\n💡 Suggestions:")
        print("   1. Check LunaAI documentation")
        print("   2. Verify API key is correct")
        print("   3. Check if LunaAI is the right service")
        print("   4. Try a different image generation service")

if __name__ == "__main__":
    main()
