#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test LunaAI integration
"""

import os
import sys
import tempfile
from pathlib import Path

# Thêm thư mục gốc vào Python path
sys.path.append(str(Path(__file__).parent))

# Load biến môi trường từ file .env
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def test_luna_ai_config():
    """Test cấu hình LunaAI"""
    print("🔍 Testing LunaAI configuration...")
    
    try:
        from services.luna_ai_service import is_luna_ai_available, luna_ai_service
        
        if is_luna_ai_available():
            print("✅ LunaAI API key configured")
            
            # Test generate image
            test_prompt = "Professional educational illustration about machine learning, realistic, detailed"
            print(f"🎨 Testing image generation: {test_prompt[:50]}...")
            
            result = luna_ai_service.generate_image(test_prompt, style="educational")
            
            if result and result.get("success"):
                print("✅ LunaAI image generation successful!")
                print(f"   File: {result.get('file_path')}")
                print(f"   Style: {result.get('style')}")
                return True
            else:
                print("❌ LunaAI image generation failed")
                return False
        else:
            print("❌ LunaAI API key not configured")
            print("   Please add LUNA_AI_KEY to your .env file")
            return False
            
    except Exception as e:
        print(f"❌ LunaAI test error: {e}")
        return False

def test_luna_video_generation():
    """Test tạo video với LunaAI"""
    print("\n🎬 Testing LunaAI video generation...")
    
    # Tạo tài liệu mẫu
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
    
    # Tạo file tạm
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(sample_content)
    temp_file.close()
    
    try:
        from services.doc_video_service import make_luna_lecture_video
        
        # Tạo thư mục output
        output_dir = "test_luna_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"📄 Created sample document: {temp_file.name}")
        print("🎬 Generating video with LunaAI...")
        
        result = make_luna_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Machine Learning với LunaAI"
        )
        
        if result:
            print("✅ LunaAI video generation successful!")
            print(f"   Video: {result['video_path']}")
            print(f"   Caption: {result['caption_path']}")
            print(f"   Script length: {len(result['script_text'])} characters")
            
            lecture_info = result.get('lecture_info', {})
            print(f"   Title: {lecture_info.get('title', 'N/A')}")
            print(f"   Slides: {lecture_info.get('total_slides', 'N/A')}")
            print(f"   Duration: {lecture_info.get('total_duration_seconds', 'N/A'):.1f}s")
            print(f"   Image generator: {lecture_info.get('image_generator', 'N/A')}")
            
            return True
        else:
            print("❌ LunaAI video generation failed")
            return False
            
    except Exception as e:
        print(f"❌ LunaAI video generation error: {e}")
        return False
    
    finally:
        # Xóa file tạm
        try:
            os.unlink(temp_file.name)
        except:
            pass

def test_content_analysis():
    """Test phân tích nội dung cho LunaAI"""
    print("\n🧠 Testing content analysis for LunaAI...")
    
    try:
        from services.luna_ai_service import analyze_content_for_luna_images
        
        sample_content = """
        Machine Learning là một nhánh của AI tập trung vào việc phát triển thuật toán học từ dữ liệu.
        Có ba loại chính: Supervised Learning, Unsupervised Learning, và Reinforcement Learning.
        Deep Learning sử dụng neural networks với nhiều lớp để học pattern phức tạp.
        """
        
        prompts = analyze_content_for_luna_images(sample_content)
        
        if prompts:
            print("✅ Content analysis successful!")
            print("   Generated prompts:")
            for i, prompt in enumerate(prompts, 1):
                print(f"   {i}. {prompt}")
            return True
        else:
            print("❌ Content analysis failed")
            return False
            
    except Exception as e:
        print(f"❌ Content analysis error: {e}")
        return False

def main():
    """Hàm main"""
    print("🚀 Testing LunaAI Integration")
    print("=" * 50)
    
    config_ok = test_luna_ai_config()
    analysis_ok = test_content_analysis()
    video_ok = test_luna_video_generation()
    
    print("\n📊 Test Results:")
    print(f"   LunaAI Config: {'✅ OK' if config_ok else '❌ Failed'}")
    print(f"   Content Analysis: {'✅ OK' if analysis_ok else '❌ Failed'}")
    print(f"   Video Generation: {'✅ OK' if video_ok else '❌ Failed'}")
    
    if config_ok and analysis_ok and video_ok:
        print("\n🎉 All LunaAI tests passed!")
        print("   LunaAI is ready for video generation with realistic images")
    else:
        print("\n⚠️ Some tests failed:")
        if not config_ok:
            print("   - Check LUNA_AI_KEY configuration")
        if not analysis_ok:
            print("   - Check Gemini API for content analysis")
        if not video_ok:
            print("   - Check LunaAI API and dependencies")

if __name__ == "__main__":
    main()
