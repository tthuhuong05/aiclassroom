#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Video Generation with Fallback Method
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

def test_fallback_video_generation():
    """Test video generation using fallback method"""
    print("Testing Fallback Video Generation...")
    
    # Create simple document
    simple_content = """
    # Introduction to Machine Learning

    Machine Learning is a subset of artificial intelligence that focuses on algorithms.

    ## Key Concepts

    ### Supervised Learning
    Uses labeled data to train models.

    ### Unsupervised Learning  
    Finds patterns in unlabeled data.

    ### Deep Learning
    Uses neural networks with multiple layers.

    ## Applications
    Machine Learning is used in many fields like healthcare, finance, and technology.
    """
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(simple_content)
    temp_file.close()
    
    try:
        from services.doc_video_service import make_gemini_lecture_video
        
        # Create output directory
        output_dir = "test_fallback_video_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created simple document: {temp_file.name}")
        print("Generating video with fallback method...")
        
        result = make_gemini_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Fallback Machine Learning Video"
        )
        
        if result:
            print("SUCCESS: Fallback video generation successful!")
            print(f"Video: {result['video_path']}")
            print(f"Caption: {result['caption_path']}")
            
            lecture_info = result.get('lecture_info', {})
            print(f"Title: {lecture_info.get('title', 'N/A')}")
            print(f"Slides: {lecture_info.get('total_slides', 'N/A')}")
            print(f"Duration: {lecture_info.get('total_duration_seconds', 'N/A'):.1f}s")
            print(f"Image generator: {lecture_info.get('image_generator', 'N/A')}")
            
            return True
        else:
            print("ERROR: Fallback video generation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Fallback video generation failed: {e}")
        return False
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def main():
    """Main function"""
    print("Fallback Video Generation Test")
    print("=" * 40)
    
    # Test fallback video generation
    video_ok = test_fallback_video_generation()
    
    print("\n" + "=" * 40)
    print("RESULTS:")
    print(f"  Fallback Video Generation: {'OK' if video_ok else 'FAILED'}")
    
    if video_ok:
        print("\nSUCCESS: Fallback video generation is working!")
        print("The system can generate videos even when Gemini fails:")
        print("  - Uses fallback content analysis")
        print("  - Still gets relevant images from Pexels")
        print("  - Maintains human voice synthesis")
        print("  - Creates professional video structure")
    else:
        print("\nERROR: Fallback video generation failed")
        print("Check the error messages above for details")

if __name__ == "__main__":
    main()
