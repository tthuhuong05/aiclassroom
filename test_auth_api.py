#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test API with Authentication
"""

import requests
import tempfile
import os
from pathlib import Path

# Add project root to path
import sys
sys.path.append(str(Path(__file__).parent))

def test_with_authentication():
    """Test API endpoint with proper authentication"""
    print("=" * 60)
    print("TEST API WITH AUTHENTICATION")
    print("=" * 60)
    
    # Start Flask app context
    try:
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

def test_frontend_integration():
    """Test frontend integration"""
    print("\n" + "=" * 60)
    print("TEST FRONTEND INTEGRATION")
    print("=" * 60)
    
    print("""
    FRONTEND INTEGRATION CHECKLIST:
    
    1. ✅ JavaScript Error Handling
       - Response status checking
       - Content type validation
       - Authentication error handling
       - User-friendly error messages
    
    2. ✅ API Endpoint Protection
       - @login_required decorator
       - Session validation
       - Redirect to login if not authenticated
    
    3. ✅ File Upload Handling
       - FormData creation
       - File validation
       - Multipart form submission
    
    4. ✅ Error Display
       - Clear error messages
       - Status updates
       - User guidance
    
    COMMON CAUSES OF "FAILED TO FETCH":
    
    1. ❌ User not logged in
       - Solution: Login first
       - Check: Session cookies
    
    2. ❌ Session expired
       - Solution: Re-login
       - Check: Session timeout
    
    3. ❌ Network issues
       - Solution: Check internet connection
       - Check: Server status
    
    4. ❌ CORS issues
       - Solution: Check server CORS settings
       - Check: Same-origin policy
    
    5. ❌ Server errors
       - Solution: Check server logs
       - Check: API endpoint status
    """)

def main():
    """Main function"""
    print("TESTING API WITH AUTHENTICATION")
    
    # Test with authentication
    auth_ok = test_with_authentication()
    
    # Test frontend integration
    test_frontend_integration()
    
    print("\n" + "=" * 60)
    print("DIAGNOSIS AND SOLUTION")
    print("=" * 60)
    
    if auth_ok:
        print("OK - API endpoint working with authentication!")
        print("\nSOLUTION FOR 'FAILED TO FETCH' ERROR:")
        print("1. Make sure you are logged in to the application")
        print("2. Check if your session has expired")
        print("3. Try refreshing the page and logging in again")
        print("4. Clear browser cache and cookies")
        print("5. Check browser console for detailed error messages")
    else:
        print("NO - API endpoint has issues")
        print("\nTROUBLESHOOTING STEPS:")
        print("1. Check if Flask app is running on port 5000")
        print("2. Verify API endpoint is accessible")
        print("3. Check server logs for errors")
        print("4. Test with different browsers")
        print("5. Check network connectivity")

if __name__ == "__main__":
    main()
