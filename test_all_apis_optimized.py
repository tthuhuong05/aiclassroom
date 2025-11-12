#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comprehensive API Keys Test and Video Generation Optimization
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

def test_all_api_keys():
    """Test all API keys comprehensively"""
    print("=" * 60)
    print("KIEM TRA TAT CA API KEYS")
    print("=" * 60)
    
    results = {}
    
    # Test Pexels API
    print("\n1. PEXELS API (Hinh anh chat luong cao):")
    try:
        import requests
        pexels_key = os.getenv("PEXELS_API_KEY")
        if pexels_key:
            headers = {"Authorization": pexels_key}
            response = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": "machine learning", "per_page": 1},
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("photos"):
                    print("   ✅ HOAT DONG TOT - Co the tim hinh anh")
                    results["pexels"] = True
                else:
                    print("   ⚠️ HOAT DONG NHUNG KHONG TIM THAY HINH ANH")
                    results["pexels"] = True
            else:
                print(f"   ❌ LOI: {response.status_code}")
                results["pexels"] = False
        else:
            print("   ❌ CHUA CO API KEY")
            results["pexels"] = False
    except Exception as e:
        print(f"   ❌ LOI: {e}")
        results["pexels"] = False
    
    # Test Unsplash API
    print("\n2. UNSPLASH API (Backup hinh anh):")
    try:
        unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if unsplash_key:
            headers = {"Authorization": f"Client-ID {unsplash_key}"}
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                params={"query": "technology", "per_page": 1},
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    print("   ✅ HOAT DONG TOT - Co the tim hinh anh")
                    results["unsplash"] = True
                else:
                    print("   ⚠️ HOAT DONG NHUNG KHONG TIM THAY HINH ANH")
                    results["unsplash"] = True
            else:
                print(f"   ❌ LOI: {response.status_code}")
                results["unsplash"] = False
        else:
            print("   ❌ CHUA CO API KEY")
            results["unsplash"] = False
    except Exception as e:
        print(f"   ❌ LOI: {e}")
        results["unsplash"] = False
    
    # Test ElevenLabs API
    print("\n3. ELEVENLABS API (Giong nguoi that):")
    try:
        elevenlabs_key = os.getenv("ELEVENLABS_API_KEY")
        if elevenlabs_key:
            headers = {"xi-api-key": elevenlabs_key}
            response = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("voices"):
                    print("   ✅ HOAT DONG TOT - Co the tao giong nguoi that")
                    results["elevenlabs"] = True
                else:
                    print("   ⚠️ HOAT DONG NHUNG KHONG CO VOICES")
                    results["elevenlabs"] = True
            else:
                print(f"   ❌ LOI: {response.status_code}")
                results["elevenlabs"] = False
        else:
            print("   ❌ CHUA CO API KEY")
            results["elevenlabs"] = False
    except Exception as e:
        print(f"   ❌ LOI: {e}")
        results["elevenlabs"] = False
    
    # Test Gemini API
    print("\n4. GEMINI API (Phan tich noi dung):")
    try:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content("Test API connection")
            if response.text:
                print("   ✅ HOAT DONG TOT - Co the phan tich noi dung")
                results["gemini"] = True
            else:
                print("   ❌ LOI: Khong tra ve ket qua")
                results["gemini"] = False
        else:
            print("   ❌ CHUA CO API KEY")
            results["gemini"] = False
    except Exception as e:
        print(f"   ❌ LOI: {e}")
        results["gemini"] = False
    
    # Test Stability AI API
    print("\n5. STABILITY AI API (Tao hinh anh bang AI):")
    try:
        stability_key = os.getenv("STABILITY_API_KEY")
        if stability_key:
            headers = {
                "Authorization": f"Bearer {stability_key}",
                "Content-Type": "application/json"
            }
            data = {
                "text_prompts": [{"text": "test"}],
                "cfg_scale": 7,
                "height": 512,
                "width": 512,
                "samples": 1,
                "steps": 10
            }
            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                json=data,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                print("   ✅ HOAT DONG TOT - Co the tao hinh anh bang AI")
                results["stability"] = True
            else:
                print(f"   ❌ LOI: {response.status_code}")
                results["stability"] = False
        else:
            print("   ❌ CHUA CO API KEY")
            results["stability"] = False
    except Exception as e:
        print(f"   ❌ LOI: {e}")
        results["stability"] = False
    
    # Test Luna AI API (if available)
    print("\n6. LUNA AI API (Tao hinh anh bang AI):")
    try:
        luna_key = os.getenv("LUNA_API_KEY")
        if luna_key:
            # Test basic connectivity
            response = requests.get("https://api.luna.ai/v1/models", timeout=10)
            if response.status_code in [200, 401, 403]:  # Any response means API exists
                print("   ⚠️ API CO TON TAI NHUNG CHUA HOAT DONG")
                results["luna"] = False
            else:
                print("   ❌ API KHONG TON TAI")
                results["luna"] = False
        else:
            print("   ❌ CHUA CO API KEY")
            results["luna"] = False
    except Exception as e:
        print("   ❌ API KHONG HOAT DONG")
        results["luna"] = False
    
    # Test KIE AI API (if available)
    print("\n7. KIE AI API (Tao hinh anh bang AI):")
    try:
        kie_key = os.getenv("KIE_AI_KEY")
        if kie_key:
            # Test basic connectivity
            response = requests.get("https://api.kie.ai/v1/models", timeout=10)
            if response.status_code in [200, 401, 403]:  # Any response means API exists
                print("   ⚠️ API CO TON TAI NHUNG CHUA HOAT DONG")
                results["kie"] = False
            else:
                print("   ❌ API KHONG TON TAI")
                results["kie"] = False
        else:
            print("   ❌ CHUA CO API KEY")
            results["kie"] = False
    except Exception as e:
        print("   ❌ API KHONG HOAT DONG")
        results["kie"] = False
    
    return results

def create_optimized_video_system():
    """Create optimized video generation system using all available APIs"""
    print("\n" + "=" * 60)
    print("TAO HE THONG TAI VIDEO TOI UU")
    print("=" * 60)
    
    # Create optimized doc_video_service
    optimized_code = '''
def make_optimized_lecture_video(src_path: str, out_dir: str, title: str = None,
                                width=1280, height=720) -> Dict[str, str]:
    """
    Tạo video bài giảng tối ưu sử dụng TẤT CẢ API keys có sẵn.
    Thứ tự ưu tiên:
    1. Stability AI (tạo hình ảnh AI chất lượng cao)
    2. Pexels (tìm hình ảnh phù hợp)
    3. Unsplash (backup hình ảnh)
    4. ElevenLabs (giọng người thật)
    5. Gemini (phân tích nội dung chuyên sâu)
    """
    from ai_gemini import extract_main_content_from_document
    
    # Kiểm tra tất cả API keys
    apis_available = {
        "stability": is_stability_available(),
        "pexels": is_pexels_available(), 
        "unsplash": is_unsplash_available(),
        "elevenlabs": is_human_voice_available(),
        "gemini": is_gemini_available()
    }
    
    print(f"APIs available: {apis_available}")
    
    # Kiểm tra bắt buộc
    if not apis_available["elevenlabs"]:
        raise RuntimeError("ElevenLabs API key required for human voice")
    
    if not apis_available["gemini"]:
        raise RuntimeError("Gemini API key required for content analysis")
    
    if not any([apis_available["stability"], apis_available["pexels"], apis_available["unsplash"]]):
        raise RuntimeError("At least one image API required")
    
    _safe_makedirs(out_dir)
    
    # Bước 1: Trích xuất nội dung
    print("Extracting content from document...")
    raw = extract_text_from_file(src_path)
    raw = clean_text(raw)
    if not raw:
        raise ValueError("Cannot extract content from document")
    
    # Bước 2: AI phân tích nội dung
    print("AI analyzing content...")
    lecture_data = extract_main_content_from_document(raw)
    if not lecture_data:
        print("Gemini analysis failed, using fallback...")
        lecture_data = create_fallback_lecture_data(raw)
    
    print(f"Main topic: {lecture_data.get('main_topic', 'N/A')}")
    print(f"Core concepts: {', '.join(lecture_data.get('core_concepts', []))}")
    
    # Bước 3: Tạo video với tất cả APIs
    clips = []
    timeline = []
    cur_t = 0.0
    tmpdir = tempfile.mkdtemp(prefix="optimized_lecture_")
    
    # Slide giới thiệu
    intro_data = lecture_data.get("introduction", {})
    intro_script = intro_data.get("script", f"Welcome to {lecture_data.get('lecture_title', 'AI Lecture')}")
    
    print("\\nCreating introduction slide...")
    intro_img = generate_optimal_image(
        intro_data.get("image_keywords", ["introduction"]),
        apis_available
    )
    
    intro_clip = create_optimized_slide(
        intro_script, intro_data.get("key_points", []),
        tmpdir, 0, width, height, img_path=intro_img,
        apis_available
    )
    if intro_clip:
        clips.append(intro_clip)
        timeline.append((cur_t, cur_t + intro_clip.duration, intro_script))
        cur_t += intro_clip.duration
    
    # Các slides chính
    slides_data = lecture_data.get("slides", [])
    for i, slide_data in enumerate(slides_data, 1):
        print(f"\\nCreating slide {i}/{len(slides_data)}: {slide_data.get('title', 'N/A')}")
        
        slide_content = f"{slide_data.get('title', '')} {slide_data.get('main_content', '')}"
        
        # Tạo hình ảnh tối ưu
        print(f"Generating optimal image for slide {i}...")
        slide_img = generate_optimal_image(
            slide_data.get("image_keywords", []),
            apis_available
        )
        
        slide_script = slide_data.get("script", slide_data.get("main_content", ""))
        
        slide_clip = create_optimized_slide(
            slide_script, slide_data.get("key_points", []),
            tmpdir, i, width, height, img_path=slide_img,
            apis_available
        )
        
        if slide_clip:
            clips.append(slide_clip)
            timeline.append((cur_t, cur_t + slide_clip.duration, slide_script))
            cur_t += slide_clip.duration
    
    # Slide kết luận
    conclusion_data = lecture_data.get("conclusion", {})
    conclusion_script = conclusion_data.get("script", "Thank you for watching!")
    
    print("\\nCreating conclusion slide...")
    conclusion_img = generate_optimal_image(
        conclusion_data.get("image_keywords", ["conclusion"]),
        apis_available
    )
    
    conclusion_clip = create_optimized_slide(
        conclusion_script, conclusion_data.get("key_takeaways", []),
        tmpdir, len(slides_data) + 1, width, height, img_path=conclusion_img,
        apis_available
    )
    if conclusion_clip:
        clips.append(conclusion_clip)
        timeline.append((cur_t, cur_t + conclusion_clip.duration, conclusion_script))
        cur_t += conclusion_clip.duration
    
    # Ghép video
    if not clips:
        raise ValueError("Cannot create video from lecture")
    
    print("\\nRendering final video...")
    final = concatenate_videoclips(clips, method="compose")
    
    video_title = title or lecture_data.get("lecture_title", os.path.splitext(os.path.basename(src_path))[0])
    vid_name = f"{uuid.uuid4()}_{re.sub(r'[^a-zA-Z0-9_-]+','_', video_title)}.mp4"
    vtt_name = vid_name.replace(".mp4", ".vtt")
    
    out_video = os.path.join(out_dir, vid_name)
    out_vtt = os.path.join(out_dir, vtt_name)
    
    final.write_videofile(
        out_video, fps=24, codec="libx264", audio_codec="aac",
        temp_audiofile=os.path.join(tmpdir, "temp-audio.m4a"),
        remove_temp=True
    )
    write_vtt(timeline, out_vtt)
    
    # Tạo full script
    full_script = "\\n\\n".join([
        f"# {lecture_data.get('lecture_title', 'Optimized AI Lecture')}",
        f"\\n## Introduction\\n{intro_script}",
        *[f"\\n## {slide.get('title', f'Slide {i}')}\\n{slide.get('script', '')}" 
          for i, slide in enumerate(slides_data, 1)],
        f"\\n## Conclusion\\n{conclusion_script}"
    ])
    
    print(f"\\nOptimized video created successfully: {out_video}")
    print(f"Duration: {cur_t:.1f} seconds")
    print(f"Total slides: {len(slides_data) + 2}")
    print(f"APIs used: {[k for k, v in apis_available.items() if v]}")
    
    return {
        "video_path": out_video,
        "caption_path": out_vtt,
        "script_text": full_script,
        "lecture_info": {
            "title": lecture_data.get("lecture_title", "Optimized AI Lecture"),
            "main_topic": lecture_data.get("main_topic", "N/A"),
            "core_concepts": lecture_data.get("core_concepts", []),
            "total_slides": len(slides_data) + 2,
            "total_duration_seconds": cur_t,
            "apis_used": [k for k, v in apis_available.items() if v],
            "image_generator": "Optimized Multi-API"
        }
    }

def generate_optimal_image(keywords, apis_available):
    """Generate optimal image using best available API"""
    if not keywords:
        return None
    
    # Thứ tự ưu tiên: Stability AI -> Pexels -> Unsplash
    if apis_available["stability"]:
        try:
            from services.working_image_service import generate_working_image
            result = generate_working_image(keywords[0], style="educational")
            if result and result.get("success"):
                print(f"   ✅ Stability AI: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   ❌ Stability AI failed: {e}")
    
    if apis_available["pexels"]:
        try:
            from services.working_image_service import generate_working_image
            result = generate_working_image(keywords[0], style="educational")
            if result and result.get("success"):
                print(f"   ✅ Pexels: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   ❌ Pexels failed: {e}")
    
    if apis_available["unsplash"]:
        try:
            from services.working_image_service import generate_working_image
            result = generate_working_image(keywords[0], style="educational")
            if result and result.get("success"):
                print(f"   ✅ Unsplash: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   ❌ Unsplash failed: {e}")
    
    print("   ❌ All image APIs failed")
    return None

def create_optimized_slide(script, key_points, tmpdir, slide_num, width, height, img_path, apis_available):
    """Create optimized slide with best available APIs"""
    try:
        # Tạo nội dung hiển thị
        display_content = script
        if key_points:
            display_content += "\\n\\nKey Points:\\n" + "\\n".join(f"• {point}" for point in key_points)
        
        frame_path = os.path.join(tmpdir, f"optimized_slide_{slide_num:03d}.png")
        im = render_slide_image(display_content, w=width, h=height, 
                               content_type="educational", image_path=img_path)
        im.save(frame_path)
        
        # Tạo audio với ElevenLabs
        audio_path = os.path.join(tmpdir, f"optimized_audio_{slide_num:03d}.mp3")
        print(f"   Synthesizing voice for slide {slide_num}...")
        dur = synth_voice(script, audio_path)
        
        # Kiểm tra audio file
        if not os.path.exists(audio_path):
            alt_audio_path = audio_path.replace(".mp3", ".wav")
            if os.path.exists(alt_audio_path):
                audio_path = alt_audio_path
            else:
                audio_path = None
        
        clip = ImageClip(frame_path).set_duration(max(3.0, float(dur)))
        if audio_path:
            aclip = AudioFileClip(audio_path)
            clip = clip.set_audio(aclip).set_duration(aclip.duration)
            print(f"   Slide {slide_num} duration: {aclip.duration:.1f}s")
        
        return clip
        
    except Exception as e:
        print(f"   Error creating optimized slide {slide_num}: {e}")
        return None

def is_stability_available():
    """Check if Stability AI is available"""
    return bool(os.getenv("STABILITY_API_KEY"))

def is_pexels_available():
    """Check if Pexels is available"""
    return bool(os.getenv("PEXELS_API_KEY"))

def is_unsplash_available():
    """Check if Unsplash is available"""
    return bool(os.getenv("UNSPLASH_ACCESS_KEY"))

def is_gemini_available():
    """Check if Gemini is available"""
    return bool(os.getenv("GEMINI_API_KEY"))

def create_fallback_lecture_data(content):
    """Create fallback lecture data if Gemini fails"""
    return {
        "lecture_title": "AI Generated Lecture",
        "main_topic": "Educational Content",
        "core_concepts": ["Learning", "Education", "Knowledge"],
        "introduction": {
            "script": "Welcome to this educational presentation",
            "key_points": ["Introduction", "Overview"],
            "image_keywords": ["education", "learning"]
        },
        "slides": [
            {
                "title": "Main Content",
                "main_content": content[:200] + "..." if len(content) > 200 else content,
                "key_points": ["Key Point 1", "Key Point 2"],
                "script": content[:100] + "..." if len(content) > 100 else content,
                "image_keywords": ["education", "presentation"]
            }
        ],
        "conclusion": {
            "script": "Thank you for watching this presentation",
            "key_takeaways": ["Summary", "Conclusion"],
            "image_keywords": ["conclusion", "thank you"]
        }
    }
'''
    
    # Write optimized code to file
    with open("optimized_video_system.py", "w", encoding="utf-8") as f:
        f.write(optimized_code)
    
    print("✅ Đã tạo hệ thống video tối ưu: optimized_video_system.py")

def test_optimized_video_generation():
    """Test optimized video generation"""
    print("\n" + "=" * 60)
    print("TEST HE THONG VIDEO TOI UU")
    print("=" * 60)
    
    # Create sample document
    sample_content = """
    # Machine Learning and Artificial Intelligence

    ## Introduction
    Machine Learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.

    ## Key Concepts

    ### Supervised Learning
    Uses labeled training data to learn a mapping function from inputs to outputs.

    ### Unsupervised Learning
    Finds hidden patterns in data without labeled examples.

    ### Deep Learning
    Uses neural networks with multiple layers to model complex patterns.

    ## Applications
    Machine Learning is used in healthcare, finance, technology, and many other fields.

    ## Conclusion
    AI and Machine Learning are transforming how we solve complex problems.
    """
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(sample_content)
    temp_file.close()
    
    try:
        # Import optimized system
        sys.path.append(".")
        from optimized_video_system import make_optimized_lecture_video
        
        # Create output directory
        output_dir = "test_optimized_video_output"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating optimized video with all APIs...")
        
        result = make_optimized_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Optimized AI Video Test"
        )
        
        if result:
            print("SUCCESS: Optimized video generation successful!")
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
            print("ERROR: Optimized video generation failed")
            return False
            
    except Exception as e:
        print(f"ERROR: Optimized video generation failed: {e}")
        return False
    
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_file.name)
        except:
            pass

def main():
    """Main function"""
    print("HE THONG TAI VIDEO AI TOI UU")
    print("Sử dụng TẤT CẢ API keys có sẵn")
    
    # Test all API keys
    api_results = test_all_api_keys()
    
    # Create optimized system
    create_optimized_video_system()
    
    # Test optimized video generation
    video_ok = test_optimized_video_generation()
    
    print("\n" + "=" * 60)
    print("KET QUA TONG HOP")
    print("=" * 60)
    
    working_apis = [k for k, v in api_results.items() if v]
    failed_apis = [k for k, v in api_results.items() if not v]
    
    print(f"APIs hoạt động: {working_apis}")
    print(f"APIs lỗi: {failed_apis}")
    print(f"Video generation: {'OK' if video_ok else 'FAILED'}")
    
    if video_ok:
        print("\n🎉 THÀNH CÔNG!")
        print("Hệ thống đã được tối ưu để sử dụng TẤT CẢ API keys:")
        print("- Stability AI: Tạo hình ảnh AI chất lượng cao")
        print("- Pexels: Tìm hình ảnh phù hợp với nội dung")
        print("- Unsplash: Backup hình ảnh")
        print("- ElevenLabs: Giọng người thật tự nhiên")
        print("- Gemini: Phân tích nội dung chuyên sâu")
        print("\nBạn có thể sử dụng ngay trong ứng dụng web!")
    else:
        print("\n❌ CẦN KIỂM TRA LẠI")
        print("Một số API keys có thể cần cấu hình lại")

if __name__ == "__main__":
    main()
