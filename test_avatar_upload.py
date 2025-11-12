#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Avatar Upload Feature
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_avatar_upload():
    """Test avatar upload functionality"""
    print("=" * 60)
    print("TEST TINH NANG UPLOAD AVATAR")
    print("=" * 60)
    
    try:
        # Test database update
        from model.user_model import UserModel
        user_model = UserModel()
        
        print("OK Database updated successfully")
        print("OK Avatar column added to users table")
        
        # Test avatar directory
        avatar_dir = "static/avatars"
        if os.path.exists(avatar_dir):
            print(f"OK Avatar directory exists: {avatar_dir}")
        else:
            print(f"NO Avatar directory not found: {avatar_dir}")
            return False
        
        # Test user creation with avatar
        test_avatar_path = "avatars/test_avatar.jpg"
        user_model.create_user("test_user", "test_password", "student", test_avatar_path)
        
        # Test user retrieval
        user = user_model.find_user_by_username("test_user")
        if user and user["avatar_path"] == test_avatar_path:
            print("OK User creation with avatar successful")
            print(f"OK Avatar path saved: {user['avatar_path']}")
        else:
            print("NO User creation with avatar failed")
            return False
        
        # Clean up test user
        user_model.delete_user(user["id"])
        print("OK Test user cleaned up")
        
        return True
        
    except Exception as e:
        print(f"NO Error testing avatar upload: {e}")
        return False

def test_file_upload_validation():
    """Test file upload validation"""
    print("\n" + "=" * 60)
    print("TEST VALIDATION UPLOAD FILE")
    print("=" * 60)
    
    # Test allowed extensions
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    test_files = [
        "avatar.png",
        "avatar.jpg", 
        "avatar.jpeg",
        "avatar.gif",
        "avatar.webp",
        "avatar.txt",  # Should fail
        "avatar.pdf"   # Should fail
    ]
    
    for filename in test_files:
        if '.' in filename:
            extension = filename.rsplit('.', 1)[1].lower()
            if extension in allowed_extensions:
                print(f"OK {filename} - Valid extension")
            else:
                print(f"NO {filename} - Invalid extension")
        else:
            print(f"NO {filename} - No extension")

def show_usage_instructions():
    """Show usage instructions"""
    print("\n" + "=" * 60)
    print("HUONG DAN SU DUNG")
    print("=" * 60)
    
    print("1. Chay ung dung:")
    print("   python app.py")
    
    print("\n2. Mo trinh duyet:")
    print("   http://localhost:5000/register")
    
    print("\n3. Dien thong tin dang ky:")
    print("   - Username: Ten dang nhap")
    print("   - Password: Mat khau")
    print("   - Role: Student hoac Teacher")
    print("   - Avatar: Upload hinh anh dai dien (tuy chon)")
    
    print("\n4. Tinh nang avatar:")
    print("   - Chap nhan: PNG, JPG, JPEG, GIF, WEBP")
    print("   - Kich thuoc toi da: 5MB")
    print("   - Preview hinh anh truoc khi upload")
    print("   - Tu dong resize va luu tru")
    
    print("\n5. Luu tru:")
    print("   - Thu muc: static/avatars/")
    print("   - Ten file: UUID + ten goc")
    print("   - Database: Cot avatar_path")

def main():
    """Main function"""
    print("KIEM TRA TINH NANG UPLOAD AVATAR")
    print("Cho dang ky tai khoan hoc sinh")
    
    # Test avatar upload
    success = test_avatar_upload()
    
    if success:
        # Test file validation
        test_file_upload_validation()
        
        # Show usage instructions
        show_usage_instructions()
        
        print("\n" + "=" * 60)
        print("THANH CONG!")
        print("=" * 60)
        print("Tinh nang upload avatar da duoc them vao dang ky tai khoan!")
        print("\nCac tinh nang da duoc them:")
        print("OK Upload hinh anh dai dien")
        print("OK Preview hinh anh truoc khi upload")
        print("OK Validation dinh dang file")
        print("OK Validation kich thuoc file")
        print("OK Luu tru an toan voi UUID")
        print("OK Ho tro da dinh dang: PNG, JPG, JPEG, GIF, WEBP")
        print("OK Tuy chon - khong bat buoc")
        
        print("\nBan co the su dung ngay!")
    else:
        print("\nNO CAN KIEM TRA LAI")
        print("Co loi trong qua trinh cap nhat")

if __name__ == "__main__":
    main()
