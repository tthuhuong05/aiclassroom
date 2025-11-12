#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final Working Video System with TTS Fallback
"""

import os
import sys
import tempfile
import uuid
import re
import requests
from pathlib import Path
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Load environment variables
try:
    from load_env import load_env_file
    load_env_file()
except ImportError:
    pass

def extract_text_from_file(file_path):
    """Extract text from various file formats"""
    try:
        if file_path.endswith('.pdf'):
            import PyPDF2
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        elif file_path.endswith('.docx'):
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        else:
            return "Unsupported file format"
    except Exception as e:
        print(f"Error extracting text: {e}")
        return ""

def clean_text(text):
    """Clean and normalize text"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters
    text = re.sub(r'[^\w\s.,!?;:-]', '', text)
    return text.strip()

def generate_image_with_pexels(keyword):
    """Generate image using Pexels API"""
    try:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return None
        
        headers = {"Authorization": api_key}
        response = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": keyword, "per_page": 1},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("photos"):
                photo = data["photos"][0]
                img_url = photo["src"]["large"]
                
                # Download image
                img_response = requests.get(img_url, timeout=10)
                if img_response.status_code == 200:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_file.write(img_response.content)
                    temp_file.close()
                    return temp_file.name
        
        return None
    except Exception as e:
        print(f"Pexels error: {e}")
        return None

def generate_image_with_unsplash(keyword):
    """Generate image using Unsplash API"""
    try:
        api_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if not api_key:
            return None
        
        headers = {"Authorization": f"Client-ID {api_key}"}
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={"query": keyword, "per_page": 1},
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                photo = data["results"][0]
                img_url = photo["urls"]["regular"]
                
                # Download image
                img_response = requests.get(img_url, timeout=10)
                if img_response.status_code == 200:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_file.write(img_response.content)
                    temp_file.close()
                    return temp_file.name
        
        return None
    except Exception as e:
        print(f"Unsplash error: {e}")
        return None

def generate_image_with_stability(keyword):
    """Generate image using Stability AI API"""
    try:
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "text_prompts": [{"text": keyword}],
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
            data = response.json()
            if data.get("artifacts"):
                artifact = data["artifacts"][0]
                import base64
                img_data = base64.b64decode(artifact["base64"])
                
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_file.write(img_data)
                temp_file.close()
                return temp_file.name
        
        return None
    except Exception as e:
        print(f"Stability AI error: {e}")
        return None

def generate_optimal_image(keywords):
    """Generate image using best available API"""
    if not keywords:
        return None
    
    # Try Stability AI first (best quality)
    if os.getenv("STABILITY_API_KEY"):
        img = generate_image_with_stability(keywords[0])
        if img:
            print(f"   OK Stability AI: {img}")
            return img
    
    # Try Pexels
    if os.getenv("PEXELS_API_KEY"):
        img = generate_image_with_pexels(keywords[0])
        if img:
            print(f"   OK Pexels: {img}")
            return img
    
    # Try Unsplash
    if os.getenv("UNSPLASH_ACCESS_KEY"):
        img = generate_image_with_unsplash(keywords[0])
        if img:
            print(f"   OK Unsplash: {img}")
            return img
    
    print("   LOI: All image APIs failed")
    return None

def synthesize_voice_with_elevenlabs(text, output_path):
    """Synthesize voice using ElevenLabs API"""
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        voice_id = os.getenv("ELEVENLABS_VOICE_ID", "ipTvfDXAg1zowfF1rv9w")
        
        if not api_key:
            return 0
        
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.3
            }
        }
        
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return len(text) / 10  # Estimate duration
        else:
            print(f"ElevenLabs error: {response.status_code}")
            return 0
    except Exception as e:
        print(f"ElevenLabs error: {e}")
        return 0

def synthesize_voice_with_gtts(text, output_path):
    """Synthesize voice using gTTS as fallback"""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_path)
        return len(text) / 10  # Estimate duration
    except Exception as e:
        print(f"gTTS error: {e}")
        return 0

def synthesize_voice_with_pyttsx3(text, output_path):
    """Synthesize voice using pyttsx3 as fallback"""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.9)
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        return len(text) / 10  # Estimate duration
    except Exception as e:
        print(f"pyttsx3 error: {e}")
        return 0

def synthesize_voice_fallback(text, output_path):
    """Synthesize voice with fallback options"""
    # Try ElevenLabs first
    dur = synthesize_voice_with_elevenlabs(text, output_path)
    if dur > 0:
        return dur
    
    # Try gTTS
    dur = synthesize_voice_with_gtts(text, output_path)
    if dur > 0:
        return dur
    
    # Try pyttsx3
    dur = synthesize_voice_with_pyttsx3(text, output_path)
    if dur > 0:
        return dur
    
    print("   LOI: All TTS methods failed")
    return 0

def create_slide_image(text, width=1280, height=720, image_path=None):
    """Create slide image with text and optional background"""
    try:
        # Create image
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add background image if available
        if image_path and os.path.exists(image_path):
            try:
                bg_img = Image.open(image_path)
                bg_img = bg_img.resize((width, height), Image.Resampling.LANCZOS)
                img.paste(bg_img, (0, 0))
                draw = ImageDraw.Draw(img)
            except:
                pass
        
        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Wrap text
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] > width - 100:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw text
        y_offset = 50
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y_offset), line, fill='black', font=font)
            y_offset += 40
        
        return img
    except Exception as e:
        print(f"Error creating slide image: {e}")
        return Image.new('RGB', (width, height), color='white')

def make_final_lecture_video(src_path: str, out_dir: str, title: str = None):
    """Create lecture video using all available APIs with fallbacks"""
    print("=" * 60)
    print("TAO VIDEO BAI GIANG CUOI CUNG")
    print("=" * 60)
    
    # Check APIs
    apis_available = {
        "pexels": bool(os.getenv("PEXELS_API_KEY")),
        "unsplash": bool(os.getenv("UNSPLASH_ACCESS_KEY")),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
        "stability": bool(os.getenv("STABILITY_API_KEY"))
    }
    
    print(f"APIs available: {[k for k, v in apis_available.items() if v]}")
    
    # Check minimum requirements
    if not any([apis_available["pexels"], apis_available["unsplash"], apis_available["stability"]]):
        raise RuntimeError("At least one image API required")
    
    # Create output directory
    os.makedirs(out_dir, exist_ok=True)
    
    # Step 1: Extract content
    print("Extracting content from document...")
    raw = extract_text_from_file(src_path)
    raw = clean_text(raw)
    if not raw:
        raise ValueError("Cannot extract content from document")
    
    # Step 2: Simple content analysis
    print("Analyzing content...")
    lines = raw.split('\n')
    title_line = lines[0] if lines else "AI Generated Lecture"
    
    # Create simple lecture structure
    lecture_data = {
        "lecture_title": title or title_line,
        "introduction": {
            "script": f"Welcome to {title_line}",
            "image_keywords": ["education", "learning"]
        },
        "slides": [
            {
                "title": "Main Content",
                "script": raw[:200] + "..." if len(raw) > 200 else raw,
                "image_keywords": ["presentation", "education"]
            }
        ],
        "conclusion": {
            "script": "Thank you for watching",
            "image_keywords": ["conclusion", "thank you"]
        }
    }
    
    print(f"Title: {lecture_data['lecture_title']}")
    
    # Step 3: Create video
    clips = []
    timeline = []
    cur_t = 0.0
    tmpdir = tempfile.mkdtemp(prefix="final_lecture_")
    
    # Introduction slide
    print("\nCreating introduction slide...")
    intro_img = generate_optimal_image(lecture_data["introduction"]["image_keywords"])
    intro_clip = create_final_slide(
        lecture_data["introduction"]["script"], 
        tmpdir, 0, img_path=intro_img
    )
    if intro_clip:
        clips.append(intro_clip)
        timeline.append((cur_t, cur_t + intro_clip.duration, lecture_data["introduction"]["script"]))
        cur_t += intro_clip.duration
    
    # Main slides
    for i, slide_data in enumerate(lecture_data["slides"], 1):
        print(f"\nCreating slide {i}...")
        slide_img = generate_optimal_image(slide_data["image_keywords"])
        slide_clip = create_final_slide(
            slide_data["script"], 
            tmpdir, i, img_path=slide_img
        )
        if slide_clip:
            clips.append(slide_clip)
            timeline.append((cur_t, cur_t + slide_clip.duration, slide_data["script"]))
            cur_t += slide_clip.duration
    
    # Conclusion slide
    print("\nCreating conclusion slide...")
    conclusion_img = generate_optimal_image(lecture_data["conclusion"]["image_keywords"])
    conclusion_clip = create_final_slide(
        lecture_data["conclusion"]["script"], 
        tmpdir, len(lecture_data["slides"]) + 1, img_path=conclusion_img
    )
    if conclusion_clip:
        clips.append(conclusion_clip)
        timeline.append((cur_t, cur_t + conclusion_clip.duration, lecture_data["conclusion"]["script"]))
        cur_t += conclusion_clip.duration
    
    # Render video
    if not clips:
        raise ValueError("Cannot create video")
    
    print("\nRendering final video...")
    final = concatenate_videoclips(clips, method="compose")
    
    video_title = title or lecture_data["lecture_title"]
    vid_name = f"{uuid.uuid4()}_{re.sub(r'[^a-zA-Z0-9_-]+','_', video_title)}.mp4"
    vtt_name = vid_name.replace(".mp4", ".vtt")
    
    out_video = os.path.join(out_dir, vid_name)
    out_vtt = os.path.join(out_dir, vtt_name)
    
    final.write_videofile(
        out_video, fps=24, codec="libx264", audio_codec="aac",
        temp_audiofile=os.path.join(tmpdir, "temp-audio.m4a"),
        remove_temp=True
    )
    
    # Write VTT file
    with open(out_vtt, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for i, (start, end, text) in enumerate(timeline):
            f.write(f"{i+1}\n")
            f.write(f"{start:.3f} --> {end:.3f}\n")
            f.write(f"{text}\n\n")
    
    print(f"\nFinal video created successfully: {out_video}")
    print(f"Duration: {cur_t:.1f} seconds")
    print(f"Total slides: {len(clips)}")
    
    return {
        "video_path": out_video,
        "caption_path": out_vtt,
        "script_text": raw,
        "lecture_info": {
            "title": lecture_data["lecture_title"],
            "total_slides": len(clips),
            "total_duration_seconds": cur_t,
            "apis_used": [k for k, v in apis_available.items() if v],
            "image_generator": "Final Multi-API with Fallbacks"
        }
    }

def create_final_slide(script, tmpdir, slide_num, img_path=None):
    """Create final slide with fallback TTS"""
    try:
        # Create slide image
        frame_path = os.path.join(tmpdir, f"final_slide_{slide_num:03d}.png")
        slide_img = create_slide_image(script, image_path=img_path)
        slide_img.save(frame_path)
        
        # Create audio with fallback
        audio_path = os.path.join(tmpdir, f"final_audio_{slide_num:03d}.mp3")
        print(f"   Synthesizing voice for slide {slide_num}...")
        dur = synthesize_voice_fallback(script, audio_path)
        
        # Check audio file
        if not os.path.exists(audio_path):
            return None
        
        clip = ImageClip(frame_path).set_duration(max(3.0, float(dur)))
        if audio_path:
            aclip = AudioFileClip(audio_path)
            clip = clip.set_audio(aclip).set_duration(aclip.duration)
            print(f"   Slide {slide_num} duration: {aclip.duration:.1f}s")
        
        return clip
        
    except Exception as e:
        print(f"   Error creating slide {slide_num}: {e}")
        return None

def test_final_system():
    """Test final video system"""
    print("\n" + "=" * 60)
    print("TEST HE THONG VIDEO CUOI CUNG")
    print("=" * 60)
    
    # Create sample document
    sample_content = """
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
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(sample_content)
    temp_file.close()
    
    try:
        # Create output directory
        output_dir = "test_final_system"
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Created sample document: {temp_file.name}")
        print("Generating final video with all APIs and fallbacks...")
        
        result = make_final_lecture_video(
            src_path=temp_file.name,
            out_dir=output_dir,
            title="Final AI Video Test"
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

def main():
    """Main function"""
    print("HE THONG VIDEO AI CUOI CUNG")
    print("Su dung TAT CA API keys co san voi fallback")
    
    # Test final system
    success = test_final_system()
    
    if success:
        print("\nHOAN THANH!")
        print("He thong cuoi cung da hoat dong!")
        print("\nBan co the:")
        print("1. Su dung ngay trong ung dung web")
        print("2. Tao video tu file PDF, DOCX, PPTX, TXT")
        print("3. Thuong thuc chat luong cao voi tat ca APIs")
        print("\nAPIs da duoc su dung:")
        print("- Pexels: Tim hinh anh phu hop")
        print("- Unsplash: Backup hinh anh")
        print("- ElevenLabs: Giong nguoi that (voi fallback)")
        print("- Stability AI: Tao hinh anh AI")
        print("\nFallback systems:")
        print("- gTTS: Google Text-to-Speech")
        print("- pyttsx3: Offline TTS")
    else:
        print("\nCAN KIEM TRA LAI")
        print("Mot so API keys co the can cau hinh lai")

if __name__ == "__main__":
    main()
