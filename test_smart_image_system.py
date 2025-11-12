# test_smart_image_system.py
"""
Test script để kiểm tra hệ thống hình ảnh thông minh
"""

import os
import sys

# Thêm thư mục services vào path
sys.path.append('services')

def test_smart_image_analyzer():
    """Test Smart Image Analyzer"""
    print("🧪 Testing Smart Image Analyzer...")
    
    try:
        from smart_image_analyzer import analyze_content_for_smart_images, get_smart_image_keywords
        
        # Test content
        test_content = """
        Lập trình Python là một ngôn ngữ lập trình phổ biến và dễ học. 
        Python được sử dụng rộng rãi trong phát triển web, phân tích dữ liệu, 
        trí tuệ nhân tạo và nhiều lĩnh vực khác. Trong bài học này, chúng ta sẽ 
        tìm hiểu về các khái niệm cơ bản của Python như biến, hàm, vòng lặp và cấu trúc dữ liệu.
        """
        
        # Test phân tích nội dung
        print("📝 Analyzing content...")
        analysis = analyze_content_for_smart_images(test_content, "educational")
        print(f"✅ Analysis result: {analysis}")
        
        # Test tạo từ khóa
        print("🔑 Generating keywords...")
        keywords = get_smart_image_keywords(test_content, "educational", count=3)
        print(f"✅ Keywords: {keywords}")
        
        return True
        
    except Exception as e:
        print(f"❌ Smart Image Analyzer test failed: {e}")
        return False

def test_content_based_image_service():
    """Test Content-Based Image Service"""
    print("🧪 Testing Content-Based Image Service...")
    
    try:
        from content_based_image_service import create_content_based_image, is_content_based_image_available
        
        # Test content
        test_content = """
        Machine Learning là một nhánh của trí tuệ nhân tạo tập trung vào việc 
        phát triển các thuật toán có thể học từ dữ liệu. Các thuật toán này 
        có thể nhận dạng mẫu, đưa ra dự đoán và cải thiện hiệu suất theo thời gian.
        """
        
        # Test tạo hình ảnh
        print("🎨 Creating content-based image...")
        if is_content_based_image_available():
            image_path = create_content_based_image(test_content, "educational")
            if image_path and os.path.exists(image_path):
                print(f"✅ Created image: {image_path}")
                return True
            else:
                print("⚠️ Image creation failed")
                return False
        else:
            print("⚠️ Content-based image service not available (missing API key)")
            return False
        
    except Exception as e:
        print(f"❌ Content-Based Image Service test failed: {e}")
        return False

def test_doc_video_service():
    """Test Doc Video Service với hình ảnh thông minh"""
    print("🧪 Testing Doc Video Service with Smart Images...")
    
    try:
        from doc_video_service import find_smart_image_for_content
        
        # Test content
        test_content = """
        Blockchain là một công nghệ lưu trữ dữ liệu phân tán, trong đó mỗi khối 
        chứa thông tin về giao dịch và được liên kết với khối trước đó. 
        Điều này tạo ra một chuỗi khối không thể thay đổi và minh bạch.
        """
        
        # Test tìm hình ảnh thông minh
        print("🔍 Finding smart image...")
        image_path = find_smart_image_for_content(test_content, "educational")
        if image_path and os.path.exists(image_path):
            print(f"✅ Found smart image: {image_path}")
            return True
        else:
            print("⚠️ No smart image found")
            return False
        
    except Exception as e:
        print(f"❌ Doc Video Service test failed: {e}")
        return False

def main():
    """Chạy tất cả các test"""
    print("🚀 Starting Smart Image System Tests...")
    print("=" * 50)
    
    results = []
    
    # Test 1: Smart Image Analyzer
    results.append(test_smart_image_analyzer())
    print()
    
    # Test 2: Content-Based Image Service
    results.append(test_content_based_image_service())
    print()
    
    # Test 3: Doc Video Service
    results.append(test_doc_video_service())
    print()
    
    # Summary
    print("=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Passed: {sum(results)}")
    print(f"❌ Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 All tests passed! Smart image system is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the error messages above.")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

