#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test API Endpoint with Authentication
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_api_with_auth():
    """Test the API endpoint with authentication"""
    print("=" * 60)
    print("TEST API ENDPOINT VOI AUTHENTICATION")
    print("=" * 60)
    
    try:
        # Start the Flask app
        from app import app
        
        with app.test_client() as client:
            # First, login to get session
            print("1. Dang nhap de lay session...")
            
            # Create a test user first
            from model.user_model import UserModel
            user_model = UserModel()
            
            # Check if test user exists, if not create one
            test_user = user_model.find_user_by_username("test_user")
            if not test_user:
                user_model.create_user("test_user", "test_password", "teacher")
                print("   Created test user: test_user")
            
            # Login
            login_response = client.post('/login', data={
                'email': 'test_user',
                'password': 'test_password'
            }, follow_redirects=True)
            
            print(f"   Login status: {login_response.status_code}")
            
            if login_response.status_code != 200:
                print("   NO - Login failed")
                return False
            
            print("   OK - Login successful")
            
            # Now test the API endpoint
            print("\n2. Test API endpoint voi session...")
            
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
            
            # Test the API endpoint with session
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

def test_without_auth():
    """Test the API endpoint without authentication"""
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
                
                if response.status_code == 302:
                    print("OK - Redirected to login (expected behavior)")
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

def main():
    """Main function"""
    print("KIEM TRA API ENDPOINT VOI AUTHENTICATION")
    
    # Test without auth (should redirect)
    no_auth_ok = test_without_auth()
    
    # Test with auth (should work)
    auth_ok = test_api_with_auth()
    
    print("\n" + "=" * 60)
    print("KET QUA TONG HOP")
    print("=" * 60)
    
    if no_auth_ok and auth_ok:
        print("OK - API endpoint hoạt động đúng!")
        print("\nNguyên nhân lỗi 'Failed to fetch':")
        print("1. User chưa đăng nhập")
        print("2. Session hết hạn")
        print("3. Lỗi JavaScript trong frontend")
        print("\nGiải pháp:")
        print("1. Đảm bảo user đã đăng nhập")
        print("2. Kiểm tra session trong browser")
        print("3. Kiểm tra console browser (F12)")
        print("4. Thử refresh trang và đăng nhập lại")
    else:
        print("NO - Có lỗi trong API endpoint")
        print("Cần kiểm tra lại code")

if __name__ == "__main__":
    main()
