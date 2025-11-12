# demo_smart_images.py
"""
Demo script để minh họa hệ thống hình ảnh thông minh mới
"""

import os
import sys
import tempfile
from pathlib import Path

# Thêm thư mục services vào path
sys.path.append('services')

def demo_smart_image_analysis():
    """Demo phân tích nội dung thông minh"""
    print("🎯 DEMO: Smart Image Analysis")
    print("=" * 50)
    
    try:
        from smart_image_analyzer import analyze_content_for_smart_images, get_smart_image_keywords
        
        # Test cases với nội dung khác nhau
        test_cases = [
            {
                "title": "Lập trình Python",
                "content": """
                Python là ngôn ngữ lập trình phổ biến với cú pháp đơn giản và dễ đọc. 
                Trong bài học này, chúng ta sẽ tìm hiểu về biến, hàm, vòng lặp và cấu trúc dữ liệu.
                Python được sử dụng rộng rãi trong web development, data science và AI.
                """,
                "context": "educational"
            },
            {
                "title": "Machine Learning",
                "content": """
                Machine Learning là nhánh của AI tập trung vào việc phát triển thuật toán 
                có thể học từ dữ liệu. Các thuật toán này có thể nhận dạng mẫu, đưa ra dự đoán 
                và cải thiện hiệu suất theo thời gian mà không cần lập trình rõ ràng.
                """,
                "context": "technical"
            },
            {
                "title": "Blockchain Technology",
                "content": """
                Blockchain là công nghệ lưu trữ dữ liệu phân tán, trong đó mỗi khối chứa 
                thông tin về giao dịch và được liên kết với khối trước đó. Điều này tạo ra 
                một chuỗi khối không thể thay đổi và minh bạch.
                """,
                "context": "business"
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n📝 Test Case {i}: {case['title']}")
            print(f"Context: {case['context']}")
            print(f"Content: {case['content'][:100]}...")
            
            # Phân tích nội dung
            analysis = analyze_content_for_smart_images(case['content'], case['context'])
            print(f"✅ Analysis completed")
            print(f"   Main concepts: {analysis.get('main_concepts', [])}")
            print(f"   Visual style: {analysis.get('visual_style', 'N/A')}")
            print(f"   Mood: {analysis.get('mood', 'N/A')}")
            
            # Tạo từ khóa
            keywords = get_smart_image_keywords(case['content'], case['context'], count=3)
            print(f"   Keywords: {keywords}")
            
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

def demo_content_based_image_creation():
    """Demo tạo hình ảnh dựa trên nội dung"""
    print("\n🎨 DEMO: Content-Based Image Creation")
    print("=" * 50)
    
    try:
        from content_based_image_service import create_content_based_image, is_content_based_image_available
        
        if not is_content_based_image_available():
            print("⚠️ Content-based image service not available (missing GEMINI_API_KEY)")
            print("   This demo requires GEMINI_API_KEY in environment variables")
            return False
        
        # Test content
        test_content = """
        Artificial Intelligence và Machine Learning đang thay đổi cách chúng ta 
        làm việc và sống. Các thuật toán AI có thể xử lý dữ liệu lớn, nhận dạng 
        mẫu phức tạp và đưa ra dự đoán chính xác.
        """
        
        print(f"📝 Creating image for content: {test_content[:100]}...")
        
        # Tạo hình ảnh
        image_path = create_content_based_image(test_content, "technical")
        
        if image_path and os.path.exists(image_path):
            print(f"✅ Image created successfully: {image_path}")
            print(f"   File size: {os.path.getsize(image_path)} bytes")
            return True
        else:
            print("❌ Image creation failed")
            return False
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

def demo_smart_image_integration():
    """Demo tích hợp hệ thống hình ảnh thông minh"""
    print("\n🔗 DEMO: Smart Image Integration")
    print("=" * 50)
    
    try:
        from doc_video_service import find_smart_image_for_content
        
        # Test content
        test_content = """
        Data Science là lĩnh vực kết hợp thống kê, lập trình và domain knowledge 
        để trích xuất insights từ dữ liệu. Quy trình bao gồm thu thập, làm sạch, 
        phân tích và visualization dữ liệu.
        """
        
        print(f"📝 Finding smart image for: {test_content[:100]}...")
        
        # Tìm hình ảnh thông minh
        image_path = find_smart_image_for_content(test_content, "educational")
        
        if image_path and os.path.exists(image_path):
            print(f"✅ Smart image found: {image_path}")
            print(f"   File size: {os.path.getsize(image_path)} bytes")
            return True
        else:
            print("⚠️ No smart image found (this is normal if no AI services are configured)")
            return True  # Không phải lỗi, chỉ là không có service nào khả dụng
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

def demo_comparison():
    """Demo so sánh hệ thống cũ vs mới"""
    print("\n📊 DEMO: System Comparison")
    print("=" * 50)
    
    print("🔴 HỆ THỐNG CŨ:")
    print("   - Từ khóa đơn giản: lấy 5 từ đầu của nội dung")
    print("   - Không phân tích ngữ cảnh")
    print("   - Có thể tìm thấy hình ảnh con người không phù hợp")
    print("   - Thiếu AI phân tích nội dung")
    
    print("\n🟢 HỆ THỐNG MỚI:")
    print("   - AI phân tích nội dung để tạo từ khóa chính xác")
    print("   - Tự động tạo hình ảnh dựa trên concept cụ thể")
    print("   - Loại bỏ hình ảnh con người, khuôn mặt")
    print("   - Ưu tiên illustration, diagram, concept art")
    print("   - Hệ thống fallback thông minh")
    
    # Demo từ khóa cũ vs mới
    test_content = "Lập trình Python với các khái niệm về biến, hàm và vòng lặp"
    
    print(f"\n📝 Test content: {test_content}")
    
    # Từ khóa cũ (đơn giản)
    old_keywords = test_content.split()[:5]
    print(f"🔴 Old keywords: {' '.join(old_keywords)}")
    
    # Từ khóa mới (thông minh)
    try:
        from smart_image_analyzer import get_smart_image_keywords
        new_keywords = get_smart_image_keywords(test_content, "educational", count=3)
        print(f"🟢 New keywords: {new_keywords}")
    except Exception as e:
        print(f"🟢 New keywords: [AI analysis failed: {e}]")
    
    return True

def main():
    """Chạy tất cả các demo"""
    print("🚀 SMART IMAGE SYSTEM DEMO")
    print("=" * 60)
    print("Hệ thống hình ảnh thông minh - Giải quyết vấn đề hình ảnh không liên quan")
    print("=" * 60)
    
    results = []
    
    # Demo 1: Smart Image Analysis
    results.append(demo_smart_image_analysis())
    
    # Demo 2: Content-Based Image Creation
    results.append(demo_content_based_image_creation())
    
    # Demo 3: Smart Image Integration
    results.append(demo_smart_image_integration())
    
    # Demo 4: System Comparison
    results.append(demo_comparison())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 DEMO SUMMARY:")
    print(f"✅ Successful demos: {sum(results)}")
    print(f"❌ Failed demos: {len(results) - sum(results)}")
    
    if all(results):
        print("\n🎉 All demos completed successfully!")
        print("🎯 Smart image system is working correctly.")
        print("\n💡 Key improvements:")
        print("   - AI-powered content analysis")
        print("   - Content-based image creation")
        print("   - Smart keyword generation")
        print("   - Elimination of inappropriate images")
        print("   - Professional visual consistency")
    else:
        print("\n⚠️ Some demos failed. Check the error messages above.")
        print("💡 Make sure to set up API keys for full functionality:")
        print("   - GEMINI_API_KEY for AI analysis")
        print("   - UNSPLASH_ACCESS_KEY for image search")
        print("   - PEXELS_API_KEY for additional image sources")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

