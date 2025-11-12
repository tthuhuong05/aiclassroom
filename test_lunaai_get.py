#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LunaAI GET Method Test
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

def test_lunaai_get_methods():
    """Test LunaAI with GET methods"""
    print("Testing LunaAI with GET Methods")
    print("=" * 40)
    
    api_key = os.getenv("LUNA_API_KEY")
    if not api_key:
        print("ERROR: LUNA_API_KEY not found")
        return False
    
    print(f"API Key: {api_key[:10]}...")
    
    # Test GET methods
    test_cases = [
        {
            "name": "Video Generation GET",
            "url": "https://lunaai.video/api/v1/videos/generate",
            "headers": {"Authorization": f"Bearer {api_key}"},
            "params": {"prompt": "test video", "duration": 5}
        },
        {
            "name": "Text to Video GET",
            "url": "https://lunaai.video/api/v1/text-to-video",
            "headers": {"Authorization": f"Bearer {api_key}"},
            "params": {"text": "test video", "duration": 5}
        },
        {
            "name": "Generate Video GET",
            "url": "https://lunaai.video/api/generate",
            "headers": {"Authorization": f"Bearer {api_key}"},
            "params": {"prompt": "test video", "type": "video"}
        },
        {
            "name": "API Key in URL",
            "url": f"https://lunaai.video/api/v1/videos/generate?api_key={api_key}",
            "headers": {},
            "params": {"prompt": "test video", "duration": 5}
        },
        {
            "name": "X-API-Key Header",
            "url": "https://lunaai.video/api/v1/videos/generate",
            "headers": {"X-API-Key": api_key},
            "params": {"prompt": "test video", "duration": 5}
        }
    ]
    
    successful_endpoints = []
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"URL: {test_case['url']}")
        
        try:
            response = requests.get(
                test_case['url'],
                params=test_case['params'],
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
                print("ERROR: Bad request - Wrong parameters")
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

def test_lunaai_help_page():
    """Extract API info from help page"""
    print("\nExtracting API Info from Help Page")
    print("=" * 40)
    
    try:
        response = requests.get("https://lunaai.video/help", timeout=10)
        
        if response.status_code == 200:
            content = response.text.lower()
            
            # Look for API-related information
            api_keywords = ['api', 'endpoint', 'generate', 'video', 'text-to-video']
            found_keywords = [kw for kw in api_keywords if kw in content]
            
            print(f"Found keywords: {found_keywords}")
            
            # Look for specific patterns
            if 'api' in content:
                print("Help page mentions API")
            if 'endpoint' in content:
                print("Help page mentions endpoints")
            if 'generate' in content:
                print("Help page mentions generation")
                
            # Try to find API documentation link
            if 'docs' in content:
                print("Help page mentions documentation")
            if 'documentation' in content:
                print("Help page mentions documentation")
                
        else:
            print(f"ERROR: Could not access help page: {response.status_code}")
            
    except Exception as e:
        print(f"ERROR: {e}")

def main():
    """Main function"""
    print("LunaAI GET Method Test")
    print("=" * 50)
    
    # Test help page
    test_lunaai_help_page()
    
    # Test GET methods
    successful_endpoints = test_lunaai_get_methods()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    
    if successful_endpoints:
        print(f"SUCCESS: Found {len(successful_endpoints)} working endpoint(s):")
        for endpoint in successful_endpoints:
            print(f"  - {endpoint['name']}: {endpoint['url']}")
    else:
        print("ERROR: No working endpoints found")
        print("\nCONCLUSION:")
        print("LunaAI appears to be a web-only service without a public API")
        print("The API key might be for internal use or a different service")
        
        print("\nNEXT STEPS:")
        print("1. Contact LunaAI support: support@lunaai.video")
        print("2. Ask about API access and documentation")
        print("3. Verify if the API key is correct")
        print("4. Consider using alternative image/video generation services")

if __name__ == "__main__":
    main()
