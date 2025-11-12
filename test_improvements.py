#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test nhanh để kiểm tra các cải tiến
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

def test_voice_synthesis():
    """Test giọng nói"""
    print("🎤 Testing voice synthesis...")
    
    try:
        from services.doc_video_service import synth_voice
        
        # Tạo file tạm
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_file.close()
        
        test_text = "Xin chào! Đây là test giọng người thật."
        duration = synth_voice(test_text, temp_file.name)
        
        print(f"✅ Voice synthesis completed: {duration:.1f}s")
        print(f"   File: {temp_file.name}")
        
        # Xóa file tạm
        try:
            os.unlink(temp_file.name)
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"❌ Voice synthesis failed: {e}")
        return False

def test_gemini_analysis():
    """Test phân tích Gemini"""
    print("\n🤖 Testing Gemini analysis...")
    
    try:
        from ai_gemini import extract_main_content_from_document
        
        sample_text = """
        Machine Learning là một nhánh của trí tuệ nhân tạo tập trung vào việc phát triển các thuật toán cho phép máy tính học từ dữ liệu.
        
        Có ba loại chính:
        1. Supervised Learning - học có giám sát
        2. Unsupervised Learning - học không giám sát  
        3. Reinforcement Learning - học tăng cường
        
        Deep Learning sử dụng neural networks với nhiều lớp để học các pattern phức tạp.
        """
        
        result = extract_main_content_from_document(sample_text)
        
        if result:
            print("✅ Gemini analysis successful!")
            print(f"   Main topic: {result.get('main_topic', 'N/A')}")
            print(f"   Core concepts: {len(result.get('core_concepts', []))}")
            print(f"   Slides: {len(result.get('slides', []))}")
            return True
        else:
            print("❌ Gemini analysis returned None")
            return False
            
    except Exception as e:
        print(f"❌ Gemini analysis failed: {e}")
        return False

def test_image_keywords():
    """Test tạo từ khóa hình ảnh"""
    print("\n🖼️ Testing image keywords...")
    
    try:
        from services.doc_video_service import _build_image_queries_from_slide
        
        # Tạo slide object giả
        class MockSlide:
            def __init__(self):
                self.title = "Machine Learning và Deep Learning"
                self.content = "Machine Learning là một nhánh của AI tập trung vào việc phát triển thuật toán học từ dữ liệu."
                self.key_points = ["Supervised Learning", "Unsupervised Learning", "Neural Networks"]
        
        slide = MockSlide()
        keywords = _build_image_queries_from_slide(slide)
        
        print("✅ Image keywords generated!")
        print(f"   Keywords: {keywords}")
        return True
        
    except Exception as e:
        print(f"❌ Image keywords failed: {e}")
        return False

def main():
    """Hàm main"""
    print("🚀 Test nhanh các cải tiến")
    print("=" * 40)
    
    voice_ok = test_voice_synthesis()
    gemini_ok = test_gemini_analysis()
    image_ok = test_image_keywords()
    
    print("\n📊 Kết quả test:")
    print(f"   Voice synthesis: {'✅ OK' if voice_ok else '❌ Failed'}")
    print(f"   Gemini analysis: {'✅ OK' if gemini_ok else '❌ Failed'}")
    print(f"   Image keywords: {'✅ OK' if image_ok else '❌ Failed'}")
    
    if voice_ok and gemini_ok and image_ok:
        print("\n🎉 Tất cả test đều thành công!")
        print("   Các cải tiến đã hoạt động đúng.")
    else:
        print("\n⚠️ Một số test thất bại:")
        if not voice_ok:
            print("   - Kiểm tra cấu hình ElevenLabs")
        if not gemini_ok:
            print("   - Kiểm tra cấu hình Gemini API")
        if not image_ok:
            print("   - Kiểm tra lỗi trong code")

if __name__ == "__main__":
    main()
