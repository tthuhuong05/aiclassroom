#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Diverse Content-Matched Image Generation System
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

def extract_diverse_concepts_from_text(text):
    """Extract diverse concepts automatically from text"""
    if not text:
        return []
    
    # Define comprehensive concept patterns
    concept_patterns = {
        'mathematics': [
            r'\b(?:linear algebra|matrix|vector|calculus|derivative|integral|equation|formula|statistics|probability)\b',
            r'\b(?:mathematical|mathematics|math|algebraic|geometric|analytical|numerical|computational)\b',
            r'\b(?:graph|chart|function|variable|constant|coefficient|polynomial|trigonometric)\b'
        ],
        'machine_learning': [
            r'\b(?:machine learning|neural network|algorithm|model|training|data|classification|regression|deep learning)\b',
            r'\b(?:artificial intelligence|AI|ML|supervised|unsupervised|reinforcement learning)\b',
            r'\b(?:dataset|feature|label|clustering|prediction|accuracy|precision|recall)\b'
        ],
        'programming': [
            r'\b(?:programming|code|software|development|python|java|function|variable|loop|algorithm)\b',
            r'\b(?:coding|programming language|software engineering|computer science)\b',
            r'\b(?:API|framework|library|module|package|import|export|debugging)\b'
        ],
        'business': [
            r'\b(?:business|management|strategy|marketing|finance|economics|organization|leadership)\b',
            r'\b(?:market|revenue|profit|investment|entrepreneurship|corporate)\b',
            r'\b(?:analysis|evaluation|assessment|measurement|KPI|metric|performance)\b'
        ],
        'science': [
            r'\b(?:science|research|experiment|theory|hypothesis|analysis|scientific method)\b',
            r'\b(?:physics|chemistry|biology|laboratory|scientific|empirical)\b',
            r'\b(?:discovery|innovation|study|investigation|observation|data)\b'
        ],
        'technology': [
            r'\b(?:technology|tech|innovation|digital|computer|software|hardware|system)\b',
            r'\b(?:IT|information technology|cybersecurity|database|network)\b',
            r'\b(?:cloud|virtualization|container|microservice|deployment|automation)\b'
        ],
        'data_analysis': [
            r'\b(?:data analysis|data science|big data|analytics|visualization|statistics)\b',
            r'\b(?:database|data mining|data processing|data modeling)\b',
            r'\b(?:chart|graph|plot|visualization|dashboard|report)\b'
        ],
        'engineering': [
            r'\b(?:engineering|design|construction|mechanical|electrical|civil|chemical)\b',
            r'\b(?:system|process|optimization|efficiency|performance|quality)\b',
            r'\b(?:innovation|technology|automation|control|monitoring)\b'
        ]
    }
    
    # Extract concepts
    detected_concepts = []
    text_lower = text.lower()
    
    for concept, patterns in concept_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                detected_concepts.append(concept)
                break
    
    return list(set(detected_concepts))  # Remove duplicates

def generate_diverse_keywords_for_section(text_section, concepts, section_index):
    """Generate diverse keywords for each section based on content and concepts"""
    if not text_section or not concepts:
        return ["diverse content", "document analysis"]
    
    text_lower = text_section.lower()
    
    # Define diverse keyword patterns for each concept
    diverse_keyword_patterns = {
        'mathematics': [
            r'\b(?:equation|formula|calculation|graph|chart|function|variable|constant|coefficient)\b',
            r'\b(?:linear|quadratic|exponential|logarithmic|trigonometric|geometric)\b',
            r'\b(?:matrix|vector|scalar|determinant|eigenvalue|eigenvector)\b',
            r'\b(?:derivative|integral|limit|continuity|differentiation|integration)\b',
            r'\b(?:statistics|probability|distribution|regression|correlation)\b'
        ],
        'machine_learning': [
            r'\b(?:algorithm|model|training|testing|validation|prediction|classification)\b',
            r'\b(?:neural|network|layer|node|weight|bias|activation|backpropagation)\b',
            r'\b(?:dataset|feature|label|supervised|unsupervised|clustering|regression)\b',
            r'\b(?:accuracy|precision|recall|f1-score|confusion matrix|overfitting)\b',
            r'\b(?:deep learning|convolutional|recurrent|transformer|attention)\b'
        ],
        'programming': [
            r'\b(?:function|method|class|object|variable|constant|loop|condition)\b',
            r'\b(?:array|list|dictionary|string|integer|float|boolean|null)\b',
            r'\b(?:syntax|semantic|compiler|interpreter|debugging|testing)\b',
            r'\b(?:API|framework|library|module|package|import|export)\b',
            r'\b(?:algorithm|data structure|optimization|performance)\b'
        ],
        'business': [
            r'\b(?:strategy|planning|management|leadership|organization|team)\b',
            r'\b(?:marketing|advertising|promotion|brand|customer|market)\b',
            r'\b(?:finance|budget|revenue|profit|investment|capital)\b',
            r'\b(?:analysis|evaluation|assessment|measurement|KPI|metric)\b',
            r'\b(?:innovation|growth|expansion|scaling|competition)\b'
        ],
        'science': [
            r'\b(?:hypothesis|theory|experiment|observation|data|analysis)\b',
            r'\b(?:research|study|investigation|discovery|innovation)\b',
            r'\b(?:laboratory|equipment|instrument|measurement|result)\b',
            r'\b(?:peer review|publication|journal|conference|presentation)\b',
            r'\b(?:methodology|procedure|protocol|standard|validation)\b'
        ],
        'technology': [
            r'\b(?:system|platform|application|software|hardware|database)\b',
            r'\b(?:network|server|client|protocol|interface|API)\b',
            r'\b(?:security|encryption|authentication|authorization|firewall)\b',
            r'\b(?:cloud|virtualization|container|microservice|deployment)\b',
            r'\b(?:automation|integration|optimization|scalability|reliability)\b'
        ],
        'data_analysis': [
            r'\b(?:data|dataset|analysis|analytics|visualization|statistics)\b',
            r'\b(?:chart|graph|plot|dashboard|report|insight)\b',
            r'\b(?:mining|processing|modeling|prediction|forecasting)\b',
            r'\b(?:big data|machine learning|artificial intelligence)\b',
            r'\b(?:trend|pattern|correlation|regression|classification)\b'
        ],
        'engineering': [
            r'\b(?:design|construction|mechanical|electrical|civil|chemical)\b',
            r'\b(?:system|process|optimization|efficiency|performance|quality)\b',
            r'\b(?:innovation|technology|automation|control|monitoring)\b',
            r'\b(?:materials|components|assembly|manufacturing|production)\b',
            r'\b(?:safety|reliability|maintenance|testing|validation)\b'
        ]
    }
    
    # Extract keywords based on detected concepts
    all_keywords = []
    for concept in concepts:
        if concept in diverse_keyword_patterns:
            for pattern in diverse_keyword_patterns[concept]:
                matches = re.findall(pattern, text_lower)
                all_keywords.extend(matches)
    
    # Remove duplicates and create diverse sets
    unique_keywords = list(set(all_keywords))
    
    # Create diverse keyword sets for different sections
    if section_index == 0:
        # Introduction - use general concepts
        keywords = unique_keywords[:2] if unique_keywords else ["introduction", "overview"]
    elif section_index == 1:
        # First main section - use specific technical terms
        keywords = unique_keywords[:3] if unique_keywords else ["main concept", "technical details"]
    elif section_index == 2:
        # Second main section - use different technical terms
        keywords = unique_keywords[1:4] if len(unique_keywords) > 1 else ["advanced concept", "detailed analysis"]
    else:
        # Additional sections - use remaining terms
        keywords = unique_keywords[2:5] if len(unique_keywords) > 2 else ["additional content", "further analysis"]
    
    # Ensure we have diverse keywords
    if not keywords:
        concept_fallbacks = {
            'mathematics': ['mathematical equations', 'formulas', 'calculations', 'graphs', 'charts'],
            'machine_learning': ['machine learning', 'algorithms', 'data analysis', 'neural networks', 'AI models'],
            'programming': ['programming code', 'software development', 'algorithms', 'data structures', 'APIs'],
            'business': ['business strategy', 'management', 'analysis', 'marketing', 'finance'],
            'science': ['scientific research', 'experiments', 'analysis', 'laboratory', 'discovery'],
            'technology': ['technology systems', 'software', 'innovation', 'automation', 'digital'],
            'data_analysis': ['data analysis', 'visualization', 'statistics', 'charts', 'insights'],
            'engineering': ['engineering design', 'systems', 'optimization', 'innovation', 'technology']
        }
        
        # Get fallback keywords for detected concepts
        fallback_keywords = []
        for concept in concepts:
            if concept in concept_fallbacks:
                fallback_keywords.extend(concept_fallbacks[concept][:2])
        
        keywords = fallback_keywords[:3] if fallback_keywords else ['diverse content', 'document analysis', 'main topic']
    
    return keywords[:3]  # Limit to 3 keywords for diversity

def analyze_content_for_diverse_images(text):
    """Analyze content to create diverse, content-matched images"""
    print("Analyzing content for DIVERSE images...")
    
    # Extract diverse concepts
    concepts = extract_diverse_concepts_from_text(text)
    print(f"Detected diverse concepts: {concepts}")
    
    # Get main concept
    main_concept = concepts[0] if concepts else 'general'
    
    # Split content into meaningful sections for diverse images
    sections = text.split('\n\n')
    meaningful_sections = [s.strip() for s in sections if len(s.strip()) > 50]
    
    # Create diverse slides with different image focuses
    slides = []
    for i, section in enumerate(meaningful_sections[:5]):  # Max 5 slides for diversity
        # Generate diverse keywords for each section
        diverse_keywords = generate_diverse_keywords_for_section(section, concepts, i)
        
        slides.append({
            "title": f"Diverse Content {i+1}",
            "script": section[:200] + "..." if len(section) > 200 else section,
            "image_keywords": diverse_keywords
        })
    
    # Ensure we have at least 4 diverse slides
    while len(slides) < 4:
        diverse_keywords = generate_diverse_keywords_for_section(text, concepts, len(slides))
        slides.append({
            "title": f"Additional Diverse Content {len(slides)+1}",
            "script": "Additional diverse content analysis",
            "image_keywords": diverse_keywords
        })
    
    return {
        "lecture_title": "Diverse Content Analysis",
        "main_concept": main_concept,
        "detected_concepts": concepts,
        "introduction": {
            "script": f"Welcome to diverse content analysis focusing on {main_concept}",
            "image_keywords": generate_diverse_keywords_for_section(text, concepts, 0)
        },
        "slides": slides,
        "conclusion": {
            "script": "Thank you for this diverse learning experience",
            "image_keywords": ["conclusion", "summary", "completion"]
        }
    }

def generate_diverse_image(keywords, image_index):
    """Generate diverse image with enhanced content matching and no people"""
    if not keywords:
        keywords = ["diverse content", "document analysis"]
    
    # Use different keywords for diversity
    search_keyword = keywords[image_index % len(keywords)] if keywords else "diverse content"
    
    print(f"   Generating DIVERSE image {image_index+1} for: {search_keyword}")
    
    # Try Stability AI first (best for diverse generation)
    if os.getenv("STABILITY_API_KEY"):
        try:
            result = generate_diverse_stability_image(search_keyword, image_index)
            if result and result.get("success"):
                print(f"   OK Diverse Stability AI: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Stability AI error: {e}")
    
    # Try Pexels (good for diverse content)
    if os.getenv("PEXELS_API_KEY"):
        try:
            result = generate_diverse_pexels_image(search_keyword, image_index)
            if result and result.get("success"):
                print(f"   OK Diverse Pexels: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Pexels error: {e}")
    
    # Try Unsplash (backup)
    if os.getenv("UNSPLASH_ACCESS_KEY"):
        try:
            result = generate_diverse_unsplash_image(search_keyword, image_index)
            if result and result.get("success"):
                print(f"   OK Diverse Unsplash: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Unsplash error: {e}")
    
    # Fallback to diverse default image
    return create_diverse_default_image(search_keyword, image_index)

def generate_diverse_stability_image(prompt, image_index):
    """Generate diverse image using Stability AI with enhanced prompts"""
    try:
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        # Create diverse-focused prompt with no people
        diverse_prompt = f"diverse {prompt}, professional, educational, clear, detailed, specific, high quality, content-matched, no people, no humans, technical, analytical, abstract, conceptual"
        
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Vary parameters for diversity
        cfg_scale = 8 + (image_index % 2)  # 8 or 9
        steps = 25 + (image_index % 5)     # 25-29 steps
        
        data = {
            "text_prompts": [{"text": diverse_prompt, "weight": 1}],
            "cfg_scale": cfg_scale,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": steps
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

def generate_diverse_pexels_image(query, image_index):
    """Generate diverse image using Pexels with enhanced search"""
    try:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        # Create diverse query with no people
        diverse_query = f"{query} diverse professional education no people technical"
        
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": api_key}
        params = {
            "query": diverse_query, 
            "per_page": 1, 
            "orientation": "landscape",
            "page": (image_index % 3) + 1  # Vary page for diversity
        }
        
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

def generate_diverse_unsplash_image(query, image_index):
    """Generate diverse image using Unsplash with enhanced search"""
    try:
        access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if not access_key:
            return {"success": False, "error": "No API key"}
        
        # Create diverse query with no people
        diverse_query = f"{query} diverse professional education no people technical"
        
        url = "https://api.unsplash.com/search/photos"
        headers = {"Authorization": f"Client-ID {access_key}"}
        params = {
            "query": diverse_query, 
            "per_page": 1, 
            "orientation": "landscape",
            "page": (image_index % 3) + 1  # Vary page for diversity
        }
        
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

def create_diverse_default_image(keyword, image_index):
    """Create diverse default image when APIs fail"""
    try:
        # Create diverse colored images
        colors = [
            (60, 120, 180),   # Blue
            (120, 60, 180),   # Purple
            (180, 120, 60),   # Orange
            (60, 180, 120),   # Green
            (180, 60, 120)    # Pink
        ]
        
        color = colors[image_index % len(colors)]
        img = Image.new('RGB', (1024, 1024), color=color)
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Draw diverse text
        text = f"Diverse: {keyword.replace('_', ' ').title()}"
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
        print(f"Error creating diverse default image: {e}")
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

def create_diverse_slide(script, tmpdir, slide_num, img_path=None):
    """Create diverse slide with better processing"""
    try:
        # Create slide image
        frame_path = os.path.join(tmpdir, f"diverse_slide_{slide_num:03d}.png")
        
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
        audio_path = os.path.join(tmpdir, f"diverse_audio_{slide_num:03d}.mp3")
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
        print(f"Error creating diverse slide {slide_num}: {e}")
        return None

def make_diverse_lecture_video(src_path: str, out_dir: str, title: str = None):
    """Create lecture video with diverse, content-matched images"""
    print("=" * 60)
    print("TAO VIDEO BAI GIANG DA DANG")
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
    
    # Step 1: Extract content
    print("Step 1/5: Extracting content...")
    extract_start = time.time()
    raw = extract_text_from_file(src_path)
    raw = clean_text(raw)
    if not raw:
        raise ValueError("Cannot extract content from document")
    print(f"Content extracted in {time.time() - extract_start:.1f}s")
    
    # Step 2: Diverse content analysis
    print("Step 2/5: Analyzing content for DIVERSE images...")
    analysis_start = time.time()
    lecture_data = analyze_content_for_diverse_images(raw)
    print(f"Diverse analysis completed in {time.time() - analysis_start:.1f}s")
    print(f"Created {len(lecture_data['slides'])} DIVERSE slides")
    print(f"Main concept: {lecture_data.get('main_concept', 'general')}")
    print(f"Detected concepts: {lecture_data.get('detected_concepts', [])}")
    
    # Step 3: Generate diverse images
    print("Step 3/5: Generating DIVERSE images...")
    image_start = time.time()
    tmpdir = tempfile.mkdtemp(prefix="diverse_lecture_")
    
    # Generate diverse images for all slides
    slide_images = []
    for i, slide in enumerate(lecture_data["slides"]):
        print(f"   Generating DIVERSE image for slide {i+1}: {slide['image_keywords']}")
        img_path = generate_diverse_image(slide["image_keywords"], i)
        slide_images.append(img_path)
    
    # Generate diverse introduction and conclusion images
    intro_img = generate_diverse_image(lecture_data["introduction"]["image_keywords"], 0)
    conclusion_img = generate_diverse_image(lecture_data["conclusion"]["image_keywords"], len(lecture_data["slides"]) + 1)
    
    print(f"Diverse images generated in {time.time() - image_start:.1f}s")
    
    # Step 4: Create diverse slides
    print("Step 4/5: Creating DIVERSE slides...")
    slide_start = time.time()
    clips = []
    timeline = []
    cur_t = 0.0
    
    # Introduction
    print("   Creating diverse introduction slide...")
    intro_clip = create_diverse_slide(
        lecture_data["introduction"]["script"], 
        tmpdir, 0, img_path=intro_img
    )
    if intro_clip:
        clips.append(intro_clip)
        timeline.append((cur_t, cur_t + intro_clip.duration, lecture_data["introduction"]["script"]))
        cur_t += intro_clip.duration
    
    # Main slides
    for i, slide_data in enumerate(lecture_data["slides"], 1):
        print(f"   Creating diverse slide {i}: {slide_data['title']}")
        slide_img = slide_images[i-1] if i-1 < len(slide_images) else None
        slide_clip = create_diverse_slide(
            slide_data["script"], 
            tmpdir, i, img_path=slide_img
        )
        if slide_clip:
            clips.append(slide_clip)
            timeline.append((cur_t, cur_t + slide_clip.duration, slide_data["script"]))
            cur_t += slide_clip.duration
    
    # Conclusion
    print("   Creating diverse conclusion slide...")
    conclusion_clip = create_diverse_slide(
        lecture_data["conclusion"]["script"], 
        tmpdir, len(lecture_data["slides"]) + 1, img_path=conclusion_img
    )
    if conclusion_clip:
        clips.append(conclusion_clip)
        timeline.append((cur_t, cur_t + conclusion_clip.duration, lecture_data["conclusion"]["script"]))
        cur_t += conclusion_clip.duration
    
    print(f"Diverse slides created in {time.time() - slide_start:.1f}s")
    
    # Step 5: Render video
    print("Step 5/5: Rendering DIVERSE video...")
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
    
    print(f"Diverse video rendered in {render_time:.1f}s")
    print(f"Total time: {total_time:.1f}s")
    print(f"Final video: {out_video}")
    print(f"Duration: {cur_t:.1f} seconds")
    print(f"Total slides: {len(clips)}")
    print(f"DIVERSE with content-matched images - NO PEOPLE!")
    
    return {
        "video_path": out_video,
        "caption_path": out_vtt,
        "script_text": raw,
        "lecture_info": {
            "title": lecture_data["lecture_title"],
            "total_slides": len(clips),
            "total_duration_seconds": cur_t,
            "apis_used": [k for k, v in apis_available.items() if v],
            "image_generator": "Diverse Multi-API System with Content-Matched Images (No People)",
            "processing_time": total_time,
            "slides_created": len(lecture_data["slides"]),
            "main_concept": lecture_data.get("main_concept", "general"),
            "detected_concepts": lecture_data.get("detected_concepts", [])
        }
    }

if __name__ == "__main__":
    # Test the diverse system
    import tempfile
    
    # Create test content
    test_content = """
    # Mathematics for Machine Learning
    
    Mathematics is the foundation of machine learning. Understanding mathematical concepts is crucial for developing effective ML algorithms.
    
    ## Linear Algebra
    
    Linear algebra provides the mathematical framework for machine learning. Vectors and matrices are fundamental concepts.
    
    ## Calculus
    
    Calculus helps us understand optimization in machine learning. Derivatives and gradients are essential for training models.
    
    ## Statistics
    
    Statistics provides the tools for understanding data and making predictions. Probability theory is fundamental to ML.
    
    ## Conclusion
    
    A strong mathematical foundation is essential for success in machine learning.
    """
    
    # Create test file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
    temp_file.write(test_content)
    temp_file.close()
    
    # Test diverse video creation
    result = make_diverse_lecture_video(temp_file.name, "test_output", "Test Diverse Video")
    
    print(f"\nDiverse video created: {result['video_path']}")
    print(f"Processing time: {result['lecture_info']['processing_time']:.1f}s")
    print(f"Slides created: {result['lecture_info']['slides_created']}")
    print(f"Main concept: {result['lecture_info']['main_concept']}")
    print(f"Detected concepts: {result['lecture_info']['detected_concepts']}")
    
    # Clean up
    os.unlink(temp_file.name)
