# test_simple_api.py
"""
Simple test script để debug API endpoint
"""

import os
import sys
import tempfile

# Thêm thư mục services vào path
sys.path.append('services')

def test_simple_video_creation():
    """Test tạo video đơn giản"""
    print("Testing simple video creation...")
    
    try:
        from services.doc_video_service import make_video_from_file
        
        # Tạo file test đơn giản với tiếng Anh
        test_content = """
        Python programming is a popular programming language with simple and readable syntax.
        In this lesson, we will learn about variables, functions, loops and data structures.
        Python is widely used in web development, data science and artificial intelligence.
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
        print(f"   Script text length: {len(result['script_text'])}")
        
        # Cleanup
        os.unlink(test_file.name)
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoint():
    """Test API endpoint trực tiếp"""
    print("\nTesting API endpoint...")
    
    try:
        # Test import course_controller
        from controller.course_controller import CourseController
        
        controller = CourseController()
        print("CourseController imported successfully")
        
        # Test method exists
        if hasattr(controller, 'api_doc_to_video'):
            print("api_doc_to_video method exists")
        else:
            print("api_doc_to_video method not found")
            return False
        
        return True
        
    except Exception as e:
        print(f"API endpoint test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Chạy tất cả các test"""
    print("SIMPLE API TESTS")
    print("=" * 50)
    
    results = []
    
    # Test 1: API Endpoint
    results.append(test_api_endpoint())
    
    # Test 2: Simple Video Creation
    results.append(test_simple_video_creation())
    
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

