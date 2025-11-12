#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Comparison Test
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_performance_comparison():
    """Compare performance between original and optimized systems"""
    print("=" * 60)
    print("SO SANH HIỆU SUẤT HỆ THỐNG TẠO VIDEO")
    print("=" * 60)
    
    # Create test content
    test_content = """
    # Introduction to Machine Learning
    
    Machine Learning is a subset of artificial intelligence that focuses on algorithms.
    
    ## Key Concepts
    
    ### Supervised Learning
    Uses labeled data to train models.
    
    ### Unsupervised Learning
    Finds patterns in unlabeled data.
    
    ## Applications
    Used in healthcare, finance, and technology.
    
    ## Conclusion
    ML is transforming problem-solving approaches.
    """
    
    # Create test file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(test_content)
    temp_file.close()
    
    print(f"Test file created: {temp_file.name}")
    
    # Test 1: Original system
    print("\n" + "=" * 40)
    print("TEST 1: HỆ THỐNG GỐC")
    print("=" * 40)
    
    try:
        from final_video_system import make_final_lecture_video
        
        start_time = time.time()
        result1 = make_final_lecture_video(temp_file.name, "test_output_original", "Original System Test")
        original_time = time.time() - start_time
        
        print(f"Original system time: {original_time:.1f}s")
        print(f"Video duration: {result1['lecture_info']['total_duration_seconds']:.1f}s")
        print(f"Total slides: {result1['lecture_info']['total_slides']}")
        
    except Exception as e:
        print(f"Original system error: {e}")
        original_time = None
    
    # Test 2: Optimized system
    print("\n" + "=" * 40)
    print("TEST 2: HỆ THỐNG TỐI ƯU")
    print("=" * 40)
    
    try:
        from optimized_video_system import make_fast_lecture_video
        
        start_time = time.time()
        result2 = make_fast_lecture_video(temp_file.name, "test_output_optimized", "Optimized System Test")
        optimized_time = time.time() - start_time
        
        print(f"Optimized system time: {optimized_time:.1f}s")
        print(f"Video duration: {result2['lecture_info']['total_duration_seconds']:.1f}s")
        print(f"Total slides: {result2['lecture_info']['total_slides']}")
        
    except Exception as e:
        print(f"Optimized system error: {e}")
        optimized_time = None
    
    # Comparison
    print("\n" + "=" * 40)
    print("KẾT QUẢ SO SÁNH")
    print("=" * 40)
    
    if original_time and optimized_time:
        improvement = ((original_time - optimized_time) / original_time) * 100
        print(f"Original system: {original_time:.1f}s")
        print(f"Optimized system: {optimized_time:.1f}s")
        print(f"Improvement: {improvement:.1f}% faster")
        
        if improvement > 0:
            print("✅ Optimized system is faster!")
        else:
            print("❌ Original system is faster")
    else:
        print("Cannot compare - one or both systems failed")
    
    # Clean up
    try:
        os.unlink(temp_file.name)
    except:
        pass

def test_individual_components():
    """Test individual components for bottlenecks"""
    print("\n" + "=" * 60)
    print("KIỂM TRA CÁC THÀNH PHẦN RIÊNG LẺ")
    print("=" * 60)
    
    # Test image generation
    print("\n1. Testing image generation...")
    try:
        from optimized_video_system import generate_optimal_image
        
        start_time = time.time()
        img_path = generate_optimal_image(["education", "learning"])
        image_time = time.time() - start_time
        
        print(f"Image generation time: {image_time:.1f}s")
        print(f"Image path: {img_path}")
        
    except Exception as e:
        print(f"Image generation error: {e}")
    
    # Test voice synthesis
    print("\n2. Testing voice synthesis...")
    try:
        from optimized_video_system import synthesize_voice_fast
        
        test_text = "This is a test of voice synthesis speed."
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_audio.close()
        
        start_time = time.time()
        result = synthesize_voice_fast(test_text, temp_audio.name)
        voice_time = time.time() - start_time
        
        print(f"Voice synthesis time: {voice_time:.1f}s")
        print(f"Success: {result.get('success', False)}")
        
        # Clean up
        try:
            os.unlink(temp_audio.name)
        except:
            pass
        
    except Exception as e:
        print(f"Voice synthesis error: {e}")
    
    # Test video rendering
    print("\n3. Testing video rendering...")
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
        
        # Create simple test clips
        temp_dir = tempfile.mkdtemp()
        
        # Create test image
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (1280, 720), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), "Test Video", fill=(0, 0, 0))
        img_path = os.path.join(temp_dir, "test.png")
        img.save(img_path)
        
        start_time = time.time()
        
        # Create video clip
        clip = ImageClip(img_path).set_duration(5.0)
        
        # Render video
        output_path = os.path.join(temp_dir, "test_video.mp4")
        clip.write_videofile(
            output_path, 
            fps=24, 
            codec="libx264", 
            audio_codec="aac",
            verbose=False,
            logger=None
        )
        
        render_time = time.time() - start_time
        print(f"Video rendering time: {render_time:.1f}s")
        
        # Clean up
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass
        
    except Exception as e:
        print(f"Video rendering error: {e}")

def analyze_bottlenecks():
    """Analyze potential bottlenecks"""
    print("\n" + "=" * 60)
    print("PHÂN TÍCH CÁC NÚT THẮT CỔ CHAI")
    print("=" * 60)
    
    bottlenecks = [
        {
            "component": "Image Generation",
            "description": "Tạo hình ảnh từ API (Stability AI, Pexels, Unsplash)",
            "typical_time": "5-15 seconds",
            "optimization": "Cache images, use smaller sizes, parallel requests"
        },
        {
            "component": "Voice Synthesis",
            "description": "Tạo giọng nói từ text (ElevenLabs, pyttsx3)",
            "typical_time": "3-10 seconds",
            "optimization": "Use faster TTS engines, shorter text chunks"
        },
        {
            "component": "Video Rendering",
            "description": "Kết hợp hình ảnh và âm thanh thành video",
            "typical_time": "10-30 seconds",
            "optimization": "Lower quality settings, faster codecs, parallel processing"
        },
        {
            "component": "Content Analysis",
            "description": "Phân tích nội dung tài liệu (Gemini AI)",
            "typical_time": "2-5 seconds",
            "optimization": "Simpler analysis, cached results, faster models"
        },
        {
            "component": "File Processing",
            "description": "Đọc và xử lý file PDF/DOCX",
            "typical_time": "1-3 seconds",
            "optimization": "Faster libraries, parallel processing"
        }
    ]
    
    for i, bottleneck in enumerate(bottlenecks, 1):
        print(f"\n{i}. {bottleneck['component']}")
        print(f"   Description: {bottleneck['description']}")
        print(f"   Typical time: {bottleneck['typical_time']}")
        print(f"   Optimization: {bottleneck['optimization']}")

def main():
    """Main function"""
    print("KIỂM TRA HIỆU SUẤT HỆ THỐNG TẠO VIDEO AI")
    
    # Test performance comparison
    test_performance_comparison()
    
    # Test individual components
    test_individual_components()
    
    # Analyze bottlenecks
    analyze_bottlenecks()
    
    print("\n" + "=" * 60)
    print("KẾT LUẬN VÀ KHUYẾN NGHỊ")
    print("=" * 60)
    
    print("""
    🚀 CÁC CẢI THIỆN ĐÃ THỰC HIỆN:
    
    1. ✅ Optimized Image Generation
       - Sử dụng API nhanh nhất trước
       - Fallback system khi API fail
       - Cache và reuse images
    
    2. ✅ Fast Voice Synthesis
       - ElevenLabs với timeout ngắn
       - Fallback về pyttsx3 (nhanh nhất)
       - Silent audio nếu tất cả fail
    
    3. ✅ Optimized Video Rendering
       - Lower quality settings
       - Faster codecs
       - Parallel processing
    
    4. ✅ Simplified Content Analysis
       - Bỏ qua complex AI analysis
       - Sử dụng simple text processing
       - Faster content extraction
    
    5. ✅ Better Error Handling
       - Graceful fallbacks
       - No crashes on API failures
       - Continue với available resources
    
    📊 KẾT QUẢ MONG ĐỢI:
    - Giảm thời gian tạo video từ 60-120s xuống 20-40s
    - Tăng reliability với fallback systems
    - Better user experience với progress tracking
    - Consistent performance regardless of API availability
    """)

if __name__ == "__main__":
    main()
