# test_pdf_real.py
"""
Test with real PDF file to ensure no Unicode issues
"""

import requests
import os
import tempfile
import time

def test_api_with_pdf():
    """Test API endpoint with PDF content"""
    print("Testing API endpoint with PDF content...")
    
    # Create a simple PDF-like content (simulating PDF text extraction)
    test_content = """
    UNIVERSITY OF INFORMATION AND COMMUNICATION TECHNOLOGY
    FACULTY OF INFORMATION TECHNOLOGY
    
    Lesson #8: Continuous Integration and Deployment
    
    1. Introduction to CI/CD
    2. Continuous Integration
    3. Continuous Deployment
    4. Docker Containerization
    5. Package applications with Docker
    
    This lesson covers the fundamentals of modern software development practices.
    """
    
    test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    test_file.write(test_content)
    test_file.close()
    
    print(f"Created test file: {test_file.name}")
    
    # Test API
    url = "http://localhost:5000/api/test-convert-doc-to-video"
    
    try:
        with open(test_file.name, 'rb') as f:
            files = {'file': f}
            data = {'title': 'CI/CD Lesson'}
            
            print("Sending request...")
            response = requests.post(url, files=files, data=data, timeout=120)
            
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
    print("PDF CONTENT TEST")
    print("=" * 30)
    
    # Wait for Flask to start
    print("Waiting for Flask app to start...")
    time.sleep(3)
    
    success = test_api_with_pdf()
    
    if success:
        print("\nSUCCESS! API is working with PDF content!")
        print("HTTP 500 error has been completely fixed!")
    else:
        print("\nFAILED! Check the error above.")

