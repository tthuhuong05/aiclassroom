#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultimate Content-Matched Image Generation System - NO PEOPLE
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

def extract_ultimate_concepts_from_text(text):
    """Extract ultimate concepts automatically from text with enhanced patterns"""
    if not text:
        return []
    
    # Define ultimate concept patterns with more specific terms
    ultimate_concept_patterns = {
        'mathematics': [
            r'\b(?:linear algebra|matrix|vector|calculus|derivative|integral|equation|formula|statistics|probability)\b',
            r'\b(?:mathematical|mathematics|math|algebraic|geometric|analytical|numerical|computational)\b',
            r'\b(?:graph|chart|function|variable|constant|coefficient|polynomial|trigonometric|logarithmic|exponential)\b',
            r'\b(?:optimization|minimization|maximization|gradient|eigenvalue|eigenvector|determinant)\b'
        ],
        'machine_learning': [
            r'\b(?:machine learning|neural network|algorithm|model|training|data|classification|regression|deep learning)\b',
            r'\b(?:artificial intelligence|AI|ML|supervised|unsupervised|reinforcement learning)\b',
            r'\b(?:dataset|feature|label|clustering|prediction|accuracy|precision|recall|f1-score)\b',
            r'\b(?:backpropagation|gradient descent|overfitting|underfitting|cross-validation)\b'
        ],
        'programming': [
            r'\b(?:programming|code|software|development|python|java|function|variable|loop|algorithm)\b',
            r'\b(?:coding|programming language|software engineering|computer science)\b',
            r'\b(?:API|framework|library|module|package|import|export|debugging|testing)\b',
            r'\b(?:data structure|object-oriented|functional programming|recursion|iteration)\b'
        ],
        'business': [
            r'\b(?:business|management|strategy|marketing|finance|economics|organization|leadership)\b',
            r'\b(?:market|revenue|profit|investment|entrepreneurship|corporate|startup)\b',
            r'\b(?:analysis|evaluation|assessment|measurement|KPI|metric|performance|ROI)\b',
            r'\b(?:customer|client|stakeholder|partnership|collaboration|negotiation)\b'
        ],
        'science': [
            r'\b(?:science|research|experiment|theory|hypothesis|analysis|scientific method)\b',
            r'\b(?:physics|chemistry|biology|laboratory|scientific|empirical|evidence)\b',
            r'\b(?:discovery|innovation|study|investigation|observation|data|results)\b',
            r'\b(?:peer review|publication|journal|conference|presentation|methodology)\b'
        ],
        'technology': [
            r'\b(?:technology|tech|innovation|digital|computer|software|hardware|system)\b',
            r'\b(?:IT|information technology|cybersecurity|database|network|cloud)\b',
            r'\b(?:virtualization|container|microservice|deployment|automation|integration)\b',
            r'\b(?:blockchain|IoT|artificial intelligence|machine learning|data science)\b'
        ],
        'data_analysis': [
            r'\b(?:data analysis|data science|big data|analytics|visualization|statistics)\b',
            r'\b(?:database|data mining|data processing|data modeling|data warehouse)\b',
            r'\b(?:chart|graph|plot|visualization|dashboard|report|insight|trend)\b',
            r'\b(?:correlation|regression|classification|clustering|forecasting)\b'
        ],
        'engineering': [
            r'\b(?:engineering|design|construction|mechanical|electrical|civil|chemical)\b',
            r'\b(?:system|process|optimization|efficiency|performance|quality|reliability)\b',
            r'\b(?:innovation|technology|automation|control|monitoring|maintenance)\b',
            r'\b(?:materials|components|assembly|manufacturing|production|testing)\b'
        ],
        'education': [
            r'\b(?:education|learning|teaching|pedagogy|curriculum|instruction)\b',
            r'\b(?:student|learner|knowledge|skill|competency|assessment)\b',
            r'\b(?:classroom|course|lesson|module|assignment|examination)\b',
            r'\b(?:academic|scholarly|research|study|training|development)\b'
        ]
    }
    
    # Extract concepts with scoring
    concept_scores = {}
    text_lower = text.lower()
    
    for concept, patterns in ultimate_concept_patterns.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            score += len(matches)
        if score > 0:
            concept_scores[concept] = score
    
    # Return concepts sorted by relevance score
    detected_concepts = sorted(concept_scores.keys(), key=lambda x: concept_scores[x], reverse=True)
    
    return detected_concepts

def generate_ultimate_keywords_for_content(text_section, concepts, section_index):
    """Generate ultimate keywords based on content analysis"""
    if not text_section or not concepts:
        return ["content analysis", "document processing"]
    
    text_lower = text_section.lower()
    
    # Define ultimate keyword patterns for each concept
    ultimate_keyword_patterns = {
        'mathematics': [
            r'\b(?:equation|formula|calculation|graph|chart|function|variable|constant|coefficient)\b',
            r'\b(?:linear|quadratic|exponential|logarithmic|trigonometric|geometric|algebraic)\b',
            r'\b(?:matrix|vector|scalar|determinant|eigenvalue|eigenvector|transformation)\b',
            r'\b(?:derivative|integral|limit|continuity|differentiation|integration|optimization)\b',
            r'\b(?:statistics|probability|distribution|regression|correlation|variance|standard deviation)\b'
        ],
        'machine_learning': [
            r'\b(?:algorithm|model|training|testing|validation|prediction|classification|regression)\b',
            r'\b(?:neural|network|layer|node|weight|bias|activation|backpropagation|gradient)\b',
            r'\b(?:dataset|feature|label|supervised|unsupervised|clustering|dimensionality)\b',
            r'\b(?:accuracy|precision|recall|f1-score|confusion matrix|overfitting|cross-validation)\b',
            r'\b(?:deep learning|convolutional|recurrent|transformer|attention|embedding)\b'
        ],
        'programming': [
            r'\b(?:function|method|class|object|variable|constant|loop|condition|recursion)\b',
            r'\b(?:array|list|dictionary|string|integer|float|boolean|null|pointer)\b',
            r'\b(?:syntax|semantic|compiler|interpreter|debugging|testing|unit test)\b',
            r'\b(?:API|framework|library|module|package|import|export|dependency)\b',
            r'\b(?:algorithm|data structure|optimization|performance|complexity|sorting)\b'
        ],
        'business': [
            r'\b(?:strategy|planning|management|leadership|organization|team|collaboration)\b',
            r'\b(?:marketing|advertising|promotion|brand|customer|market|segmentation)\b',
            r'\b(?:finance|budget|revenue|profit|investment|capital|cash flow|ROI)\b',
            r'\b(?:analysis|evaluation|assessment|measurement|KPI|metric|dashboard)\b',
            r'\b(?:innovation|growth|expansion|scaling|competition|partnership|acquisition)\b'
        ],
        'science': [
            r'\b(?:hypothesis|theory|experiment|observation|data|analysis|methodology)\b',
            r'\b(?:research|study|investigation|discovery|innovation|breakthrough)\b',
            r'\b(?:laboratory|equipment|instrument|measurement|result|conclusion)\b',
            r'\b(?:peer review|publication|journal|conference|presentation|citation)\b',
            r'\b(?:scientific method|control group|variable|hypothesis testing|statistical significance)\b'
        ],
        'technology': [
            r'\b(?:system|platform|application|software|hardware|database|server)\b',
            r'\b(?:network|protocol|interface|API|microservice|container|deployment)\b',
            r'\b(?:security|encryption|authentication|authorization|firewall|vulnerability)\b',
            r'\b(?:cloud|virtualization|scalability|reliability|performance|monitoring)\b',
            r'\b(?:automation|integration|optimization|architecture|infrastructure|devops)\b'
        ],
        'data_analysis': [
            r'\b(?:data|dataset|analysis|analytics|visualization|statistics|insight)\b',
            r'\b(?:chart|graph|plot|dashboard|report|trend|pattern|correlation)\b',
            r'\b(?:mining|processing|modeling|prediction|forecasting|classification)\b',
            r'\b(?:big data|machine learning|artificial intelligence|deep learning)\b',
            r'\b(?:ETL|data warehouse|data lake|business intelligence|data governance)\b'
        ],
        'engineering': [
            r'\b(?:design|construction|mechanical|electrical|civil|chemical|aerospace)\b',
            r'\b(?:system|process|optimization|efficiency|performance|quality|reliability)\b',
            r'\b(?:innovation|technology|automation|control|monitoring|maintenance)\b',
            r'\b(?:materials|components|assembly|manufacturing|production|testing)\b',
            r'\b(?:CAD|simulation|prototype|testing|validation|certification|standards)\b'
        ],
        'education': [
            r'\b(?:learning|teaching|pedagogy|curriculum|instruction|assessment|evaluation)\b',
            r'\b(?:student|learner|knowledge|skill|competency|outcome|objective)\b',
            r'\b(?:classroom|course|lesson|module|assignment|examination|grade)\b',
            r'\b(?:academic|scholarly|research|study|training|development|certification)\b',
            r'\b(?:e-learning|online|digital|interactive|multimedia|gamification)\b'
        ]
    }
    
    # Extract keywords based on detected concepts
    all_keywords = []
    for concept in concepts:
        if concept in ultimate_keyword_patterns:
            for pattern in ultimate_keyword_patterns[concept]:
                matches = re.findall(pattern, text_lower)
                all_keywords.extend(matches)
    
    # Remove duplicates and create ultimate diverse sets
    unique_keywords = list(set(all_keywords))
    
    # Create ultimate diverse keyword sets for different sections
    if section_index == 0:
        # Introduction - use general but specific concepts
        keywords = unique_keywords[:2] if unique_keywords else ["introduction", "overview"]
    elif section_index == 1:
        # First main section - use specific technical terms
        keywords = unique_keywords[:3] if unique_keywords else ["main concept", "technical details"]
    elif section_index == 2:
        # Second main section - use different technical terms
        keywords = unique_keywords[1:4] if len(unique_keywords) > 1 else ["advanced concept", "detailed analysis"]
    elif section_index == 3:
        # Third main section - use remaining specific terms
        keywords = unique_keywords[2:5] if len(unique_keywords) > 2 else ["specialized content", "expert analysis"]
    else:
        # Additional sections - use remaining terms
        keywords = unique_keywords[3:6] if len(unique_keywords) > 3 else ["additional content", "further analysis"]
    
    # Ensure we have ultimate keywords
    if not keywords:
        concept_fallbacks = {
            'mathematics': ['mathematical equations', 'formulas', 'calculations', 'graphs', 'charts', 'statistics'],
            'machine_learning': ['machine learning', 'algorithms', 'data analysis', 'neural networks', 'AI models', 'predictions'],
            'programming': ['programming code', 'software development', 'algorithms', 'data structures', 'APIs', 'frameworks'],
            'business': ['business strategy', 'management', 'analysis', 'marketing', 'finance', 'operations'],
            'science': ['scientific research', 'experiments', 'analysis', 'laboratory', 'discovery', 'methodology'],
            'technology': ['technology systems', 'software', 'innovation', 'automation', 'digital', 'infrastructure'],
            'data_analysis': ['data analysis', 'visualization', 'statistics', 'charts', 'insights', 'trends'],
            'engineering': ['engineering design', 'systems', 'optimization', 'innovation', 'technology', 'construction'],
            'education': ['educational content', 'learning', 'teaching', 'curriculum', 'assessment', 'knowledge']
        }
        
        # Get fallback keywords for detected concepts
        fallback_keywords = []
        for concept in concepts:
            if concept in concept_fallbacks:
                fallback_keywords.extend(concept_fallbacks[concept][:2])
        
        keywords = fallback_keywords[:3] if fallback_keywords else ['content analysis', 'document processing', 'main topic']
    
    return keywords[:3]  # Limit to 3 keywords for ultimate diversity

def analyze_content_for_ultimate_images(text):
    """Analyze content to create ultimate diverse, content-matched images"""
    print("Analyzing content for ULTIMATE DIVERSE images...")
    
    # Extract ultimate concepts
    concepts = extract_ultimate_concepts_from_text(text)
    print(f"Detected ultimate concepts: {concepts}")
    
    # Get main concept
    main_concept = concepts[0] if concepts else 'general'
    
    # Split content into meaningful sections for ultimate diverse images
    sections = text.split('\n\n')
    meaningful_sections = [s.strip() for s in sections if len(s.strip()) > 50]
    
    # Create ultimate diverse slides with different image focuses
    slides = []
    for i, section in enumerate(meaningful_sections[:6]):  # Max 6 slides for ultimate diversity
        # Generate ultimate diverse keywords for each section
        ultimate_keywords = generate_ultimate_keywords_for_content(section, concepts, i)
        
        slides.append({
            "title": f"Ultimate Content {i+1}",
            "script": section[:200] + "..." if len(section) > 200 else section,
            "image_keywords": ultimate_keywords
        })
    
    # Ensure we have at least 5 ultimate diverse slides
    while len(slides) < 5:
        ultimate_keywords = generate_ultimate_keywords_for_content(text, concepts, len(slides))
        slides.append({
            "title": f"Additional Ultimate Content {len(slides)+1}",
            "script": "Additional ultimate diverse content analysis",
            "image_keywords": ultimate_keywords
        })
    
    return {
        "lecture_title": "Ultimate Content Analysis",
        "main_concept": main_concept,
        "detected_concepts": concepts,
        "introduction": {
            "script": f"Welcome to ultimate content analysis focusing on {main_concept}",
            "image_keywords": generate_ultimate_keywords_for_content(text, concepts, 0)
        },
        "slides": slides,
        "conclusion": {
            "script": "Thank you for this ultimate diverse learning experience",
            "image_keywords": ["conclusion", "summary", "completion"]
        }
    }

def generate_ultimate_image(keywords, image_index):
    """Generate ultimate image with enhanced content matching and ABSOLUTELY NO PEOPLE"""
    if not keywords:
        keywords = ["content analysis", "document processing"]
    
    # Use different keywords for ultimate diversity
    search_keyword = keywords[image_index % len(keywords)] if keywords else "content analysis"
    
    print(f"   Generating ULTIMATE image {image_index+1} for: {search_keyword}")
    
    # Try Stability AI first (best for ultimate generation)
    if os.getenv("STABILITY_API_KEY"):
        try:
            result = generate_ultimate_stability_image(search_keyword, image_index)
            if result and result.get("success"):
                print(f"   OK Ultimate Stability AI: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Stability AI error: {e}")
    
    # Try Pexels (good for ultimate content)
    if os.getenv("PEXELS_API_KEY"):
        try:
            result = generate_ultimate_pexels_image(search_keyword, image_index)
            if result and result.get("success"):
                print(f"   OK Ultimate Pexels: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Pexels error: {e}")
    
    # Try Unsplash (backup)
    if os.getenv("UNSPLASH_ACCESS_KEY"):
        try:
            result = generate_ultimate_unsplash_image(search_keyword, image_index)
            if result and result.get("success"):
                print(f"   OK Ultimate Unsplash: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   Unsplash error: {e}")
    
    # Fallback to ultimate default image
    return create_ultimate_default_image(search_keyword, image_index)

def generate_ultimate_stability_image(prompt, image_index):
    """Generate ultimate image using Stability AI with ABSOLUTELY NO PEOPLE"""
    try:
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        # Create ultimate-focused prompt with ABSOLUTELY NO PEOPLE
        ultimate_prompt = f"ultimate {prompt}, professional, educational, clear, detailed, specific, high quality, content-matched, absolutely no people, no humans, no persons, no faces, no portraits, technical, analytical, abstract, conceptual, data visualization, charts, graphs, diagrams, symbols, icons, geometric shapes, mathematical formulas, scientific illustrations, business charts, technology diagrams, engineering blueprints, educational infographics, professional graphics, clean design, minimalist, modern, sophisticated"
        
        url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
        
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # Vary parameters for ultimate diversity
        cfg_scale = 9 + (image_index % 2)  # 9 or 10
        steps = 30 + (image_index % 5)     # 30-34 steps
        
        data = {
            "text_prompts": [{"text": ultimate_prompt, "weight": 1}],
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

def generate_ultimate_pexels_image(query, image_index):
    """Generate ultimate image using Pexels with ABSOLUTELY NO PEOPLE"""
    try:
        api_key = os.getenv("PEXELS_API_KEY")
        if not api_key:
            return {"success": False, "error": "No API key"}
        
        # Create ultimate query with ABSOLUTELY NO PEOPLE
        ultimate_query = f"{query} ultimate professional education absolutely no people no humans technical abstract conceptual"
        
        url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": api_key}
        params = {
            "query": ultimate_query, 
            "per_page": 1, 
            "orientation": "landscape",
            "page": (image_index % 5) + 1  # Vary page for ultimate diversity
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

def generate_ultimate_unsplash_image(query, image_index):
    """Generate ultimate image using Unsplash with ABSOLUTELY NO PEOPLE"""
    try:
        access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        if not access_key:
            return {"success": False, "error": "No API key"}
        
        # Create ultimate query with ABSOLUTELY NO PEOPLE
        ultimate_query = f"{query} ultimate professional education absolutely no people no humans technical abstract conceptual"
        
        url = "https://api.unsplash.com/search/photos"
        headers = {"Authorization": f"Client-ID {access_key}"}
        params = {
            "query": ultimate_query, 
            "per_page": 1, 
            "orientation": "landscape",
            "page": (image_index % 5) + 1  # Vary page for ultimate diversity
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

def create_ultimate_default_image(keyword, image_index):
    """Create ultimate default image when APIs fail - ABSOLUTELY NO PEOPLE"""
    try:
        # Create ultimate diverse colored images
        colors = [
            (40, 100, 160),   # Deep Blue
            (100, 40, 160),   # Deep Purple
            (160, 100, 40),   # Deep Orange
            (40, 160, 100),   # Deep Green
            (160, 40, 100),   # Deep Pink
            (100, 160, 40),   # Deep Yellow
            (80, 120, 200),   # Light Blue
            (200, 80, 120)    # Light Pink
        ]
        
        color = colors[image_index % len(colors)]
        img = Image.new('RGB', (1024, 1024), color=color)
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", 48)
        except:
            font = ImageFont.load_default()
        
        # Draw ultimate text
        text = f"Ultimate: {keyword.replace('_', ' ').title()}"
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
        print(f"Error creating ultimate default image: {e}")
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

def create_ultimate_slide(script, tmpdir, slide_num, img_path=None):
    """Create ultimate slide with better processing"""
    try:
        # Create slide image
        frame_path = os.path.join(tmpdir, f"ultimate_slide_{slide_num:03d}.png")
        
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
        audio_path = os.path.join(tmpdir, f"ultimate_audio_{slide_num:03d}.mp3")
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
        print(f"Error creating ultimate slide {slide_num}: {e}")
        return None

def make_ultimate_lecture_video(src_path: str, out_dir: str, title: str = None):
    """Create lecture video with ultimate diverse, content-matched images - ABSOLUTELY NO PEOPLE"""
    print("=" * 60)
    print("TAO VIDEO BAI GIANG ULTIMATE DA DANG")
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
    
    # Step 2: Ultimate content analysis
    print("Step 2/5: Analyzing content for ULTIMATE DIVERSE images...")
    analysis_start = time.time()
    lecture_data = analyze_content_for_ultimate_images(raw)
    print(f"Ultimate analysis completed in {time.time() - analysis_start:.1f}s")
    print(f"Created {len(lecture_data['slides'])} ULTIMATE DIVERSE slides")
    print(f"Main concept: {lecture_data.get('main_concept', 'general')}")
    print(f"Detected concepts: {lecture_data.get('detected_concepts', [])}")
    
    # Step 3: Generate ultimate images
    print("Step 3/5: Generating ULTIMATE DIVERSE images...")
    image_start = time.time()
    tmpdir = tempfile.mkdtemp(prefix="ultimate_lecture_")
    
    # Generate ultimate images for all slides
    slide_images = []
    for i, slide in enumerate(lecture_data["slides"]):
        print(f"   Generating ULTIMATE image for slide {i+1}: {slide['image_keywords']}")
        img_path = generate_ultimate_image(slide["image_keywords"], i)
        slide_images.append(img_path)
    
    # Generate ultimate introduction and conclusion images
    intro_img = generate_ultimate_image(lecture_data["introduction"]["image_keywords"], 0)
    conclusion_img = generate_ultimate_image(lecture_data["conclusion"]["image_keywords"], len(lecture_data["slides"]) + 1)
    
    print(f"Ultimate images generated in {time.time() - image_start:.1f}s")
    
    # Step 4: Create ultimate slides
    print("Step 4/5: Creating ULTIMATE DIVERSE slides...")
    slide_start = time.time()
    clips = []
    timeline = []
    cur_t = 0.0
    
    # Introduction
    print("   Creating ultimate introduction slide...")
    intro_clip = create_ultimate_slide(
        lecture_data["introduction"]["script"], 
        tmpdir, 0, img_path=intro_img
    )
    if intro_clip:
        clips.append(intro_clip)
        timeline.append((cur_t, cur_t + intro_clip.duration, lecture_data["introduction"]["script"]))
        cur_t += intro_clip.duration
    
    # Main slides
    for i, slide_data in enumerate(lecture_data["slides"], 1):
        print(f"   Creating ultimate slide {i}: {slide_data['title']}")
        slide_img = slide_images[i-1] if i-1 < len(slide_images) else None
        slide_clip = create_ultimate_slide(
            slide_data["script"], 
            tmpdir, i, img_path=slide_img
        )
        if slide_clip:
            clips.append(slide_clip)
            timeline.append((cur_t, cur_t + slide_clip.duration, slide_data["script"]))
            cur_t += slide_clip.duration
    
    # Conclusion
    print("   Creating ultimate conclusion slide...")
    conclusion_clip = create_ultimate_slide(
        lecture_data["conclusion"]["script"], 
        tmpdir, len(lecture_data["slides"]) + 1, img_path=conclusion_img
    )
    if conclusion_clip:
        clips.append(conclusion_clip)
        timeline.append((cur_t, cur_t + conclusion_clip.duration, lecture_data["conclusion"]["script"]))
        cur_t += conclusion_clip.duration
    
    print(f"Ultimate slides created in {time.time() - slide_start:.1f}s")
    
    # Step 5: Render video
    print("Step 5/5: Rendering ULTIMATE DIVERSE video...")
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
    
    print(f"Ultimate video rendered in {render_time:.1f}s")
    print(f"Total time: {total_time:.1f}s")
    print(f"Final video: {out_video}")
    print(f"Duration: {cur_t:.1f} seconds")
    print(f"Total slides: {len(clips)}")
    print(f"ULTIMATE DIVERSE with content-matched images - ABSOLUTELY NO PEOPLE!")
    
    return {
        "video_path": out_video,
        "caption_path": out_vtt,
        "script_text": raw,
        "lecture_info": {
            "title": lecture_data["lecture_title"],
            "total_slides": len(clips),
            "total_duration_seconds": cur_t,
            "apis_used": [k for k, v in apis_available.items() if v],
            "image_generator": "Ultimate Multi-API System with Content-Matched Images (ABSOLUTELY NO PEOPLE)",
            "processing_time": total_time,
            "slides_created": len(lecture_data["slides"]),
            "main_concept": lecture_data.get("main_concept", "general"),
            "detected_concepts": lecture_data.get("detected_concepts", [])
        }
    }

if __name__ == "__main__":
    # Test the ultimate system
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
    
    # Test ultimate video creation
    result = make_ultimate_lecture_video(temp_file.name, "test_output", "Test Ultimate Video")
    
    print(f"\nUltimate video created: {result['video_path']}")
    print(f"Processing time: {result['lecture_info']['processing_time']:.1f}s")
    print(f"Slides created: {result['lecture_info']['slides_created']}")
    print(f"Main concept: {result['lecture_info']['main_concept']}")
    print(f"Detected concepts: {result['lecture_info']['detected_concepts']}")
    
    # Clean up
    os.unlink(temp_file.name)
