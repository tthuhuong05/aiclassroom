# debug_response.py
"""
Debug response from API
"""

import requests
import os
import tempfile
import time

def debug_api():
    """Debug API response"""
    print("Debugging API response...")
    
    # Create English-only test file
    test_content = "Python programming is a popular programming language."
    
    test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    test_file.write(test_content)
    test_file.close()
    
    print(f"Created test file: {test_file.name}")
    
    # Test API
    url = "http://localhost:5000/api/convert-doc-to-video"
    
    try:
        with open(test_file.name, 'rb') as f:
            files = {'file': f}
            data = {'title': 'Test Video'}
            
            print("Sending request...")
            response = requests.post(url, files=files, data=data, timeout=60)
            
            print(f"Status: {response.status_code}")
            print(f"Headers: {response.headers}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            print(f"Response length: {len(response.text)}")
            print(f"First 500 chars: {response.text[:500]}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"JSON response: {result}")
                    if result.get('ok'):
                        print("SUCCESS!")
                        return True
                    else:
                        print(f"API error: {result.get('error')}")
                        return False
                except Exception as e:
                    print(f"JSON parse error: {e}")
                    print(f"Raw response: {response.text}")
                    return False
            else:
                print(f"HTTP Error: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        os.unlink(test_file.name)

if __name__ == "__main__":
    print("API RESPONSE DEBUG")
    print("=" * 30)
    
    # Wait for Flask to start
    print("Waiting for Flask app to start...")
    time.sleep(3)
    
    debug_api()

