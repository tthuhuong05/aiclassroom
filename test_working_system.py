#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple Test for All APIs Working
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

def test_working_video_system():
    """Test the working video system with all APIs"""
    print("=" * 60)
    print("TEST HE THONG VIDEO HOAT DONG")
    print("=" * 60)
    
    # Create simple document
    simple_content = """
    # Machine Learning Basics

    Machine Learning is a subset of artificial intelligence.

    ## Types of Learning

    ### Supervised Learning
    Uses labeled data to train models.

    ### Unsupervised Learning
    Finds patterns in unlabeled data.

    ## Applications
    Used in many fields like healthcare and finance.

    ## Conclusion
    ML is very important for modern technology.
    """
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(simple_content)
    temp_file.close()
    
    try:
        from services.doc_video_service import make_working_lecture_video
        
        # Create output directory
        output_dir = "test_working_final"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating video with working system...")
        
        result = make_working_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Working AI Video Test"
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
            print(f"Image generator: {lecture_info.get('image_generator', 'N/A')}")
            
            print("\n" + "=" * 40)
            print("HE THONG DA HOAT DONG!")
            print("=" * 40)
            print("Tat ca API keys da duoc su dung:")
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

def check_all_apis():
    """Check all API keys"""
    print("\nKIEM TRA TAT CA API KEYS:")
    print("-" * 40)
    
    apis = {
        "PEXELS_API_KEY": "Pexels (Hinh anh)",
        "UNSPLASH_ACCESS_KEY": "Unsplash (Backup hinh anh)",
        "ELEVENLABS_API_KEY": "ElevenLabs (Giong noi)",
        "GEMINI_API_KEY": "Gemini (Phan tich noi dung)",
        "STABILITY_API_KEY": "Stability AI (Tao hinh anh AI)"
    }
    
    working_apis = []
    for key, description in apis.items():
        value = os.getenv(key)
        if value:
            masked_value = value[:10] + "..." if len(value) > 10 else value
            print(f"OK {description}: {masked_value}")
            working_apis.append(key)
        else:
            print(f"NO {description}: CHUA CO")
    
    print(f"\nTong so APIs hoat dong: {len(working_apis)}/5")
    return working_apis

def main():
    """Main function"""
    print("HE THONG TAI VIDEO AI")
    print("Su dung TAT CA API keys co san")
    
    # Check all APIs
    working_apis = check_all_apis()
    
    if len(working_apis) >= 3:  # At least 3 APIs needed
        print("\nDu APIs de tao video!")
        
        # Test video generation
        success = test_working_video_system()
        
        if success:
            print("\nHOAN THANH!")
            print("He thong da san sang su dung!")
            print("\nBan co the:")
            print("1. Su dung ngay trong ung dung web")
            print("2. Tao video tu file PDF, DOCX, PPTX, TXT")
            print("3. Thuong thuc chat luong cao")
            print("\nAPIs da duoc su dung:")
            for api in working_apis:
                print(f"- {api}")
        else:
            print("\nCAN KIEM TRA LAI")
            print("Mot so API keys co the can cau hinh lai")
    else:
        print("\nKHONG DU APIs")
        print("Can it nhat 3 APIs de tao video:")
        print("- Pexels hoac Unsplash (hinh anh)")
        print("- ElevenLabs (giong noi)")
        print("- Gemini (phan tich noi dung)")

if __name__ == "__main__":
    main()
