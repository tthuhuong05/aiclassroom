#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test KIE AI Integration
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

def test_kie_ai_service():
    """Test KIE AI service"""
    print("Testing KIE AI Service...")
    
    try:
        from services.kie_ai_service import is_kie_ai_available, kie_ai_service
        
        if is_kie_ai_available():
            print("SUCCESS: KIE AI service available")
            
            # Test simple generation
            result = kie_ai_service.generate_image("machine learning technology", style="educational")
            
            if result and result.get("success"):
                print("SUCCESS: Image generation worked!")
                print(f"Service: {result.get('service', 'Unknown')}")
                print(f"Source: {result.get('source', 'Unknown')}")
                return True
            else:
                print("ERROR: Image generation failed")
                print(f"Error: {result.get('error', 'Unknown error')}")
                return False
        else:
            print("ERROR: KIE AI service not available")
            return False
            
    except Exception as e:
        print(f"ERROR: KIE AI service error: {e}")
        return False

def test_kie_video_generation():
    """Test KIE AI video generation"""
    print("\nTesting KIE AI Video Generation...")
    
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
        from services.doc_video_service import make_kie_lecture_video
        
        # Create output directory
        output_dir = "test_kie_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating video with KIE AI...")
        
        result = make_kie_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Machine Learning với KIE AI"
        )
        
        if result:
            print("SUCCESS: KIE AI video generation successful!")
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
            print("ERROR: KIE AI video generation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: KIE AI video generation error: {e}")
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
    
    # Test KIE AI
    try:
        from services.kie_ai_service import is_kie_ai_available
        kie_ok = is_kie_ai_available()
        print(f"KIE AI: {'Available' if kie_ok else 'Not Available'}")
    except Exception as e:
        print(f"KIE AI: Error - {e}")
        kie_ok = False
    
    # Test Working Services
    try:
        from services.working_image_service import is_working_image_available
        working_ok = is_working_image_available()
        print(f"Working Services: {'Available' if working_ok else 'Not Available'}")
    except Exception as e:
        print(f"Working Services: Error - {e}")
        working_ok = False
    
    # Test LunaAI
    try:
        from services.luna_ai_service import is_luna_ai_available
        luna_ok = is_luna_ai_available()
        print(f"LunaAI: {'Available' if luna_ok else 'Not Available'}")
    except Exception as e:
        print(f"LunaAI: Error - {e}")
        luna_ok = False
    
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
    
    return kie_ok, working_ok, luna_ok, gemini_ok, voice_ok

def main():
    """Main function"""
    print("KIE AI Integration Test")
    print("=" * 40)
    
    # Test service status
    kie_ok, working_ok, luna_ok, gemini_ok, voice_ok = test_image_services_status()
    
    # Test KIE AI service
    kie_service_ok = test_kie_ai_service()
    
    # Test KIE AI video generation
    video_ok = test_kie_video_generation()
    
    print("\nResults:")
    print(f"  KIE AI: {'OK' if kie_ok else 'FAILED'}")
    print(f"  KIE AI Service Test: {'OK' if kie_service_ok else 'FAILED'}")
    print(f"  Working Services: {'OK' if working_ok else 'FAILED'}")
    print(f"  LunaAI: {'OK' if luna_ok else 'FAILED'}")
    print(f"  Gemini: {'OK' if gemini_ok else 'FAILED'}")
    print(f"  ElevenLabs: {'OK' if voice_ok else 'FAILED'}")
    print(f"  KIE AI Video Generation: {'OK' if video_ok else 'FAILED'}")
    
    if video_ok:
        print("\nSUCCESS: KIE AI video generation is working!")
        print("The system will use KIE AI for realistic image generation:")
        print("  - KIE AI creates realistic images matching content")
        print("  - AI Gemini analyzes content deeply")
        print("  - ElevenLabs provides natural human voice")
        print("  - Fallback to Working services if needed")
    else:
        print("\nERROR: KIE AI video generation failed")
        print("Check the error messages above for details")
        
        if kie_service_ok:
            print("\nKIE AI service works but video generation failed.")
            print("This might be due to:")
            print("  - Gemini model issues")
            print("  - Encoding problems")
            print("  - Video rendering issues")
        else:
            print("\nKIE AI service is not working.")
            print("Check:")
            print("  - API key is correct")
            print("  - KIE AI endpoints are accessible")
            print("  - Network connection")

if __name__ == "__main__":
    main()
