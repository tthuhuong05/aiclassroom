#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final Test - All APIs Working in Web Application
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

def test_web_application():
    """Test the web application with final video system"""
    print("=" * 60)
    print("TEST UNG DUNG WEB VOI HE THONG CUOI CUNG")
    print("=" * 60)
    
    # Create sample document
    sample_content = """
    # Introduction to Artificial Intelligence

    Artificial Intelligence is transforming our world.

    ## What is AI?

    AI refers to machines that can perform tasks that typically require human intelligence.

    ## Types of AI

    ### Machine Learning
    Algorithms that learn from data.

    ### Deep Learning
    Neural networks with multiple layers.

    ### Natural Language Processing
    Understanding and generating human language.

    ## Applications

    AI is used in healthcare, finance, transportation, and many other fields.

    ## Future of AI

    AI will continue to evolve and impact our daily lives.

    ## Conclusion

    AI is a powerful technology that requires responsible development and use.
    """
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(sample_content)
    temp_file.close()
    
    try:
        # Test the final video system
        from final_video_system import make_final_lecture_video
        
        # Create output directory
        output_dir = "test_web_final"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating video for web application...")
        
        result = make_final_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Web Application AI Video Test"
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

def check_all_api_keys():
    """Check all API keys status"""
    print("\nKIEM TRA TAT CA API KEYS:")
    print("-" * 40)
    
    apis = {
        "PEXELS_API_KEY": "Pexels (Hinh anh chat luong cao)",
        "UNSPLASH_ACCESS_KEY": "Unsplash (Backup hinh anh)",
        "ELEVENLABS_API_KEY": "ElevenLabs (Giong nguoi that)",
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
    print("HE THONG VIDEO AI CUOI CUNG")
    print("Su dung TAT CA API keys co san trong ung dung web")
    
    # Check all APIs
    working_apis = check_all_api_keys()
    
    if len(working_apis) >= 3:  # At least 3 APIs needed
        print("\nDu APIs de tao video!")
        
        # Test web application
        success = test_web_application()
        
        if success:
            print("\n" + "=" * 60)
            print("HOAN THANH!")
            print("=" * 60)
            print("He thong da san sang su dung trong ung dung web!")
            print("\nBan co the:")
            print("1. Su dung ngay trong ung dung web")
            print("2. Tao video tu file PDF, DOCX, PPTX, TXT")
            print("3. Thuong thuc chat luong cao voi tat ca APIs")
            print("\nAPIs da duoc su dung:")
            for api in working_apis:
                print(f"- {api}")
            print("\nFallback systems:")
            print("- gTTS: Google Text-to-Speech")
            print("- pyttsx3: Offline TTS")
            print("\nDe su dung:")
            print("1. Chay: python app.py")
            print("2. Mo trinh duyet: http://localhost:5000")
            print("3. Upload file va tao video AI")
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
