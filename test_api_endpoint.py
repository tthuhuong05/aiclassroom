# test_api_endpoint.py
"""
Test script để test API endpoint thực tế
"""

import requests
import os
import tempfile

def test_api_endpoint():
    """Test API endpoint với file thực tế"""
    print("Testing API endpoint...")
    
    # Tạo file test
    test_content = """
    Python Programming Fundamentals
    
    Python is a high-level programming language known for its simplicity and readability.
    In this lesson, we will cover:
    
    1. Variables and Data Types
    2. Control Structures
    3. Functions and Modules
    4. Object-Oriented Programming
    
    Python is widely used in web development, data science, and artificial intelligence.
    """
    
    # Tạo file text test
    test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    test_file.write(test_content)
    test_file.close()
    
    print(f"Created test file: {test_file.name}")
    
    # Test API endpoint
    url = "http://localhost:5000/api/convert-doc-to-video"
    
    try:
        with open(test_file.name, 'rb') as f:
            files = {'file': f}
            data = {
                'title': 'Python Programming Test',
                'wpm': '140'
            }
            
            print("Sending request to API...")
            response = requests.post(url, files=files, data=data, timeout=300)
            
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    print("SUCCESS! Video created successfully!")
                    print(f"Video URL: {result.get('video_url')}")
                    print(f"Caption URL: {result.get('caption_url')}")
                    print(f"Script text: {result.get('script_text', '')[:100]}...")
                    return True
                else:
                    print(f"API returned error: {result.get('error')}")
                    return False
            else:
                print(f"HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
    except requests.exceptions.ConnectionError:
        print("Connection error: Make sure the Flask app is running on localhost:5000")
        return False
    except requests.exceptions.Timeout:
        print("Request timeout: Video creation took too long")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
    finally:
        # Cleanup
        os.unlink(test_file.name)

def main():
    """Chạy test"""
    print("API ENDPOINT TEST")
    print("=" * 50)
    print("Make sure Flask app is running: python app.py")
    print("=" * 50)
    
    success = test_api_endpoint()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS! API endpoint is working correctly!")
        print("The HTTP 500 error has been fixed!")
    else:
        print("FAILED! API endpoint still has issues.")
        print("Check the error messages above.")
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)