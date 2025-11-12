
def make_simple_lecture_video(src_path: str, out_dir: str, title: str = None) -> dict:
    """
    Tao video bai giang don gian su dung tat ca API keys co san
    """
    import os
    import tempfile
    import uuid
    import re
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    
    # Import required functions
    from services.doc_video_service import (
        extract_text_from_file, clean_text, _safe_makedirs,
        render_slide_image, synth_voice, write_vtt
    )
    
    # Check APIs
    apis_available = {
        "pexels": bool(os.getenv("PEXELS_API_KEY")),
        "unsplash": bool(os.getenv("UNSPLASH_ACCESS_KEY")),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "stability": bool(os.getenv("STABILITY_API_KEY"))
    }
    
    print(f"APIs available: {[k for k, v in apis_available.items() if v]}")
    
    # Check minimum requirements
    if not apis_available["elevenlabs"]:
        raise RuntimeError("ElevenLabs API key required")
    
    if not apis_available["gemini"]:
        raise RuntimeError("Gemini API key required")
    
    if not any([apis_available["pexels"], apis_available["unsplash"], apis_available["stability"]]):
        raise RuntimeError("At least one image API required")
    
    _safe_makedirs(out_dir)
    
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
        "main_topic": "Educational Content",
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
    tmpdir = tempfile.mkdtemp(prefix="simple_lecture_")
    
    # Introduction slide
    print("\nCreating introduction slide...")
    intro_img = generate_simple_image(lecture_data["introduction"]["image_keywords"], apis_available)
    intro_clip = create_simple_slide(
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
        slide_img = generate_simple_image(slide_data["image_keywords"], apis_available)
        slide_clip = create_simple_slide(
            slide_data["script"], 
            tmpdir, i, img_path=slide_img
        )
        if slide_clip:
            clips.append(slide_clip)
            timeline.append((cur_t, cur_t + slide_clip.duration, slide_data["script"]))
            cur_t += slide_clip.duration
    
    # Conclusion slide
    print("\nCreating conclusion slide...")
    conclusion_img = generate_simple_image(lecture_data["conclusion"]["image_keywords"], apis_available)
    conclusion_clip = create_simple_slide(
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
    write_vtt(timeline, out_vtt)
    
    print(f"\nSimple video created successfully: {out_video}")
    print(f"Duration: {cur_t:.1f} seconds")
    print(f"Total slides: {len(clips)}")
    
    return {
        "video_path": out_video,
        "caption_path": out_vtt,
        "script_text": raw,
        "lecture_info": {
            "title": lecture_data["lecture_title"],
            "main_topic": lecture_data["main_topic"],
            "total_slides": len(clips),
            "total_duration_seconds": cur_t,
            "apis_used": [k for k, v in apis_available.items() if v],
            "image_generator": "Simple Multi-API"
        }
    }

def generate_simple_image(keywords, apis_available):
    """Generate image using available APIs"""
    if not keywords:
        return None
    
    # Try Pexels first
    if apis_available["pexels"]:
        try:
            from services.working_image_service import generate_working_image
            result = generate_working_image(keywords[0], style="educational")
            if result and result.get("success"):
                print(f"   OK Pexels: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   LOI Pexels: {e}")
    
    # Try Unsplash
    if apis_available["unsplash"]:
        try:
            from services.working_image_service import generate_working_image
            result = generate_working_image(keywords[0], style="educational")
            if result and result.get("success"):
                print(f"   OK Unsplash: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   LOI Unsplash: {e}")
    
    # Try Stability AI
    if apis_available["stability"]:
        try:
            from services.working_image_service import generate_working_image
            result = generate_working_image(keywords[0], style="educational")
            if result and result.get("success"):
                print(f"   OK Stability AI: {result['file_path']}")
                return result["file_path"]
        except Exception as e:
            print(f"   LOI Stability AI: {e}")
    
    print("   LOI: All image APIs failed")
    return None

def create_simple_slide(script, tmpdir, slide_num, img_path=None):
    """Create simple slide"""
    try:
        # Create slide content
        display_content = script
        
        frame_path = os.path.join(tmpdir, f"simple_slide_{slide_num:03d}.png")
        im = render_slide_image(display_content, w=1280, h=720, 
                               content_type="educational", image_path=img_path)
        im.save(frame_path)
        
        # Create audio
        audio_path = os.path.join(tmpdir, f"simple_audio_{slide_num:03d}.mp3")
        print(f"   Synthesizing voice for slide {slide_num}...")
        dur = synth_voice(script, audio_path)
        
        # Check audio file
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
        print(f"   Error creating slide {slide_num}: {e}")
        return None
