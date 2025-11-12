#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Smart Image Generation Service
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Load environment variables
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def test_alternative_image_service():
    """Test alternative image service"""
    print("Testing Alternative Image Service...")
    
    try:
        from services.alternative_image_service import is_alternative_image_available, alternative_image_service
        
        if is_alternative_image_available():
            print("SUCCESS: Alternative image service available")
            
            # Test simple generation
            result = alternative_image_service.generate_image("machine learning technology", style="educational")
            
            if result and result.get("success"):
                print("SUCCESS: Image generation worked!")
                print(f"Service: {result.get('service', 'Unknown')}")
                print(f"Source: {result.get('source', 'Unknown')}")
                return True
            else:
                print("ERROR: Image generation failed")
                return False
        else:
            print("ERROR: Alternative image service not available")
            return False
            
    except Exception as e:
        print(f"ERROR: Alternative image service error: {e}")
        return False

def test_smart_video_generation():
    """Test smart video generation"""
    print("\nTesting Smart Video Generation...")
    
    # Create sample document
    sample_content = """
    # Machine Learning và Deep Learning

    ## Giới thiệu
    Machine Learning là một nhánh của trí tuệ nhân tạo tập trung vào việc phát triển các thuật toán cho phép máy tính học từ dữ liệu.

    ## Các loại Machine Learning

    ### 1. Supervised Learning
    Supervised learning sử dụng dữ liệu đã được gắn nhãn để huấn luyện mô hình.

    **Ví dụ:**
    - Phân loại email spam
    - Dự đoán giá nhà
    - Nhận dạng hình ảnh

    ### 2. Unsupervised Learning
    Unsupervised learning tìm kiếm các pattern ẩn trong dữ liệu không có nhãn.

    **Ví dụ:**
    - Phân nhóm khách hàng
    - Phát hiện anomaly
    - Giảm chiều dữ liệu

    ### 3. Deep Learning
    Deep Learning sử dụng Neural Networks với nhiều lớp để học các pattern phức tạp.

    **Ứng dụng:**
    - Computer Vision
    - Natural Language Processing
    - Speech Recognition

    ## Kết luận
    Machine Learning và Deep Learning đang thay đổi cách chúng ta giải quyết các vấn đề phức tạp.
    """
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(sample_content)
    temp_file.close()
    
    try:
        from services.doc_video_service import make_smart_lecture_video
        
        # Create output directory
        output_dir = "test_smart_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating video with Smart Image Generation...")
        
        result = make_smart_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Machine Learning với Smart Images"
        )
        
        if result:
            print("SUCCESS: Smart video generation successful!")
            print(f"Video: {result['video_path']}")
            print(f"Caption: {result['caption_path']}")
            print(f"Script length: {len(result['script_text'])} characters")
            
            lecture_info = result.get('lecture_info', {})
            print(f"Title: {lecture_info.get('title', 'N/A')}")
            print(f"Slides: {lecture_info.get('total_slides', 'N/A')}")
            print(f"Duration: {lecture_info.get('total_duration_seconds', 'N/A'):.1f}s")
            print(f"Image generator: {lecture_info.get('image_generator', 'N/A')}")
            
            return True
        else:
            print("ERROR: Smart video generation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Smart video generation error: {e}")
        return False
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def test_image_services_status():
    """Test status of all image services"""
    print("\nTesting Image Services Status...")
    
    # Test LunaAI
    try:
        from services.luna_ai_service import is_luna_ai_available
        luna_ok = is_luna_ai_available()
        print(f"LunaAI: {'Available' if luna_ok else 'Not Available'}")
    except Exception as e:
        print(f"LunaAI: Error - {e}")
        luna_ok = False
    
    # Test Alternative Services
    try:
        from services.alternative_image_service import is_alternative_image_available
        alt_ok = is_alternative_image_available()
        print(f"Alternative Services: {'Available' if alt_ok else 'Not Available'}")
    except Exception as e:
        print(f"Alternative Services: Error - {e}")
        alt_ok = False
    
    # Test Gemini
    try:
        from ai_gemini import _ensure
        gemini_ok = _ensure()
        print(f"Gemini: {'Available' if gemini_ok else 'Not Available'}")
    except Exception as e:
        print(f"Gemini: Error - {e}")
        gemini_ok = False
    
    # Test ElevenLabs
    try:
        from services.human_voice_service import is_human_voice_available
        voice_ok = is_human_voice_available()
        print(f"ElevenLabs: {'Available' if voice_ok else 'Not Available'}")
    except Exception as e:
        print(f"ElevenLabs: Error - {e}")
        voice_ok = False
    
    return luna_ok, alt_ok, gemini_ok, voice_ok

def main():
    """Main function"""
    print("Smart Image Generation Test")
    print("=" * 40)
    
    # Test service status
    luna_ok, alt_ok, gemini_ok, voice_ok = test_image_services_status()
    
    # Test alternative service
    alt_service_ok = test_alternative_image_service()
    
    # Test smart video generation
    video_ok = test_smart_video_generation()
    
    print("\nResults:")
    print(f"  LunaAI: {'OK' if luna_ok else 'FAILED'}")
    print(f"  Alternative Services: {'OK' if alt_ok else 'FAILED'}")
    print(f"  Alternative Service Test: {'OK' if alt_service_ok else 'FAILED'}")
    print(f"  Gemini: {'OK' if gemini_ok else 'FAILED'}")
    print(f"  ElevenLabs: {'OK' if voice_ok else 'FAILED'}")
    print(f"  Smart Video Generation: {'OK' if video_ok else 'FAILED'}")
    
    if video_ok:
        print("\nSUCCESS: Smart video generation is working!")
        print("The system will use the best available image service:")
        if luna_ok:
            print("  - LunaAI (if working)")
        if alt_ok:
            print("  - Alternative Services (Pexels, Unsplash, OpenAI DALL-E)")
        print("  - Fallback to standard method if needed")
    else:
        print("\nERROR: Smart video generation failed")
        print("Check the error messages above for details")

if __name__ == "__main__":
    main()
