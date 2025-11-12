#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Image Content Matching
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

def test_image_content_analysis():
    """Test image content analysis"""
    print("Testing Image Content Analysis...")
    
    try:
        from services.working_image_service import analyze_content_for_working_images
        
        # Test với nội dung AI
        ai_content = """
        Machine Learning và Deep Learning
        
        Machine Learning là một nhánh của trí tuệ nhân tạo tập trung vào việc phát triển các thuật toán 
        cho phép máy tính học từ dữ liệu mà không cần được lập trình rõ ràng.
        
        Deep Learning sử dụng Neural Networks với nhiều lớp để học các pattern phức tạp từ dữ liệu.
        """
        
        print("Testing AI content analysis...")
        ai_prompts = analyze_content_for_working_images(ai_content)
        print(f"AI prompts: {ai_prompts}")
        
        # Test với nội dung kinh doanh
        business_content = """
        Chiến lược Marketing Digital
        
        Marketing Digital bao gồm các hoạt động quảng cáo và tiếp thị sử dụng các kênh digital 
        như social media, email marketing, và search engine optimization.
        
        Các công cụ chính bao gồm Google Ads, Facebook Ads, và content marketing.
        """
        
        print("\nTesting Business content analysis...")
        business_prompts = analyze_content_for_working_images(business_content)
        print(f"Business prompts: {business_prompts}")
        
        # Test với nội dung giáo dục
        education_content = """
        Phương pháp Giảng dạy Hiện đại
        
        Giảng dạy hiện đại tập trung vào việc tạo ra môi trường học tập tương tác và thực tế.
        
        Sử dụng công nghệ như virtual reality, gamification, và personalized learning.
        """
        
        print("\nTesting Education content analysis...")
        education_prompts = analyze_content_for_working_images(education_content)
        print(f"Education prompts: {education_prompts}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Image content analysis failed: {e}")
        return False

def test_image_generation():
    """Test image generation with improved prompts"""
    print("\nTesting Image Generation...")
    
    try:
        from services.working_image_service import generate_working_image
        
        # Test prompts
        test_prompts = [
            "machine learning technology",
            "business strategy planning", 
            "education learning platform",
            "data analysis charts",
            "scientific research laboratory"
        ]
        
        successful_generations = 0
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\nTesting prompt {i}: {prompt}")
            
            result = generate_working_image(prompt, style="educational")
            
            if result and result.get("success"):
                print(f"SUCCESS: Generated image with {result.get('service', 'Unknown')}")
                print(f"File: {result.get('file_path', 'N/A')}")
                successful_generations += 1
            else:
                print(f"FAILED: Could not generate image for '{prompt}'")
        
        print(f"\nImage Generation Results: {successful_generations}/{len(test_prompts)} successful")
        return successful_generations > 0
        
    except Exception as e:
        print(f"ERROR: Image generation test failed: {e}")
        return False

def test_video_generation_with_images():
    """Test video generation with proper image matching"""
    print("\nTesting Video Generation with Image Matching...")
    
    # Create sample document
    sample_content = """
    # Machine Learning and Deep Learning

    ## Introduction
    Machine Learning is a branch of artificial intelligence focused on developing algorithms that allow computers to learn from data.

    ## Types of Machine Learning

    ### 1. Supervised Learning
    Supervised learning uses labeled data to train models.

    **Examples:**
    - Email spam classification
    - House price prediction
    - Image recognition

    ### 2. Unsupervised Learning
    Unsupervised learning finds hidden patterns in unlabeled data.

    **Examples:**
    - Customer segmentation
    - Anomaly detection
    - Data dimensionality reduction

    ### 3. Deep Learning
    Deep Learning uses Neural Networks with multiple layers to learn complex patterns.

    **Applications:**
    - Computer Vision
    - Natural Language Processing
    - Speech Recognition

    ## Conclusion
    Machine Learning and Deep Learning are changing how we solve complex problems.
    """
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(sample_content)
    temp_file.close()
    
    try:
        from services.doc_video_service import make_working_lecture_video
        
        # Create output directory
        output_dir = "test_image_matching_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating video with improved image matching...")
        
        result = make_working_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Machine Learning với Image Matching"
        )
        
        if result:
            print("SUCCESS: Video generation with image matching successful!")
            print(f"Video: {result['video_path']}")
            print(f"Caption: {result['caption_path']}")
            
            lecture_info = result.get('lecture_info', {})
            print(f"Title: {lecture_info.get('title', 'N/A')}")
            print(f"Slides: {lecture_info.get('total_slides', 'N/A')}")
            print(f"Duration: {lecture_info.get('total_duration_seconds', 'N/A'):.1f}s")
            print(f"Image generator: {lecture_info.get('image_generator', 'N/A')}")
            
            return True
        else:
            print("ERROR: Video generation with image matching failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Video generation test failed: {e}")
        return False
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def main():
    """Main function"""
    print("Image Content Matching Test")
    print("=" * 50)
    
    # Test image content analysis
    analysis_ok = test_image_content_analysis()
    
    # Test image generation
    generation_ok = test_image_generation()
    
    # Test video generation with images
    video_ok = test_video_generation_with_images()
    
    print("\n" + "=" * 50)
    print("RESULTS:")
    print(f"  Image Content Analysis: {'OK' if analysis_ok else 'FAILED'}")
    print(f"  Image Generation: {'OK' if generation_ok else 'FAILED'}")
    print(f"  Video Generation with Images: {'OK' if video_ok else 'FAILED'}")
    
    if analysis_ok and generation_ok and video_ok:
        print("\nSUCCESS: All tests passed!")
        print("The system should now generate videos with images that match the content.")
        print("\nKey improvements:")
        print("  - Better content analysis for image prompts")
        print("  - Improved keyword mapping for search")
        print("  - More specific and relevant image generation")
        print("  - Fixed Gemini model compatibility")
    else:
        print("\nERROR: Some tests failed")
        print("Check the error messages above for details")

if __name__ == "__main__":
    main()
