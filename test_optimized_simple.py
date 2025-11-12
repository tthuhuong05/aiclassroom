#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Performance Test
"""

import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_optimized_system():
    """Test the optimized video system"""
    print("=" * 60)
    print("TEST HỆ THỐNG TỐI ƯU")
    print("=" * 60)
    
    # Create test content
    test_content = """
    # Introduction to Machine Learning
    
    Machine Learning is a subset of artificial intelligence.
    
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
    
    try:
        from optimized_video_system import make_fast_lecture_video
        
        start_time = time.time()
        result = make_fast_lecture_video(temp_file.name, "test_output", "Test Video")
        total_time = time.time() - start_time
        
        print(f"\nKẾT QUẢ:")
        print(f"Total time: {total_time:.1f}s")
        print(f"Video duration: {result['lecture_info']['total_duration_seconds']:.1f}s")
        print(f"Total slides: {result['lecture_info']['total_slides']}")
        print(f"APIs used: {result['lecture_info']['apis_used']}")
        print(f"Video path: {result['video_path']}")
        
        return total_time
        
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        # Clean up
        try:
            os.unlink(temp_file.name)
        except:
            pass

def analyze_performance():
    """Analyze performance results"""
    print("\n" + "=" * 60)
    print("PHÂN TÍCH HIỆU SUẤT")
    print("=" * 60)
    
    print("""
    🚀 CÁC CẢI THIỆN ĐÃ THỰC HIỆN:
    
    1. ✅ Optimized Image Generation
       - Sử dụng API nhanh nhất trước (Stability AI)
       - Fallback system khi API fail
       - Parallel processing cho multiple images
    
    2. ✅ Fast Voice Synthesis
       - ElevenLabs với timeout ngắn (30s)
       - Fallback về pyttsx3 (nhanh nhất)
       - Silent audio nếu tất cả fail
    
    3. ✅ Optimized Video Rendering
       - Lower quality settings (24fps)
       - Faster codecs (libx264)
       - Disabled verbose logging
    
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

def main():
    """Main function"""
    print("KIỂM TRA HIỆU SUẤT HỆ THỐNG TỐI ƯU")
    
    # Test optimized system
    processing_time = test_optimized_system()
    
    # Analyze performance
    analyze_performance()
    
    if processing_time:
        print(f"\n🎉 HỆ THỐNG TỐI ƯU HOẠT ĐỘNG!")
        print(f"⏱️ Thời gian xử lý: {processing_time:.1f}s")
        
        if processing_time < 40:
            print("✅ Tốc độ tốt! (< 40s)")
        elif processing_time < 60:
            print("⚠️ Tốc độ trung bình (40-60s)")
        else:
            print("❌ Tốc độ chậm (> 60s)")
    else:
        print("❌ Hệ thống có lỗi")

if __name__ == "__main__":
    main()
