#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive LunaAI API Test
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

def test_luna_api_comprehensive():
    """Test LunaAI API with comprehensive approach"""
    print("Comprehensive LunaAI API Test")
    print("=" * 40)
    
    api_key = os.getenv("LUNA_API_KEY")
    if not api_key:
        print("ERROR: LUNA_API_KEY not found")
        return False
    
    print(f"API Key: {api_key[:10]}...")
    
    # Test different possible endpoints and formats
    test_cases = [
        # Format 1: Standard REST API
        {
            "name": "Standard REST API",
            "url": "https://api.luna.ai/v1/images/generations",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test image", "n": 1, "size": "1024x1024"}
        },
        # Format 2: API Key in header
        {
            "name": "API Key Header",
            "url": "https://api.luna.ai/v1/images/generations",
            "headers": {"X-API-Key": api_key, "Content-Type": "application/json"},
            "data": {"prompt": "test image", "n": 1, "size": "1024x1024"}
        },
        # Format 3: Different endpoint
        {
            "name": "Generate Endpoint",
            "url": "https://api.luna.ai/v1/generate",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test image", "model": "luna-vision", "size": "1024x1024"}
        },
        # Format 4: Simple endpoint
        {
            "name": "Simple Generate",
            "url": "https://api.luna.ai/generate",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test image", "size": "1024x1024"}
        },
        # Format 5: Query parameter
        {
            "name": "Query Parameter",
            "url": f"https://api.luna.ai/v1/images/generations?api_key={api_key}",
            "headers": {"Content-Type": "application/json"},
            "data": {"prompt": "test image", "n": 1, "size": "1024x1024"}
        },
        # Format 6: Different domain
        {
            "name": "Different Domain",
            "url": "https://lunaai.video/api/generate",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test image", "type": "image", "size": "1024x1024"}
        },
        # Format 7: Video generation (since LunaAI might be video-focused)
        {
            "name": "Video Generation",
            "url": "https://api.luna.ai/v1/videos/generations",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test video", "duration": 5, "size": "1024x1024"}
        },
        # Format 8: Text to video
        {
            "name": "Text to Video",
            "url": "https://api.luna.ai/v1/text-to-video",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"text": "test video", "duration": 5}
        }
    ]
    
    successful_endpoints = []
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"URL: {test_case['url']}")
        
        try:
            response = requests.post(
                test_case['url'],
                json=test_case['data'],
                headers=test_case['headers'],
                timeout=15
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print(f"SUCCESS: {test_case['name']} works!")
                successful_endpoints.append(test_case)
            elif response.status_code == 401:
                print("ERROR: Unauthorized - API key may be invalid")
            elif response.status_code == 404:
                print("ERROR: Not found - Wrong endpoint")
            elif response.status_code == 400:
                print("ERROR: Bad request - Wrong data format")
            else:
                print(f"ERROR: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("ERROR: Request timeout")
        except requests.exceptions.ConnectionError:
            print("ERROR: Connection error")
        except Exception as e:
            print(f"ERROR: {e}")
    
    return successful_endpoints

def test_luna_with_different_formats():
    """Test LunaAI with different data formats"""
    print("\nTesting Different Data Formats")
    print("=" * 40)
    
    api_key = os.getenv("LUNA_API_KEY")
    if not api_key:
        return False
    
    # Try different data formats
    formats = [
        {"prompt": "test image", "n": 1, "size": "1024x1024"},
        {"text": "test image", "count": 1, "resolution": "1024x1024"},
        {"input": "test image", "num_images": 1, "dimensions": "1024x1024"},
        {"query": "test image", "amount": 1, "format": "1024x1024"},
        {"description": "test image", "quantity": 1, "size": "1024x1024"}
    ]
    
    base_url = "https://api.luna.ai/v1/images/generations"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    for i, data_format in enumerate(formats, 1):
        print(f"\nFormat {i}: {list(data_format.keys())}")
        
        try:
            response = requests.post(base_url, json=data_format, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("SUCCESS: This format works!")
                return data_format
            else:
                print(f"Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    return None

def main():
    """Main function"""
    print("LunaAI Comprehensive API Test")
    print("=" * 50)
    
    # Test comprehensive endpoints
    successful_endpoints = test_luna_api_comprehensive()
    
    # Test different data formats
    working_format = test_luna_with_different_formats()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    
    if successful_endpoints:
        print(f"SUCCESS: Found {len(successful_endpoints)} working endpoint(s):")
        for endpoint in successful_endpoints:
            print(f"  - {endpoint['name']}: {endpoint['url']}")
    else:
        print("ERROR: No working endpoints found")
    
    if working_format:
        print(f"SUCCESS: Found working data format: {working_format}")
    else:
        print("ERROR: No working data format found")
    
    if not successful_endpoints and not working_format:
        print("\nRECOMMENDATIONS:")
        print("1. Check if LunaAI is the correct service")
        print("2. Verify the API key is correct")
        print("3. Check LunaAI documentation for correct endpoints")
        print("4. Contact LunaAI support")
        print("5. Consider using alternative image generation services")

if __name__ == "__main__":
    main()
