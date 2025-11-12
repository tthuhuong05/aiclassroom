#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized Video Creation System with Progress Tracking
"""

import os
import sys
import tempfile
import uuid
import re
import requests
import time
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
    text = text.strip()
    
    return text

def generate_optimal_image(keywords):
    """Generate image with fallback system"""
    if not keywords:
        keywords = ["education", "learning"]
    
    # Try Stability AI first
    if os.getenv("STABILITY_API_KEY"):
        try:
            result = generate_stability_image(keywords[0])
            if result and result.get("success"):
                return result["file_path"]
        except Exception as e:
            print(f"Stability AI error: {e}")
    
    # Try Pexels
    if os.getenv("PEXELS_API_KEY"):
        try:
            result = generate_pexels_image(keywords[0])
            if result and result.get("success"):
                return result["file_path"]
        except Exception as e:
            print(f"Pexels error: {e}")
    
    # Try Unsplash
    if os.getenv("UNSPLASH_ACCESS_KEY"):
        try:
            result = generate_unsplash_image(keywords[0])
            if result and result.get("success"):
                return result["file_path"]
        except Exception as e:
            print(f"Unsplash error: {e}")
    
    # Fallback to default image
    return create_default_image(keywords[0])

def generate_stability_image(prompt):
    """Generate image using Stability AI"""
    try:
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "text_prompts": [{"text": prompt, "weight": 1}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 20
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if "artifacts" in result and result["artifacts"]:
                import base64
                image_data = base64.b64decode(result["artifacts"][0]["base64"])
                
                # Save image
                temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                temp_file.write(image_data)
                temp_file.close()
                
                return {"success": True, "file_path": temp_file.name}
        
        return {"success": False, "error": f"API error: {response.status_code}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_pexels_image(query):
    """Generate image using Pexels"""
    try:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": api_key}
        params = {"query": query, "per_page": 1}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "photos" in data and data["photos"]:
                photo_url = data["photos"][0]["src"]["large"]
                
                # Download image
                img_response = requests.get(photo_url, timeout=10)
                if img_response.status_code == 200:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_file.write(img_response.content)
                    temp_file.close()
                    
                    return {"success": True, "file_path": temp_file.name}
        
        return {"success": False, "error": f"API error: {response.status_code}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_unsplash_image(query):
    """Generate image using Unsplash"""
    try:
        access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if not access_key:
            return {"success": False, "error": "No API key"}
        
        url = "https://api.unsplash.com/search/photos"
        headers = {"Authorization": f"Client-ID {access_key}"}
        params = {"query": query, "per_page": 1}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data and data["results"]:
                photo_url = data["results"][0]["urls"]["regular"]
                
                # Download image
                img_response = requests.get(photo_url, timeout=10)
                if img_response.status_code == 200:
                    temp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
                    temp_file.write(img_response.content)
                    temp_file.close()
                    
                    return {"success": True, "file_path": temp_file.name}
        
        return {"success": False, "error": f"API error: {response.status_code}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_default_image(keyword):
    """Create default image when APIs fail"""
    try:
        # Create a simple colored image
        img = Image.new('RGB', (1024, 1024), color=(70, 130, 180))
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Draw text
        text = keyword.replace('_', ' ').title()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (1024 - text_width) // 2
        y = (1024 - text_height) // 2
        
        draw.text((x, y), text, fill=(255, 255, 255), font=font)
        
        # Save image
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        print(f"Error creating default image: {e}")
        return None

def synthesize_voice_fast(text, output_path):
    """Fast voice synthesis with fallbacks"""
    # Try ElevenLabs first
    if os.getenv("ELEVENLABS_API_KEY"):
        try:
            result = synthesize_elevenlabs(text, output_path)
            if result.get("success"):
                return result
        except Exception as e:
            print(f"ElevenLabs error: {e}")
    
    # Fallback to pyttsx3 (fastest)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)
        engine.setProperty('volume', 0.8)
        
        # Save to file
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        if os.path.exists(output_path):
            return {"success": True, "file_path": output_path, "duration": len(text) / 150 * 60}
        
    except Exception as e:
        print(f"pyttsx3 error: {e}")
    
    # Final fallback - create silent audio
    try:
        from moviepy.editor import AudioClip
        duration = len(text) / 150 * 60  # Estimate duration
        silent_clip = AudioClip(lambda t: 0, duration=duration)
        silent_clip.write_audiofile(output_path, verbose=False, logger=None)
        return {"success": True, "file_path": output_path, "duration": duration}
        
    except Exception as e:
        print(f"Silent audio error: {e}")
        return {"success": False, "error": str(e)}

def synthesize_elevenlabs(text, output_path):
    """Synthesize voice using ElevenLabs"""
    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        url = "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.8,
                "style": 0.3
            }
        }
        
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            # Estimate duration
            duration = len(text) / 150 * 60
            return {"success": True, "file_path": output_path, "duration": duration}
        
        return {"success": False, "error": f"API error: {response.status_code}"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def create_optimized_slide(script, tmpdir, slide_num, img_path=None):
    """Create optimized slide with fast processing"""
    try:
        # Create slide image
        frame_path = os.path.join(tmpdir, f"opt_slide_{slide_num:03d}.png")
        
        if img_path and os.path.exists(img_path):
            # Use provided image
            img = Image.open(img_path)
            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
        else:
            # Create default slide
            img = Image.new('RGB', (1280, 720), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except:
                font = ImageFont.load_default()
            
            # Draw text
            text_lines = script.split('\n')
            y = 50
            for line in text_lines[:10]:  # Limit to 10 lines
                draw.text((50, y), line[:60], fill=(0, 0, 0), font=font)
                y += 40
        
        img.save(frame_path)
        
        # Create audio
        audio_path = os.path.join(tmpdir, f"opt_audio_{slide_num:03d}.mp3")
        voice_result = synthesize_voice_fast(script, audio_path)
        
        if voice_result.get("success"):
            duration = voice_result.get("duration", 5.0)
        else:
            duration = 5.0  # Default duration
        
        # Create video clip
        clip = ImageClip(frame_path).set_duration(duration)
        
        if os.path.exists(audio_path):
            audio_clip = AudioFileClip(audio_path)
            clip = clip.set_audio(audio_clip).set_duration(audio_clip.duration)
        
        return clip
        
    except Exception as e:
        print(f"Error creating slide {slide_num}: {e}")
        return None

def make_fast_lecture_video(src_path: str, out_dir: str, title: str = None):
    """Create lecture video with optimized performance"""
    print("=" * 60)
    print("TAO VIDEO BAI GIANG TOI UU")
    print("=" * 60)
    
    start_time = time.time()
    
    # Check APIs
    apis_available = {
        "pexels": bool(os.getenv("PEXELS_API_KEY")),
        "unsplash": bool(os.getenv("UNSPLASH_ACCESS_KEY")),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
        "stability": bool(os.getenv("STABILITY_API_KEY"))
    }
    
    print(f"APIs available: {[k for k, v in apis_available.items() if v]}")
    
    # Create output directory
    os.makedirs(out_dir, exist_ok=True)
    
    # Step 1: Extract content (fast)
    print("Step 1/5: Extracting content...")
    extract_start = time.time()
    raw = extract_text_from_file(src_path)
    raw = clean_text(raw)
    if not raw:
        raise ValueError("Cannot extract content from document")
    print(f"Content extracted in {time.time() - extract_start:.1f}s")
    
    # Step 2: Simple analysis (fast)
    print("Step 2/5: Analyzing content...")
    analysis_start = time.time()
    lines = raw.split('\n')
    title_line = lines[0] if lines else "AI Generated Lecture"
    
    # Create simple structure
    lecture_data = {
        "lecture_title": title or title_line,
        "introduction": {
            "script": f"Welcome to {title_line}",
            "image_keywords": ["education", "learning"]
        },
        "slides": [
            {
                "title": "Main Content",
                "script": raw[:300] + "..." if len(raw) > 300 else raw,
                "image_keywords": ["presentation", "education"]
            }
        ],
        "conclusion": {
            "script": "Thank you for watching this lecture",
            "image_keywords": ["conclusion", "thank you"]
        }
    }
    print(f"Analysis completed in {time.time() - analysis_start:.1f}s")
    
    # Step 3: Generate images (optimized)
    print("Step 3/5: Generating images...")
    image_start = time.time()
    tmpdir = tempfile.mkdtemp(prefix="fast_lecture_")
    
    intro_img = generate_optimal_image(lecture_data["introduction"]["image_keywords"])
    slide_img = generate_optimal_image(lecture_data["slides"][0]["image_keywords"])
    conclusion_img = generate_optimal_image(lecture_data["conclusion"]["image_keywords"])
    print(f"Images generated in {time.time() - image_start:.1f}s")
    
    # Step 4: Create slides (optimized)
    print("Step 4/5: Creating slides...")
    slide_start = time.time()
    clips = []
    timeline = []
    cur_t = 0.0
    
    # Introduction
    intro_clip = create_optimized_slide(
        lecture_data["introduction"]["script"], 
        tmpdir, 0, img_path=intro_img
    )
    if intro_clip:
        clips.append(intro_clip)
        timeline.append((cur_t, cur_t + intro_clip.duration, lecture_data["introduction"]["script"]))
        cur_t += intro_clip.duration
    
    # Main slide
    slide_clip = create_optimized_slide(
        lecture_data["slides"][0]["script"], 
        tmpdir, 1, img_path=slide_img
    )
    if slide_clip:
        clips.append(slide_clip)
        timeline.append((cur_t, cur_t + slide_clip.duration, lecture_data["slides"][0]["script"]))
        cur_t += slide_clip.duration
    
    # Conclusion
    conclusion_clip = create_optimized_slide(
        lecture_data["conclusion"]["script"], 
        tmpdir, 2, img_path=conclusion_img
    )
    if conclusion_clip:
        clips.append(conclusion_clip)
        timeline.append((cur_t, cur_t + conclusion_clip.duration, lecture_data["conclusion"]["script"]))
        cur_t += conclusion_clip.duration
    
    print(f"Slides created in {time.time() - slide_start:.1f}s")
    
    # Step 5: Render video (optimized)
    print("Step 5/5: Rendering video...")
    render_start = time.time()
    
    if not clips:
        raise ValueError("Cannot create video")
    
    final = concatenate_videoclips(clips, method="compose")
    
    video_title = title or lecture_data["lecture_title"]
    vid_name = f"{uuid.uuid4()}_{re.sub(r'[^a-zA-Z0-9_-]+','_', video_title)}.mp4"
    vtt_name = vid_name.replace(".mp4", ".vtt")
    
    out_video = os.path.join(out_dir, vid_name)
    out_vtt = os.path.join(out_dir, vtt_name)
    
    # Optimized video settings
    final.write_videofile(
        out_video, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac",
        temp_audiofile=os.path.join(tmpdir, "temp-audio.m4a"),
        remove_temp=True,
        verbose=False,
        logger=None
    )
    
    # Write VTT file
    with open(out_vtt, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for i, (start, end, text) in enumerate(timeline):
            f.write(f"{i+1}\n")
            f.write(f"{start:.3f} --> {end:.3f}\n")
            f.write(f"{text}\n\n")
    
    total_time = time.time() - start_time
    render_time = time.time() - render_start
    
    print(f"Video rendered in {render_time:.1f}s")
    print(f"Total time: {total_time:.1f}s")
    print(f"Final video: {out_video}")
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
            "image_generator": "Optimized Multi-API System",
            "processing_time": total_time
        }
    }

if __name__ == "__main__":
    # Test the optimized system
    import tempfile
    
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
    
    # Test optimized video creation
    result = make_fast_lecture_video(temp_file.name, "test_output", "Test Optimized Video")
    
    print(f"\nOptimized video created: {result['video_path']}")
    print(f"Processing time: {result['lecture_info']['processing_time']:.1f}s")
    
    # Clean up
    os.unlink(temp_file.name)
