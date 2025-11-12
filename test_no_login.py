# test_no_login.py
"""
Test API without login requirement
"""

import requests
import os
import tempfile
import time

def test_api():
    """Test API endpoint without login"""
    print("Testing API endpoint without login...")
    
    # Create English-only test file
    test_content = "Python programming is a popular programming language."
    
    test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    test_file.write(test_content)
    test_file.close()
    
    print(f"Created test file: {test_file.name}")
    
    # Test API with new endpoint
    url = "http://localhost:5000/api/test-convert-doc-to-video"
    
    try:
        with open(test_file.name, 'rb') as f:
            files = {'file': f}
            data = {'title': 'Test Video'}
            
            print("Sending request...")
            response = requests.post(url, files=files, data=data, timeout=60)
            
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"JSON response: {result}")
                    if result.get('ok'):
                        print("SUCCESS!")
                        print(f"Video URL: {result.get('video_url')}")
                        print(f"Caption URL: {result.get('caption_url')}")
                        return True
                    else:
                        print(f"API error: {result.get('error')}")
                        return False
                except Exception as e:
                    print(f"JSON parse error: {e}")
                    print(f"Raw response: {response.text[:200]}...")
                    return False
            else:
                print(f"HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        os.unlink(test_file.name)

if __name__ == "__main__":
    print("NO-LOGIN API TEST")
    print("=" * 30)
    
    # Wait for Flask to start
    print("Waiting for Flask app to start...")
    time.sleep(3)
    
    success = test_api()
    
    if success:
        print("\nSUCCESS! API is working!")
        print("HTTP 500 error has been fixed!")
    else:
        print("\nFAILED! Check the error above.")

