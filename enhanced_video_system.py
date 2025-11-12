#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Content Analysis and Image Generation System
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

def analyze_content_with_gemini(text):
    """Analyze content using Gemini AI to create diverse slides"""
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("No Gemini API key, using simple analysis")
            return None
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        Analyze this document content and create a diverse lecture structure with multiple slides.
        Each slide should have specific, relevant keywords for image generation.
        
        Document content:
        {text[:2000]}  # Limit to first 2000 chars
        
        Create a JSON structure with:
        {{
            "lecture_title": "Main topic title",
            "introduction": {{
                "script": "Welcome message",
                "image_keywords": ["specific", "relevant", "keywords"]
            }},
            "slides": [
                {{
                    "title": "Slide title",
                    "script": "Detailed content for this slide",
                    "image_keywords": ["specific", "topic-related", "keywords"]
                }}
            ],
            "conclusion": {{
                "script": "Conclusion message",
                "image_keywords": ["conclusion", "summary", "keywords"]
            }}
        }}
        
        Requirements:
        - Create 4-6 diverse slides based on content
        - Each slide should have unique, specific keywords
        - Keywords should be relevant to the slide content
        - Make slides cover different aspects of the topic
        - Use specific terms rather than generic ones
        """
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.8,
                "response_mime_type": "application/json"
            }
        )
        
        if response.text:
            import json
            try:
                result = json.loads(response.text)
                print("Gemini analysis successful")
                return result
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return None
        
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return None

def create_diverse_slides_from_content(text):
    """Create diverse slides based on content analysis"""
    print("Analyzing content for diverse slides...")
    
    # Try Gemini analysis first
    gemini_result = analyze_content_with_gemini(text)
    if gemini_result:
        return gemini_result
    
    # Fallback to intelligent content analysis
    print("Using intelligent content analysis...")
    
    # Split content into sections
    lines = text.split('\n')
    title_line = lines[0] if lines else "AI Generated Lecture"
    
    # Extract key topics and concepts
    content_lower = text.lower()
    
    # Define topic categories and their keywords
    topic_keywords = {
        "machine_learning": ["machine learning", "ml", "algorithm", "model", "training", "data", "neural", "ai", "artificial intelligence"],
        "mathematics": ["math", "mathematics", "equation", "formula", "calculation", "statistics", "probability", "linear algebra"],
        "programming": ["programming", "code", "software", "development", "python", "java", "programming language", "coding"],
        "business": ["business", "management", "strategy", "marketing", "finance", "economics", "organization", "leadership"],
        "science": ["science", "research", "experiment", "theory", "hypothesis", "analysis", "scientific method"],
        "technology": ["technology", "tech", "innovation", "digital", "computer", "software", "hardware", "system"]
    }
    
    # Determine main topics
    detected_topics = []
    for topic, keywords in topic_keywords.items():
        score = sum(1 for keyword in keywords if keyword in content_lower)
        if score > 0:
            detected_topics.append((topic, score))
    
    # Sort by relevance
    detected_topics.sort(key=lambda x: x[1], reverse=True)
    
    # Create slides based on detected topics
    slides = []
    
    # Introduction slide
    intro_keywords = ["education", "learning", "introduction"]
    if detected_topics:
        main_topic = detected_topics[0][0]
        if main_topic == "machine_learning":
            intro_keywords = ["machine learning", "artificial intelligence", "technology"]
        elif main_topic == "mathematics":
            intro_keywords = ["mathematics", "math", "education"]
        elif main_topic == "programming":
            intro_keywords = ["programming", "coding", "software development"]
        elif main_topic == "business":
            intro_keywords = ["business", "management", "strategy"]
        elif main_topic == "science":
            intro_keywords = ["science", "research", "analysis"]
        elif main_topic == "technology":
            intro_keywords = ["technology", "innovation", "digital"]
    
    # Create multiple slides based on content
    content_chunks = text.split('\n\n')
    slide_count = min(5, len(content_chunks))  # Max 5 slides
    
    for i in range(slide_count):
        if i < len(content_chunks):
            chunk = content_chunks[i].strip()
            if len(chunk) > 50:  # Only meaningful chunks
                # Determine keywords for this slide
                slide_keywords = []
                
                # Add topic-specific keywords
                if detected_topics:
                    main_topic = detected_topics[0][0]
                    if main_topic == "machine_learning":
                        slide_keywords = ["machine learning", "algorithm", "data analysis"]
                    elif main_topic == "mathematics":
                        slide_keywords = ["mathematics", "equation", "calculation"]
                    elif main_topic == "programming":
                        slide_keywords = ["programming", "code", "software"]
                    elif main_topic == "business":
                        slide_keywords = ["business", "strategy", "management"]
                    elif main_topic == "science":
                        slide_keywords = ["science", "research", "experiment"]
                    elif main_topic == "technology":
                        slide_keywords = ["technology", "innovation", "system"]
                
                # Add content-specific keywords
                chunk_lower = chunk.lower()
                if "introduction" in chunk_lower or "overview" in chunk_lower:
                    slide_keywords.extend(["introduction", "overview", "beginning"])
                elif "concept" in chunk_lower or "theory" in chunk_lower:
                    slide_keywords.extend(["concept", "theory", "idea"])
                elif "example" in chunk_lower or "case" in chunk_lower:
                    slide_keywords.extend(["example", "case study", "demonstration"])
                elif "application" in chunk_lower or "use" in chunk_lower:
                    slide_keywords.extend(["application", "usage", "implementation"])
                elif "conclusion" in chunk_lower or "summary" in chunk_lower:
                    slide_keywords.extend(["conclusion", "summary", "ending"])
                
                # Ensure we have keywords
                if not slide_keywords:
                    slide_keywords = ["education", "learning", "presentation"]
                
                slides.append({
                    "title": f"Slide {i+1}",
                    "script": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                    "image_keywords": slide_keywords[:3]  # Limit to 3 keywords
                })
    
    # Ensure we have at least 3 slides
    while len(slides) < 3:
        slides.append({
            "title": f"Additional Content {len(slides)+1}",
            "script": "Additional content and information",
            "image_keywords": ["education", "learning", "content"]
        })
    
    return {
        "lecture_title": title or title_line,
        "introduction": {
            "script": f"Welcome to {title_line}",
            "image_keywords": intro_keywords
        },
        "slides": slides,
        "conclusion": {
            "script": "Thank you for watching this comprehensive lecture",
            "image_keywords": ["conclusion", "thank you", "completion"]
        }
    }

def generate_optimal_image(keywords):
    """Generate image with enhanced keyword processing"""
    if not keywords:
        keywords = ["education", "learning"]
    
    # Process keywords to be more specific
    processed_keywords = []
    for keyword in keywords:
        # Remove common words and make more specific
        if keyword.lower() not in ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"]:
            processed_keywords.append(keyword)
    
    # Use the first meaningful keyword
    search_keyword = processed_keywords[0] if processed_keywords else keywords[0]
    
    print(f"   Generating image for: {search_keyword}")
    
    # Try Stability AI first (best for specific content)
    if os.getenv("STABILITY_API_KEY"):
        try:
            result = generate_stability_image(search_keyword)
            if result and result.get("success"):
                print(f"   OK Stability AI: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Stability AI error: {e}")
    
    # Try Pexels (good for diverse content)
    if os.getenv("PEXELS_API_KEY"):
        try:
            result = generate_pexels_image(search_keyword)
            if result and result.get("success"):
                print(f"   OK Pexels: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Pexels error: {e}")
    
    # Try Unsplash (backup)
    if os.getenv("UNSPLASH_ACCESS_KEY"):
        try:
            result = generate_unsplash_image(search_keyword)
            if result and result.get("success"):
                print(f"   OK Unsplash: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Unsplash error: {e}")
    
    # Fallback to default image
    return create_default_image(search_keyword)

def generate_stability_image(prompt):
    """Generate image using Stability AI with enhanced prompts"""
    try:
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        # Enhance prompt for better results
        enhanced_prompt = f"professional {prompt}, high quality, educational, clear, detailed"
        
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "text_prompts": [{"text": enhanced_prompt, "weight": 1}],
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
    """Generate image using Pexels with enhanced search"""
    try:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        # Enhance query for better results
        enhanced_query = f"{query} professional education"
        
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": api_key}
        params = {"query": enhanced_query, "per_page": 1, "orientation": "landscape"}
        
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
    """Generate image using Unsplash with enhanced search"""
    try:
        access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if not access_key:
            return {"success": False, "error": "No API key"}
        
        # Enhance query for better results
        enhanced_query = f"{query} professional education"
        
        url = "https://api.unsplash.com/search/photos"
        headers = {"Authorization": f"Client-ID {access_key}"}
        params = {"query": enhanced_query, "per_page": 1, "orientation": "landscape"}
        
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

def create_enhanced_slide(script, tmpdir, slide_num, img_path=None):
    """Create enhanced slide with better processing"""
    try:
        # Create slide image
        frame_path = os.path.join(tmpdir, f"enhanced_slide_{slide_num:03d}.png")
        
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
        audio_path = os.path.join(tmpdir, f"enhanced_audio_{slide_num:03d}.mp3")
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

def make_enhanced_lecture_video(src_path: str, out_dir: str, title: str = None):
    """Create lecture video with enhanced content analysis and diverse images"""
    print("=" * 60)
    print("TAO VIDEO BAI GIANG NANG CAO")
    print("=" * 60)
    
    start_time = time.time()
    
    # Check APIs
    apis_available = {
        "pexels": bool(os.getenv("PEXELS_API_KEY")),
        "unsplash": bool(os.getenv("UNSPLASH_ACCESS_KEY")),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
        "stability": bool(os.getenv("STABILITY_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY"))
    }
    
    print(f"APIs available: {[k for k, v in apis_available.items() if v]}")
    
    # Create output directory
    os.makedirs(out_dir, exist_ok=True)
    
    # Step 1: Extract content
    print("Step 1/5: Extracting content...")
    extract_start = time.time()
    raw = extract_text_from_file(src_path)
    raw = clean_text(raw)
    if not raw:
        raise ValueError("Cannot extract content from document")
    print(f"Content extracted in {time.time() - extract_start:.1f}s")
    
    # Step 2: Enhanced content analysis
    print("Step 2/5: Analyzing content for diverse slides...")
    analysis_start = time.time()
    lecture_data = create_diverse_slides_from_content(raw)
    print(f"Analysis completed in {time.time() - analysis_start:.1f}s")
    print(f"Created {len(lecture_data['slides'])} diverse slides")
    
    # Step 3: Generate diverse images
    print("Step 3/5: Generating diverse images...")
    image_start = time.time()
    tmpdir = tempfile.mkdtemp(prefix="enhanced_lecture_")
    
    # Generate images for all slides
    slide_images = []
    for i, slide in enumerate(lecture_data["slides"]):
        print(f"   Generating image for slide {i+1}: {slide['image_keywords']}")
        img_path = generate_optimal_image(slide["image_keywords"])
        slide_images.append(img_path)
    
    # Generate introduction and conclusion images
    intro_img = generate_optimal_image(lecture_data["introduction"]["image_keywords"])
    conclusion_img = generate_optimal_image(lecture_data["conclusion"]["image_keywords"])
    
    print(f"Images generated in {time.time() - image_start:.1f}s")
    
    # Step 4: Create enhanced slides
    print("Step 4/5: Creating enhanced slides...")
    slide_start = time.time()
    clips = []
    timeline = []
    cur_t = 0.0
    
    # Introduction
    print("   Creating introduction slide...")
    intro_clip = create_enhanced_slide(
        lecture_data["introduction"]["script"], 
        tmpdir, 0, img_path=intro_img
    )
    if intro_clip:
        clips.append(intro_clip)
        timeline.append((cur_t, cur_t + intro_clip.duration, lecture_data["introduction"]["script"]))
        cur_t += intro_clip.duration
    
    # Main slides
    for i, slide_data in enumerate(lecture_data["slides"], 1):
        print(f"   Creating slide {i}: {slide_data['title']}")
        slide_img = slide_images[i-1] if i-1 < len(slide_images) else None
        slide_clip = create_enhanced_slide(
            slide_data["script"], 
            tmpdir, i, img_path=slide_img
        )
        if slide_clip:
            clips.append(slide_clip)
            timeline.append((cur_t, cur_t + slide_clip.duration, slide_data["script"]))
            cur_t += slide_clip.duration
    
    # Conclusion
    print("   Creating conclusion slide...")
    conclusion_clip = create_enhanced_slide(
        lecture_data["conclusion"]["script"], 
        tmpdir, len(lecture_data["slides"]) + 1, img_path=conclusion_img
    )
    if conclusion_clip:
        clips.append(conclusion_clip)
        timeline.append((cur_t, cur_t + conclusion_clip.duration, lecture_data["conclusion"]["script"]))
        cur_t += conclusion_clip.duration
    
    print(f"Slides created in {time.time() - slide_start:.1f}s")
    
    # Step 5: Render video
    print("Step 5/5: Rendering enhanced video...")
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
    print(f"Enhanced with diverse, content-matched images!")
    
    return {
        "video_path": out_video,
        "caption_path": out_vtt,
        "script_text": raw,
        "lecture_info": {
            "title": lecture_data["lecture_title"],
            "total_slides": len(clips),
            "total_duration_seconds": cur_t,
            "apis_used": [k for k, v in apis_available.items() if v],
            "image_generator": "Enhanced Multi-API System with Content Analysis",
            "processing_time": total_time,
            "slides_created": len(lecture_data["slides"])
        }
    }

if __name__ == "__main__":
    # Test the enhanced system
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
    
    # Test enhanced video creation
    result = make_enhanced_lecture_video(temp_file.name, "test_output", "Test Enhanced Video")
    
    print(f"\nEnhanced video created: {result['video_path']}")
    print(f"Processing time: {result['lecture_info']['processing_time']:.1f}s")
    print(f"Slides created: {result['lecture_info']['slides_created']}")
    
    # Clean up
    os.unlink(temp_file.name)
