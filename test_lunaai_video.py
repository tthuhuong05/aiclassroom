#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LunaAI Video API Test
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

def test_lunaai_video_endpoints():
    """Test LunaAI video endpoints"""
    print("Testing LunaAI Video Endpoints")
    print("=" * 40)
    
    api_key = os.getenv("LUNA_API_KEY")
    if not api_key:
        print("ERROR: LUNA_API_KEY not found")
        return False
    
    print(f"API Key: {api_key[:10]}...")
    
    # Test different possible endpoints on lunaai.video
    test_cases = [
        # Video generation endpoints
        {
            "name": "Video Generation API",
            "url": "https://lunaai.video/api/v1/videos/generate",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test video", "duration": 5}
        },
        {
            "name": "Text to Video",
            "url": "https://lunaai.video/api/v1/text-to-video",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"text": "test video", "duration": 5}
        },
        {
            "name": "Generate Video",
            "url": "https://lunaai.video/api/generate",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test video", "type": "video"}
        },
        {
            "name": "Create Video",
            "url": "https://lunaai.video/api/v1/create",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test video", "duration": 5}
        },
        # Image generation endpoints (in case they also do images)
        {
            "name": "Image Generation",
            "url": "https://lunaai.video/api/v1/images/generate",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"prompt": "test image", "size": "1024x1024"}
        },
        # Different authentication methods
        {
            "name": "API Key Header",
            "url": "https://lunaai.video/api/v1/videos/generate",
            "headers": {"X-API-Key": api_key, "Content-Type": "application/json"},
            "data": {"prompt": "test video", "duration": 5}
        },
        {
            "name": "Query Parameter",
            "url": f"https://lunaai.video/api/v1/videos/generate?api_key={api_key}",
            "headers": {"Content-Type": "application/json"},
            "data": {"prompt": "test video", "duration": 5}
        },
        # Different data formats
        {
            "name": "Different Format",
            "url": "https://lunaai.video/api/v1/videos/generate",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "data": {"text": "test video", "length": 5, "resolution": "720p"}
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
            
            if response.status_code == 200:
                print(f"SUCCESS: {test_case['name']} works!")
                print(f"Response: {response.text[:200]}...")
                successful_endpoints.append(test_case)
            elif response.status_code == 401:
                print("ERROR: Unauthorized - API key may be invalid")
            elif response.status_code == 404:
                print("ERROR: Not found - Wrong endpoint")
            elif response.status_code == 400:
                print("ERROR: Bad request - Wrong data format")
                print(f"Response: {response.text[:200]}...")
            elif response.status_code == 405:
                print("ERROR: Method not allowed - Wrong HTTP method")
            else:
                print(f"ERROR: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                
        except requests.exceptions.Timeout:
            print("ERROR: Request timeout")
        except requests.exceptions.ConnectionError:
            print("ERROR: Connection error")
        except Exception as e:
            print(f"ERROR: {e}")
    
    return successful_endpoints

def test_lunaai_website_info():
    """Test LunaAI website for API info"""
    print("\nTesting LunaAI Website Info")
    print("=" * 40)
    
    try:
        # Try to get API documentation
        response = requests.get("https://lunaai.video/api/docs", timeout=10)
        print(f"API Docs Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: Found API documentation!")
            print(f"Content: {response.text[:500]}...")
        else:
            print("No API documentation found")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    try:
        # Try to get help page
        response = requests.get("https://lunaai.video/help", timeout=10)
        print(f"Help Page Status: {response.status_code}")
        
        if response.status_code == 200:
            print("SUCCESS: Found help page!")
            # Look for API information in the help page
            if "api" in response.text.lower():
                print("Help page contains API information")
            else:
                print("Help page doesn't contain API information")
                
    except Exception as e:
        print(f"ERROR: {e}")

def main():
    """Main function"""
    print("LunaAI Video API Test")
    print("=" * 50)
    
    # Test website info
    test_lunaai_website_info()
    
    # Test endpoints
    successful_endpoints = test_lunaai_video_endpoints()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    
    if successful_endpoints:
        print(f"SUCCESS: Found {len(successful_endpoints)} working endpoint(s):")
        for endpoint in successful_endpoints:
            print(f"  - {endpoint['name']}: {endpoint['url']}")
    else:
        print("ERROR: No working endpoints found")
        print("\nPOSSIBLE ISSUES:")
        print("1. LunaAI might not have a public API")
        print("2. API key might be invalid")
        print("3. API might be for internal use only")
        print("4. LunaAI might be a web-only service")
        
        print("\nRECOMMENDATIONS:")
        print("1. Check LunaAI website for API documentation")
        print("2. Contact LunaAI support: support@lunaai.video")
        print("3. Verify API key is correct")
        print("4. Consider using alternative services")

if __name__ == "__main__":
    main()
