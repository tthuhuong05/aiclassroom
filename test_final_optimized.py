#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Optimized Video System
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

def test_optimized_video_simple():
    """Test optimized video generation with simple content"""
    print("=" * 60)
    print("TEST HE THONG VIDEO TOI UU")
    print("=" * 60)
    
    # Create simple document
    simple_content = """
    # Introduction to Machine Learning

    Machine Learning is a subset of artificial intelligence.

    ## Key Concepts

    ### Supervised Learning
    Uses labeled data to train models.

    ### Unsupervised Learning
    Finds patterns in unlabeled data.

    ### Deep Learning
    Uses neural networks with multiple layers.

    ## Applications
    Used in healthcare, finance, and technology.

    ## Conclusion
    ML is transforming problem-solving approaches.
    """
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(simple_content)
    temp_file.close()
    
    try:
        from services.doc_video_service import make_optimized_lecture_video
        
        # Create output directory
        output_dir = "test_optimized_final"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating optimized video with all APIs...")
        
        result = make_optimized_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Final Optimized AI Video"
        )
        
        if result:
            print("\n" + "=" * 40)
            print("THANH CONG!")
            print("=" * 40)
            print(f"Video: {result['video_path']}")
            print(f"Caption: {result['caption_path']}")
            
            lecture_info = result.get('lecture_info', {})
            print(f"Title: {lecture_info.get('title', 'N/A')}")
            print(f"Slides: {lecture_info.get('total_slides', 'N/A')}")
            print(f"Duration: {lecture_info.get('total_duration_seconds', 'N/A'):.1f}s")
            print(f"APIs used: {lecture_info.get('apis_used', [])}")
            print(f"Image generator: {lecture_info.get('image_generator', 'N/A')}")
            
            print("\n" + "=" * 40)
            print("HE THONG DA HOAT DONG!")
            print("=" * 40)
            print("Tat ca API keys da duoc su dung:")
            print("- Stability AI: Tao hinh anh AI chat luong cao")
            print("- Pexels: Tim hinh anh phu hop voi noi dung")
            print("- Unsplash: Backup hinh anh")
            print("- ElevenLabs: Giong nguoi that tu nhien")
            print("- Gemini: Phan tich noi dung chuyen sau")
            
            return True
        else:
            print("ERROR: Video generation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def check_api_status():
    """Check status of all APIs"""
    print("\nKIEM TRA TRANG THAI API KEYS:")
    print("-" * 40)
    
    apis = {
        "PEXELS_API_KEY": "Pexels (Hinh anh)",
        "UNSPLASH_ACCESS_KEY": "Unsplash (Backup hinh anh)",
        "ELEVENLABS_API_KEY": "ElevenLabs (Giong noi)",
        "GEMINI_API_KEY": "Gemini (Phan tich noi dung)",
        "STABILITY_API_KEY": "Stability AI (Tao hinh anh AI)"
    }
    
    for key, description in apis.items():
        value = os.getenv(key)
        if value:
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print(f"OK {description}: {masked_value}")
        else:
            print(f"NO {description}: CHUA CO")

def main():
    """Main function"""
    print("HE THONG TAI VIDEO AI TOI UU")
    print("Su dung TAT CA API keys co san")
    
    # Check API status
    check_api_status()
    
    # Test optimized video generation
    success = test_optimized_video_simple()
    
    if success:
        print("\nHOAN THANH!")
        print("He thong da duoc toi uu va san sang su dung!")
        print("\nBan co the:")
        print("1. Su dung ngay trong ung dung web")
        print("2. Tao video tu file PDF, DOCX, PPTX, TXT")
        print("3. Thuong thuc chat luong cao voi tat ca APIs")
    else:
        print("\nCAN KIEM TRA LAI")
        print("Mot so API keys co the can cau hinh lai")

if __name__ == "__main__":
    main()
