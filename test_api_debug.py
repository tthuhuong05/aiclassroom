# test_api_debug.py
"""
Test script để debug API endpoint
"""

import os
import sys
import tempfile
import json

# Thêm thư mục services vào path
sys.path.append('services')

def test_doc_video_service():
    """Test doc_video_service với file thực tế"""
    print("Testing doc_video_service...")
    
    try:
        from services.doc_video_service import make_video_from_file
        
        # Tạo file test đơn giản
        test_content = """
        Lập trình Python là ngôn ngữ lập trình phổ biến với cú pháp đơn giản và dễ đọc.
        Trong bài học này, chúng ta sẽ tìm hiểu về biến, hàm, vòng lặp và cấu trúc dữ liệu.
        Python được sử dụng rộng rãi trong web development, data science và artificial intelligence.
        """
        
        # Tạo file text test
        test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        test_file.write(test_content)
        test_file.close()
        
        print(f"Created test file: {test_file.name}")
        
        # Tạo thư mục output
        output_dir = tempfile.mkdtemp()
        print(f"Output directory: {output_dir}")
        
        # Test tạo video
        print("Creating video...")
        result = make_video_from_file(test_file.name, output_dir, title="Test Video")
        
        print(f"Video created successfully!")
        print(f"   Video path: {result['video_path']}")
        print(f"   Caption path: {result['caption_path']}")
        print(f"   Script text: {result['script_text'][:100]}...")
        
        # Cleanup
        os.unlink(test_file.name)
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_smart_image_system():
    """Test hệ thống hình ảnh thông minh"""
    print("\nTesting Smart Image System...")
    
    try:
        from services.smart_image_analyzer import get_smart_image_keywords
        from services.content_based_image_service import create_content_based_image, is_content_based_image_available
        
        test_content = "Lập trình Python với các khái niệm về biến, hàm và vòng lặp"
        
        # Test smart keywords
        keywords = get_smart_image_keywords(test_content, "educational", count=3)
        print(f"Smart keywords: {keywords}")
        
        # Test content-based image (nếu có API key)
        if is_content_based_image_available():
            image_path = create_content_based_image(test_content, "educational")
            if image_path:
                print(f"Content-based image created: {image_path}")
            else:
                print("Content-based image creation failed")
        else:
            print("Content-based image service not available (no API key)")
        
        return True
        
    except Exception as e:
        print(f"Smart image system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_processing():
    """Test xử lý file"""
    print("\nTesting File Processing...")
    
    try:
        from services.doc_video_service import extract_text_from_file, clean_text, chunk_text
        
        # Tạo file test
        test_content = """
        Lập trình Python là ngôn ngữ lập trình phổ biến với cú pháp đơn giản và dễ đọc.
        
        Trong bài học này, chúng ta sẽ tìm hiểu về:
        1. Biến và kiểu dữ liệu
        2. Hàm và tham số
        3. Vòng lặp và điều kiện
        4. Cấu trúc dữ liệu
        
        Python được sử dụng rộng rãi trong web development, data science và artificial intelligence.
        """
        
        test_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        test_file.write(test_content)
        test_file.close()
        
        # Test extract text
        extracted_text = extract_text_from_file(test_file.name)
        print(f"Text extracted: {len(extracted_text)} characters")
        
        # Test clean text
        cleaned_text = clean_text(extracted_text)
        print(f"Text cleaned: {len(cleaned_text)} characters")
        
        # Test chunk text
        chunks = chunk_text(cleaned_text, max_chars=500)
        print(f"Text chunked: {len(chunks)} chunks")
        
        # Cleanup
        os.unlink(test_file.name)
        
        return True
        
    except Exception as e:
        print(f"File processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Chạy tất cả các test"""
    print("API DEBUG TESTS")
    print("=" * 50)
    
    results = []
    
    # Test 1: File Processing
    results.append(test_file_processing())
    
    # Test 2: Smart Image System
    results.append(test_smart_image_system())
    
    # Test 3: Doc Video Service
    results.append(test_doc_video_service())
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    print(f"Passed: {sum(results)}")
    print(f"Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("\nAll tests passed!")
        print("API should work correctly now")
    else:
        print("\nSome tests failed!")
        print("Check the error messages above")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
