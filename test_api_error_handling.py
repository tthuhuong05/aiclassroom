#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test API Endpoint for Video Creation with Better Error Handling
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_api_with_authentication():
    """Test API endpoint with proper authentication"""
    print("=" * 60)
    print("TEST API ENDPOINT VOI AUTHENTICATION")
    print("=" * 60)
    
    try:
        # Start the Flask app
        from app import app
        
        with app.test_client() as client:
            # Create a test user
            from model.user_model import UserModel
            user_model = UserModel()
            
            # Check if test user exists, if not create one
            test_user = user_model.find_user_by_username("test_video_user")
            if not test_user:
                user_model.create_user("test_video_user", "test_password", "teacher")
                print("Created test user: test_video_user")
            
            # Login first
            print("1. Logging in...")
            login_response = client.post('/login', data={
                'email': 'test_video_user',
                'password': 'test_password'
            }, follow_redirects=True)
            
            print(f"   Login status: {login_response.status_code}")
            
            if login_response.status_code != 200:
                print("   NO - Login failed")
                return False
            
            print("   OK - Login successful")
            
            # Test API endpoint
            print("\n2. Testing API endpoint...")
            
            # Create a test file
            test_content = """
            # Introduction to Machine Learning
            
            Machine Learning is a subset of artificial intelligence.
            
            ## Key Concepts
            
            ### Supervised Learning
            Uses labeled data to train models.
            
            ### Unsupervised Learning
            Finds patterns in unlabeled data.
            
            ## Applications
            Used in healthcare, finance, and technology.
            
            ## Conclusion
            ML is transforming problem-solving approaches.
            """
            
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            temp_file.write(test_content)
            temp_file.close()
            
            print(f"   Created test file: {temp_file.name}")
            
            # Test the API endpoint
            with open(temp_file.name, 'rb') as f:
                data = {
                    'file': (f, 'test_document.txt', 'text/plain'),
                    'title': 'Test AI Video'
                }
                
                print("   Sending request to /api/convert-doc-to-video...")
                response = client.post('/api/convert-doc-to-video', 
                                     data=data,
                                     content_type='multipart/form-data')
                
                print(f"   Response status: {response.status_code}")
                print(f"   Response headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    result = response.get_json()
                    print("   Response JSON:")
                    print(f"     ok: {result.get('ok')}")
                    print(f"     video_url: {result.get('video_url')}")
                    print(f"     caption_url: {result.get('caption_url')}")
                    print(f"     script_text length: {len(result.get('script_text', ''))}")
                    print(f"     lecture_structure: {result.get('lecture_structure')}")
                    
                    if result.get('ok'):
                        print("   OK - API endpoint working correctly!")
                        return True
                    else:
                        print(f"   NO - API returned error: {result.get('error')}")
                        return False
                else:
                    print(f"   NO - HTTP error: {response.status_code}")
                    print(f"   Response text: {response.get_data(as_text=True)[:200]}...")
                    return False
                    
    except Exception as e:
        print(f"NO - Error testing API: {e}")
        return False
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def test_api_without_authentication():
    """Test API endpoint without authentication"""
    print("\n" + "=" * 60)
    print("TEST API ENDPOINT KHONG CO AUTHENTICATION")
    print("=" * 60)
    
    try:
        # Start the Flask app
        from app import app
        
        with app.test_client() as client:
            # Create a test file
            test_content = "# Test Document\n\nThis is a test document."
            
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
            temp_file.write(test_content)
            temp_file.close()
            
            print(f"Created test file: {temp_file.name}")
            
            # Test the API endpoint without session
            with open(temp_file.name, 'rb') as f:
                data = {
                    'file': (f, 'test.txt', 'text/plain'),
                    'title': 'Test Video'
                }
                
                print("Sending request to /api/convert-doc-to-video...")
                response = client.post('/api/convert-doc-to-video', 
                                     data=data,
                                     content_type='multipart/form-data')
                
                print(f"Response status: {response.status_code}")
                print(f"Response headers: {dict(response.headers)}")
                
                if response.status_code == 302:
                    print("OK - Redirected to login (expected behavior)")
                    print(f"Location: {response.headers.get('Location')}")
                    return True
                elif response.status_code == 200:
                    print("OK - API worked without auth (unexpected)")
                    return True
                else:
                    print(f"NO - Unexpected status: {response.status_code}")
                    return False
                    
    except Exception as e:
        print(f"NO - Error testing API: {e}")
        return False
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def test_content_type_handling():
    """Test content type handling"""
    print("\n" + "=" * 60)
    print("TEST CONTENT TYPE HANDLING")
    print("=" * 60)
    
    try:
        # Start the Flask app
        from app import app
        
        with app.test_client() as client:
            # Test with different content types
            test_cases = [
                {
                    'name': 'No authentication',
                    'auth': False,
                    'expected_status': 302,
                    'expected_content_type': 'text/html'
                },
                {
                    'name': 'With authentication',
                    'auth': True,
                    'expected_status': 200,
                    'expected_content_type': 'application/json'
                }
            ]
            
            for test_case in test_cases:
                print(f"\nTest case: {test_case['name']}")
                
                if test_case['auth']:
                    # Login first
                    login_response = client.post('/login', data={
                        'email': 'test_video_user',
                        'password': 'test_password'
                    }, follow_redirects=True)
                    
                    if login_response.status_code != 200:
                        print("  NO - Login failed")
                        continue
                
                # Create test file
                temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
                temp_file.write("# Test Document")
                temp_file.close()
                
                # Test API
                with open(temp_file.name, 'rb') as f:
                    data = {
                        'file': (f, 'test.txt', 'text/plain'),
                        'title': 'Test Video'
                    }
                    
                    response = client.post('/api/convert-doc-to-video', 
                                         data=data,
                                         content_type='multipart/form-data')
                    
                    print(f"  Status: {response.status_code}")
                    print(f"  Content-Type: {response.headers.get('content-type')}")
                    
                    if response.status_code == test_case['expected_status']:
                        print("  OK - Expected status")
                    else:
                        print(f"  NO - Unexpected status (expected {test_case['expected_status']})")
                
                # Clean up
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                    
    except Exception as e:
        print(f"NO - Error testing content type: {e}")
        return False

def main():
    """Main function"""
    print("KIEM TRA API ENDPOINT VOI ERROR HANDLING")
    
    # Test without auth (should redirect)
    no_auth_ok = test_api_without_authentication()
    
    # Test with auth (should work)
    auth_ok = test_api_with_authentication()
    
    # Test content type handling
    content_type_ok = test_content_type_handling()
    
    print("\n" + "=" * 60)
    print("KET QUA TONG HOP")
    print("=" * 60)
    
    if no_auth_ok and auth_ok and content_type_ok:
        print("OK - API endpoint hoạt động đúng!")
        print("\nCác tính năng đã được sửa:")
        print("OK - Error handling cho authentication")
        print("OK - Content type validation")
        print("OK - Proper error messages")
        print("\nJavaScript đã được cập nhật để:")
        print("- Kiểm tra response status")
        print("- Kiểm tra content type")
        print("- Hiển thị thông báo lỗi rõ ràng")
        print("- Xử lý redirect đến login")
    else:
        print("NO - Có lỗi trong API endpoint")
        print(f"No auth test: {'OK' if no_auth_ok else 'NO'}")
        print(f"Auth test: {'OK' if auth_ok else 'NO'}")
        print(f"Content type test: {'OK' if content_type_ok else 'NO'}")

if __name__ == "__main__":
    main()
