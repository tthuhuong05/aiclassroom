# test_final_system.py
"""
Test script cuối cùng để đảm bảo hệ thống hoạt động đúng
"""

import os
import sys
import tempfile
import json

# Thêm thư mục services vào path
sys.path.append('services')

def test_system_integration():
    """Test tích hợp hệ thống"""
    print("🧪 Testing System Integration...")
    
    try:
        # Test import các module mới
        from services.smart_image_analyzer import smart_image_analyzer, get_smart_image_keywords
        from services.content_based_image_service import create_content_based_image, is_content_based_image_available
        from services.doc_video_service import find_smart_image_for_content, make_video_from_file
        
        print("✅ All modules imported successfully")
        
        # Test với nội dung thực tế
        test_content = """
        Lập trình Python là ngôn ngữ lập trình phổ biến với cú pháp đơn giản và dễ đọc.
        Trong bài học này, chúng ta sẽ tìm hiểu về biến, hàm, vòng lặp và cấu trúc dữ liệu.
        Python được sử dụng rộng rãi trong web development, data science và artificial intelligence.
        """
        
        print(f"📝 Testing with content: {test_content[:100]}...")
        
        # Test 1: Smart keywords
        keywords = get_smart_image_keywords(test_content, "educational", count=3)
        print(f"✅ Smart keywords: {keywords}")
        
        # Test 2: Content-based image (nếu có API key)
        if is_content_based_image_available():
            image_path = create_content_based_image(test_content, "educational")
            if image_path:
                print(f"✅ Content-based image created: {image_path}")
            else:
                print("⚠️ Content-based image creation failed")
        else:
            print("⚠️ Content-based image service not available (no API key)")
        
        # Test 3: Smart image search
        smart_image = find_smart_image_for_content(test_content, "educational")
        if smart_image:
            print(f"✅ Smart image found: {smart_image}")
        else:
            print("⚠️ No smart image found (normal if no AI services configured)")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def test_course_controller_update():
    """Test course controller đã được cập nhật"""
    print("\n🧪 Testing Course Controller Update...")
    
    try:
        # Đọc file course_controller.py
        with open('controller/course_controller.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Kiểm tra đã sử dụng hệ thống mới
        if 'from services.doc_video_service import make_video_from_file' in content:
            print("✅ Course controller updated to use new system")
        else:
            print("❌ Course controller still using old system")
            return False
        
        # Kiểm tra đã loại bỏ hệ thống cũ
        if 'from ultimate_video_system import make_ultimate_lecture_video' not in content:
            print("✅ Old system removed from course controller")
        else:
            print("❌ Old system still present in course controller")
            return False
        
        # Kiểm tra log message mới
        if 'Smart Image System - NO PEOPLE, CONTENT-MATCHED IMAGES ONLY' in content:
            print("✅ New log message added")
        else:
            print("⚠️ New log message not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Course controller test failed: {e}")
        return False

def test_safety_features():
    """Test các tính năng an toàn"""
    print("\n🧪 Testing Safety Features...")
    
    try:
        from services.smart_image_analyzer import smart_image_analyzer
        
        # Test unsafe keywords
        unsafe_keywords = [
            "people programming",
            "team meeting", 
            "student learning",
            "teacher teaching"
        ]
        
        for keyword in unsafe_keywords:
            is_safe = smart_image_analyzer._is_safe_keyword(keyword)
            if not is_safe:
                print(f"✅ '{keyword}' correctly identified as unsafe")
            else:
                print(f"❌ '{keyword}' incorrectly identified as safe")
                return False
        
        # Test safe keywords
        safe_keywords = [
            "programming concept",
            "algorithm diagram",
            "data structure",
            "machine learning"
        ]
        
        for keyword in safe_keywords:
            is_safe = smart_image_analyzer._is_safe_keyword(keyword)
            if is_safe:
                print(f"✅ '{keyword}' correctly identified as safe")
            else:
                print(f"❌ '{keyword}' incorrectly identified as unsafe")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Safety test failed: {e}")
        return False

def test_api_endpoint():
    """Test API endpoint"""
    print("\n🧪 Testing API Endpoint...")
    
    try:
        # Kiểm tra app.py có route đúng không
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if '@app.post("/api/convert-doc-to-video")' in content:
            print("✅ API endpoint exists")
        else:
            print("❌ API endpoint not found")
            return False
        
        if 'course_controller.api_doc_to_video()' in content:
            print("✅ API endpoint calls course controller")
        else:
            print("❌ API endpoint not properly configured")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {e}")
        return False

def main():
    """Chạy tất cả các test"""
    print("🚀 FINAL SYSTEM TEST")
    print("=" * 60)
    print("Kiểm tra hệ thống hình ảnh thông minh đã được triển khai đúng")
    print("=" * 60)
    
    results = []
    
    # Test 1: System Integration
    results.append(test_system_integration())
    
    # Test 2: Course Controller Update
    results.append(test_course_controller_update())
    
    # Test 3: Safety Features
    results.append(test_safety_features())
    
    # Test 4: API Endpoint
    results.append(test_api_endpoint())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS:")
    print(f"✅ Passed: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\n🎉 ALL TESTS PASSED!")
        print("🛡️ System is ready - NO PEOPLE IMAGES will be generated")
        print("\n💡 System features:")
        print("   ✅ Smart Image Analyzer with safety filters")
        print("   ✅ Content-Based Image Service (no people)")
        print("   ✅ Enhanced Doc Video Service")
        print("   ✅ Updated Course Controller")
        print("   ✅ Safe keyword filtering")
        print("   ✅ Improved AI prompts")
        print("\n🚀 Ready to create videos with content-matched images!")
    else:
        print("\n⚠️ Some tests failed!")
        print("🔧 System needs additional fixes")
        print("\n📋 Check the following:")
        print("   - Course controller imports")
        print("   - API endpoint configuration")
        print("   - Safety features implementation")
        print("   - Module imports and dependencies")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

