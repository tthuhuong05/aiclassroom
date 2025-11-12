#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple LunaAI test without emojis
"""

import os
import sys
import requests
import json
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Load environment variables
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def test_luna_api():
    """Test LunaAI API"""
    print("Testing LunaAI API...")
    
    api_key = os.getenv("LUNA_API_KEY")
    if not api_key:
        print("ERROR: LUNA_API_KEY not found")
        return False
    
    print(f"Found API key: {api_key[:10]}...")
    
    # Try different possible endpoints
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
        "prompt": "test image",
        "model": "luna-vision",
        "size": "1024x1024",
        "quality": "high",
        "num_images": 1
    }
    
    for endpoint in endpoints:
        print(f"Trying: {endpoint}")
        try:
            response = requests.post(
                endpoint,
                json=test_data,
                headers=headers,
                timeout=10
            )
            
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text[:100]}...")
            
            if response.status_code == 200:
                print(f"SUCCESS with: {endpoint}")
                return True
            elif response.status_code == 401:
                print("ERROR: Unauthorized - API key invalid")
            elif response.status_code == 404:
                print("ERROR: Not found - Wrong endpoint")
            else:
                print(f"ERROR: {response.status_code}")
                
        except Exception as e:
            print(f"EXCEPTION: {e}")
    
    return False

def test_luna_service():
    """Test LunaAI service"""
    print("\nTesting LunaAI service...")
    
    try:
        from services.luna_ai_service import is_luna_ai_available, luna_ai_service
        
        if is_luna_ai_available():
            print("SUCCESS: LunaAI service available")
            
            # Test simple generation
            result = luna_ai_service.generate_image("test", style="realistic")
            
            if result and result.get("success"):
                print("SUCCESS: Image generation worked!")
                return True
            else:
                print("ERROR: Image generation failed")
                return False
        else:
            print("ERROR: LunaAI service not available")
            return False
            
    except Exception as e:
        print(f"ERROR: LunaAI service error: {e}")
        return False

def main():
    """Main function"""
    print("LunaAI API Test")
    print("=" * 30)
    
    api_ok = test_luna_api()
    service_ok = test_luna_service()
    
    print("\nResults:")
    print(f"  Direct API: {'OK' if api_ok else 'FAILED'}")
    print(f"  Service: {'OK' if service_ok else 'FAILED'}")
    
    if not api_ok and not service_ok:
        print("\nLunaAI is not working. Issues:")
        print("  1. Wrong API key")
        print("  2. Wrong endpoint URL")
        print("  3. API service down")
        print("  4. Wrong API format")
        
        print("\nSuggestions:")
        print("  1. Check LunaAI documentation")
        print("  2. Verify API key is correct")
        print("  3. Check if LunaAI is the right service")
        print("  4. Try a different image generation service")

if __name__ == "__main__":
    main()
