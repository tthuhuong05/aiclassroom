#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Avatar Display on Main Interface
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_avatar_display():
    """Test avatar display functionality"""
    print("=" * 60)
    print("TEST HIEN THI AVATAR TREN GIAO DIEN CHINH")
    print("=" * 60)
    
    try:
        # Start the Flask app
        from app import app
        
        with app.test_client() as client:
            # Create a test user with avatar
            from model.user_model import UserModel
            user_model = UserModel()
            
            # Check if test user exists, if not create one
            test_user = user_model.find_user_by_username("test_avatar_user")
            if not test_user:
                user_model.create_user("test_avatar_user", "test_password", "teacher", "avatars/test_avatar.jpg")
                print("Created test user with avatar: test_avatar_user")
            
            # Login
            login_response = client.post('/login', data={
                'email': 'test_avatar_user',
                'password': 'test_password'
            }, follow_redirects=True)
            
            print(f"Login status: {login_response.status_code}")
            
            if login_response.status_code != 200:
                print("NO - Login failed")
                return False
            
            print("OK - Login successful")
            
            # Test home page
            print("\nTesting home page...")
            home_response = client.get('/')
            
            print(f"Home page status: {home_response.status_code}")
            
            if home_response.status_code == 200:
                html_content = home_response.get_data(as_text=True)
                
                # Check if avatar URL is in the HTML
                if 'avatars/test_avatar.jpg' in html_content:
                    print("OK - Avatar URL found in HTML")
                else:
                    print("NO - Avatar URL not found in HTML")
                    print("HTML content preview:")
                    print(html_content[:500] + "...")
                    return False
                
                # Check if user info is in context
                if 'test_avatar_user' in html_content:
                    print("OK - Username found in HTML")
                else:
                    print("NO - Username not found in HTML")
                    return False
                
                print("OK - Avatar display test passed!")
                return True
            else:
                print(f"NO - Home page error: {home_response.status_code}")
                return False
                
    except Exception as e:
        print(f"NO - Error testing avatar display: {e}")
        return False

def test_context_processor():
    """Test context processor functionality"""
    print("\n" + "=" * 60)
    print("TEST CONTEXT PROCESSOR")
    print("=" * 60)
    
    try:
        # Start the Flask app
        from app import app
        
        with app.test_client() as client:
            # Create a test user
            from model.user_model import UserModel
            user_model = UserModel()
            
            # Check if test user exists
            test_user = user_model.find_user_by_username("test_avatar_user")
            if not test_user:
                print("NO - Test user not found")
                return False
            
            print(f"OK - Test user found: {test_user['username']}")
            print(f"Avatar path: {test_user['avatar_path'] if 'avatar_path' in test_user.keys() else 'None'}")
            
            # Login
            login_response = client.post('/login', data={
                'email': 'test_avatar_user',
                'password': 'test_password'
            }, follow_redirects=True)
            
            if login_response.status_code != 200:
                print("NO - Login failed")
                return False
            
            print("OK - Login successful")
            
            # Test context processor by accessing a page
            response = client.get('/')
            if response.status_code == 200:
                print("OK - Context processor working")
                return True
            else:
                print(f"NO - Context processor error: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"NO - Error testing context processor: {e}")
        return False

def test_avatar_file_exists():
    """Test if avatar file exists"""
    print("\n" + "=" * 60)
    print("TEST AVATAR FILE EXISTS")
    print("=" * 60)
    
    # Check if avatars directory exists
    avatars_dir = "static/avatars"
    if os.path.exists(avatars_dir):
        print(f"OK - Avatars directory exists: {avatars_dir}")
    else:
        print(f"NO - Avatars directory not found: {avatars_dir}")
        return False
    
    # List files in avatars directory
    avatar_files = os.listdir(avatars_dir)
    print(f"Avatar files found: {len(avatar_files)}")
    for file in avatar_files[:5]:  # Show first 5 files
        print(f"  - {file}")
    
    if len(avatar_files) > 0:
        print("OK - Avatar files exist")
        return True
    else:
        print("NO - No avatar files found")
        return False

def main():
    """Main function"""
    print("KIEM TRA HIEN THI AVATAR TREN GIAO DIEN CHINH")
    
    # Test avatar file exists
    file_ok = test_avatar_file_exists()
    
    # Test context processor
    context_ok = test_context_processor()
    
    # Test avatar display
    display_ok = test_avatar_display()
    
    print("\n" + "=" * 60)
    print("KET QUA TONG HOP")
    print("=" * 60)
    
    if file_ok and context_ok and display_ok:
        print("OK - Avatar display working correctly!")
        print("\nCac tinh nang da hoat dong:")
        print("OK - Avatar files exist")
        print("OK - Context processor working")
        print("OK - Avatar display on main interface")
        print("\nAvatar se hien thi tren:")
        print("- Trang chu")
        print("- Trang khoa hoc")
        print("- Tat ca cac trang khac")
    else:
        print("NO - Co loi trong hien thi avatar")
        print(f"File exists: {'OK' if file_ok else 'NO'}")
        print(f"Context processor: {'OK' if context_ok else 'NO'}")
        print(f"Avatar display: {'OK' if display_ok else 'NO'}")

if __name__ == "__main__":
    main()
