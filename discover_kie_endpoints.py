#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KIE AI Endpoint Discovery
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

def discover_kie_endpoints():
    """Discover KIE AI endpoints"""
    print("Discovering KIE AI Endpoints...")
    
    api_key = os.getenv("KIE_AI_KEY")
    if not api_key:
        print("ERROR: KIE_AI_KEY not found")
        return False
    
    print(f"API Key: {api_key[:10]}...")
    
    # Test different possible base URLs and endpoints
    base_urls = [
        "https://api.kie.ai",
        "https://kie.ai/api",
        "https://api.kie.ai/v1",
        "https://kie.ai/v1/api"
    ]
    
    endpoints = [
        "images/generations",
        "generate",
        "text-to-image", 
        "image-generation",
        "models",
        "chat/completions",
        "completions",
        "embeddings",
        "audio/speech",
        "audio/transcriptions"
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    test_data = {
        "prompt": "test image",
        "model": "kie-image-generation",
        "size": "1024x1024"
    }
    
    successful_endpoints = []
    
    for base_url in base_urls:
        print(f"\nTesting base URL: {base_url}")
        
        for endpoint in endpoints:
            full_url = f"{base_url}/{endpoint}"
            
            try:
                print(f"  Testing: {full_url}")
                
                # Try GET first
                response = requests.get(full_url, headers=headers, timeout=10)
                print(f"    GET Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"    SUCCESS: GET {full_url}")
                    successful_endpoints.append(("GET", full_url))
                elif response.status_code == 405:
                    # Method not allowed, try POST
                    response = requests.post(full_url, json=test_data, headers=headers, timeout=10)
                    print(f"    POST Status: {response.status_code}")
                    
                    if response.status_code == 200:
                        print(f"    SUCCESS: POST {full_url}")
                        successful_endpoints.append(("POST", full_url))
                    elif response.status_code == 400:
                        print(f"    POST 400: {response.text[:100]}...")
                    else:
                        print(f"    POST {response.status_code}")
                else:
                    print(f"    GET {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"    Timeout")
            except requests.exceptions.ConnectionError:
                print(f"    Connection Error")
            except Exception as e:
                print(f"    Error: {e}")
    
    return successful_endpoints

def test_kie_models():
    """Test KIE AI models endpoint"""
    print("\nTesting KIE AI Models...")
    
    api_key = os.getenv("KIE_AI_KEY")
    if not api_key:
        return False
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    models_urls = [
        "https://api.kie.ai/v1/models",
        "https://kie.ai/api/v1/models",
        "https://api.kie.ai/models",
        "https://kie.ai/api/models"
    ]
    
    for url in models_urls:
        try:
            print(f"Testing: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                print("SUCCESS: Found models endpoint!")
                print(f"Response: {response.text[:500]}...")
                return True
            else:
                print(f"Response: {response.text[:200]}...")
                
        except Exception as e:
            print(f"Error: {e}")
    
    return False

def main():
    """Main function"""
    print("KIE AI Endpoint Discovery")
    print("=" * 40)
    
    # Discover endpoints
    successful_endpoints = discover_kie_endpoints()
    
    # Test models
    models_ok = test_kie_models()
    
    print("\n" + "=" * 40)
    print("SUMMARY:")
    
    if successful_endpoints:
        print(f"SUCCESS: Found {len(successful_endpoints)} working endpoint(s):")
        for method, url in successful_endpoints:
            print(f"  - {method} {url}")
    else:
        print("ERROR: No working endpoints found")
    
    if models_ok:
        print("SUCCESS: Found models endpoint")
    else:
        print("ERROR: No models endpoint found")
    
    if not successful_endpoints and not models_ok:
        print("\nCONCLUSION:")
        print("KIE AI appears to not have a public API or the endpoints are different")
        print("The API key might be for a different service or internal use")
        
        print("\nRECOMMENDATIONS:")
        print("1. Check KIE AI documentation")
        print("2. Contact KIE AI support")
        print("3. Verify the API key is correct")
        print("4. Use alternative image generation services")

if __name__ == "__main__":
    main()
