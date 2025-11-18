#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Content Processor - Xử lý nội dung file thành video hoàn chỉnh
Luồng công việc: File → AI Gemini tóm tắt → Tạo hình ảnh chân thật → Giọng người thật → Video
"""

import os
import json
import tempfile
import uuid
from typing import Dict, List, Optional, Tuple
from services.doc_video_service import extract_text_from_file, clean_text
from services.human_voice_service import is_human_voice_available, synthesize_human_voice
from services.image_search_service import search_image
from ai_gemini import extract_main_content_from_document
import moviepy.editor as mp
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import moviepy.video.fx.all as vfx
import moviepy.audio.fx.all as afx

class AIContentProcessor:
    """AI xử lý nội dung file thành video hoàn chỉnh"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ai_content_")
        self.require_human_voice = os.getenv('REQUIRE_HUMAN_VOICE', '1') == '1'
        
        # Kiểm tra giọng người thật bắt buộc
        if self.require_human_voice and not is_human_voice_available():
            raise RuntimeError('ElevenLabs chưa được cấu hình nhưng REQUIRE_HUMAN_VOICE=1; từ chối chuyển sang TTS máy.')
    
    def process_file_to_video(self, file_path: str, output_dir: str, 
                            title: str = None, width: int = 1280, height: int = 720) -> Dict:
        """
        Xử lý file thành video hoàn chỉnh
        
        Args:
            file_path: Đường dẫn file nội dung
            output_dir: Thư mục output
            title: Tiêu đề video (optional)
            width: Chiều rộng video
            height: Chiều cao video
        
        Returns:
            Dict chứa thông tin video đã tạo
        """
        print("🤖 AI Content Processor - Bắt đầu xử lý...")
        print("=" * 60)
        
        # Bước 1: Trích xuất nội dung từ file
        print("📄 Bước 1: Trích xuất nội dung từ file...")
        raw_content = extract_text_from_file(file_path)
        raw_content = clean_text(raw_content)
        
        if not raw_content:
            raise ValueError("Không trích xuất được nội dung từ file.")
        
        print(f"✅ Đã trích xuất {len(raw_content)} ký tự")
        
        # Bước 2: AI Gemini tóm tắt nội dung chính và tạo dàn ý 10-15 ý
        print("\n🧠 Bước 2: AI Gemini tóm tắt nội dung chính và tạo dàn ý (mục tiêu: 10-15 slides, 2-3 phút)...")
        content_summary = self._summarize_content_with_ai(raw_content)
        
        if not content_summary:
            raise ValueError("AI Gemini không thể tóm tắt nội dung.")
        
        slides_count = len(content_summary.get('slides', []))
        outline = content_summary.get('outline', [])
        
        # Kiểm tra số lượng slides
        if slides_count < 10:
            print(f"⚠️ CẢNH BÁO: Chỉ có {slides_count} slides, cần ít nhất 10 slides để đạt 2-3 phút")
            print(f"   Video có thể ngắn hơn mong đợi. Hãy kiểm tra lại tài liệu hoặc prompt.")
        else:
            print(f"✅ Đã tóm tắt thành {slides_count} mục (mục tiêu: 10-15)")
        
        if outline:
            print(f"✅ Dàn ý: {', '.join(outline[:8])}")
        
        # Tính toán thời lượng dự kiến
        estimated_duration = (slides_count + 2) * 15  # +2 cho intro và conclusion
        print(f"📊 Thời lượng dự kiến: ~{estimated_duration/60:.1f} phút ({estimated_duration} giây)")
        
        # Bước 3: Tạo hình ảnh chân thật cho từng slide
        print("\n🖼️ Bước 3: Tạo hình ảnh chân thật...")
        slides_with_images = self._create_realistic_images(content_summary)
        
        # Bước 4: Tạo giọng người thật
        print("\n🎤 Bước 4: Tạo giọng người thật...")
        slides_with_audio = self._create_human_voice_audio(slides_with_images)
        
        # Bước 5: Tạo video hoàn chỉnh
        print("\n🎬 Bước 5: Tạo video hoàn chỉnh...")
        video_result = self._create_final_video(slides_with_audio, output_dir, title, width, height)
        
        print("\n" + "=" * 60)
        print("✅ HOÀN THÀNH XỬ LÝ!")
        print("=" * 60)
        print(f"📹 Video: {video_result['video_path']}")
        print(f"📝 Captions: {video_result['caption_path']}")
        duration_sec = video_result['duration']
        duration_min = duration_sec / 60
        print(f"⏱️ Thời lượng: {duration_sec:.1f} giây ({duration_min:.1f} phút)")
        print(f"🎯 Slides: {video_result['slide_count']}")
        
        # Kiểm tra thời lượng có đạt mục tiêu không
        if duration_sec < 120:
            print(f"⚠️ CẢNH BÁO: Video chỉ dài {duration_sec:.1f} giây, chưa đạt mục tiêu 2-3 phút (120-180 giây)")
            print(f"   Gợi ý: Tài liệu có thể quá ngắn, hoặc cần tăng số lượng slides")
        elif duration_sec >= 120 and duration_sec <= 180:
            print(f"✅ Thời lượng đạt mục tiêu: {duration_min:.1f} phút (2-3 phút)")
        else:
            print(f"ℹ️ Video dài hơn mục tiêu: {duration_min:.1f} phút (mục tiêu: 2-3 phút)")
        
        return video_result
    
    def _summarize_content_with_ai(self, content: str) -> Dict:
        """AI Gemini tóm tắt nội dung thành cấu trúc video"""
        
        print("🤖 AI Gemini đang phân tích và tóm tắt nội dung...")
        
        # Sử dụng AI Gemini để tóm tắt
        lecture_data = extract_main_content_from_document(content)
        
        if not lecture_data:
            raise ValueError("AI Gemini không thể phân tích nội dung.")
        
        print(f"✅ Chủ đề chính: {lecture_data.get('main_topic', 'N/A')}")
        print(f"✅ Khái niệm cốt lõi: {', '.join(lecture_data.get('core_concepts', [])[:3])}")
        print(f"✅ Số slides: {len(lecture_data.get('slides', []))}")
        
        return lecture_data
    
    def _create_realistic_images(self, content_summary: Dict) -> List[Dict]:
        """Tạo hình ảnh chân thật cho từng slide"""
        
        slides_with_images = []
        
        # Slide giới thiệu
        intro_data = content_summary.get("introduction", {})
        intro_keywords = intro_data.get("image_keywords", [])
        
        print(f"🖼️ Tạo hình ảnh cho slide giới thiệu...")
        intro_image = self._find_realistic_image(intro_keywords, "introduction")
        
        slides_with_images.append({
            "type": "introduction",
            "script": intro_data.get("script", ""),  # Script ngắn từ AI
            "content": intro_data.get("script", ""),  # Fallback
            "subtitle": intro_data.get("subtitle", ""),  # Phụ đề ngắn
            "key_points": intro_data.get("key_points", []),
            "image_path": intro_image,
            "image_keywords": intro_keywords,
                "duration_sec": intro_data.get("duration_sec", 14.0)  # Thời lượng 12-18 giây
        })
        
        # Các slides chính
        slides_data = content_summary.get("slides", [])
        for i, slide_data in enumerate(slides_data, 1):
            print(f"🖼️ Tạo hình ảnh cho mục {i}/{len(slides_data)}: {slide_data.get('title', 'N/A')}")
            
            img_keywords = slide_data.get("image_keywords", [])
            # Ưu tiên: Hình ảnh trong file (nếu có), sau đó mới tạo AI
            slide_image = self._find_realistic_image(img_keywords, f"slide_{i}")
            
            slides_with_images.append({
                "type": "main_slide",
                "title": slide_data.get("title", ""),
                "script": slide_data.get("script", ""),  # Script ngắn từ AI
                "content": slide_data.get("script", slide_data.get("main_content", "")),  # Fallback
                "subtitle": slide_data.get("subtitle", ""),  # Phụ đề ngắn
                "key_points": slide_data.get("key_points", []),
                "image_path": slide_image,
                "image_keywords": img_keywords,
                "duration_sec": slide_data.get("duration_sec", 15.0)  # Thời lượng 12-18 giây
            })
        
        # Slide kết luận
        conclusion_data = content_summary.get("conclusion", {})
        conclusion_keywords = conclusion_data.get("image_keywords", [])
        
        print(f"🖼️ Tạo hình ảnh cho slide kết luận...")
        conclusion_image = self._find_realistic_image(conclusion_keywords, "conclusion")
        
        slides_with_images.append({
            "type": "conclusion",
            "script": conclusion_data.get("script", ""),  # Script ngắn từ AI
            "content": conclusion_data.get("script", ""),  # Fallback
            "subtitle": conclusion_data.get("subtitle", ""),  # Phụ đề ngắn
            "key_points": conclusion_data.get("key_takeaways", []),
            "image_path": conclusion_image,
            "image_keywords": conclusion_keywords,
                "duration_sec": conclusion_data.get("duration_sec", 14.0)  # Thời lượng 12-18 giây
        })
        
        return slides_with_images
    
    def _find_realistic_image(self, keywords: List[str], slide_type: str) -> Optional[str]:
        """Tìm hình ảnh chân thật phù hợp"""
        
        if not keywords:
            return None
        
        # Tạo từ khóa tìm kiếm chân thật
        realistic_keywords = self._create_realistic_keywords(keywords, slide_type)
        
        for keyword in realistic_keywords:
            print(f"🔍 Tìm kiếm hình ảnh: {keyword}")
            image_path = search_image(keyword)
            if image_path:
                print(f"✅ Tìm thấy hình ảnh: {os.path.basename(image_path)}")
                return image_path
        
        print(f"⚠️ Không tìm thấy hình ảnh phù hợp cho {slide_type}")
        return None
    
    def _create_realistic_keywords(self, original_keywords: List[str], slide_type: str) -> List[str]:
        """Tạo từ khóa tìm kiếm hình ảnh CHẤT LƯỢNG CAO, ĐA DẠNG và TRÙNG KHỚP nội dung"""
        
        realistic_keywords = []
        
        # Tạo nhiều biến thể ĐA DẠNG cho mỗi keyword để có nhiều loại ảnh khác nhau
        for keyword in original_keywords:
            # Biến thể 1: Realistic photos
            realistic_keywords.extend([
                f"{keyword} sharp clear high quality photo",
                f"{keyword} realistic professional photo",
                f"{keyword} detailed high resolution image"
            ])
            # Biến thể 2: Illustrations và diagrams
            realistic_keywords.extend([
                f"{keyword} illustration diagram clear",
                f"{keyword} infographic professional visual"
            ])
            # Biến thể 3: Real-world contexts
            realistic_keywords.extend([
                f"{keyword} real world context natural",
                f"{keyword} practical application realistic"
            ])
        
        # Thêm từ khóa chất lượng cao theo loại slide
        if slide_type == "introduction":
            realistic_keywords.extend([
                "professional presentation background sharp clear",
                "business meeting room high quality",
                "educational environment modern clean",
                "modern office setting professional"
            ])
        elif slide_type == "conclusion":
            realistic_keywords.extend([
                "success achievement celebration sharp clear",
                "completion milestone professional",
                "professional finish high quality"
            ])
        else:
            realistic_keywords.extend([
                "professional workspace modern clear",
                "business environment high quality",
                "educational setting clean sharp"
            ])
        
        return realistic_keywords[:8]  # Tăng số lượng từ khóa để có nhiều lựa chọn hơn
    
    def _create_human_voice_audio(self, slides_with_images: List[Dict]) -> List[Dict]:
        """Tạo giọng đọc TTS tự nhiên cho từng slide (script chi tiết 30-50 từ, phong cách NotebookLM)"""
        
        slides_with_audio = []
        
        for i, slide in enumerate(slides_with_images):
            print(f"🎤 Tạo giọng đọc TTS cho mục {i+1}...")
            
            # Ưu tiên sử dụng script ngắn từ AI (15-25 từ)
            script = slide.get("script") or slide.get("content", "")
            if not script:
                continue
            
            # Đảm bảo script phù hợp với 12-18 giây (khoảng 35-55 từ)
            words = script.split()
            if len(words) > 65:
                # Cắt script nếu quá dài (tối đa 65 từ cho 18 giây)
                script = " ".join(words[:65])
                print(f"⚠️ Script quá dài, đã cắt xuống còn {len(script.split())} từ")
            elif len(words) < 25:
                # Nếu script quá ngắn, cảnh báo để đảm bảo video đủ dài
                print(f"⚠️ Script hơi ngắn ({len(words)} từ), cần ít nhất 35 từ để đạt 12 giây")
            
            # Tạo audio với giọng TTS tự nhiên
            audio_path = os.path.join(self.temp_dir, f"audio_{i:03d}.mp3")
            
            try:
                result = synthesize_human_voice(script, output_path=audio_path)
                if result.get("success"):
                    slide["audio_path"] = audio_path
                    # Lưu script để dùng cho caption
                    slide["script"] = script
                    # Thời lượng từ AI response hoặc từ audio
                    audio_duration = result.get("duration", 0)
                    if audio_duration:
                        slide["duration"] = audio_duration
                    print(f"✅ Giọng TTS: {len(script.split())} từ, ~{audio_duration:.1f}s")
                else:
                    print(f"❌ Lỗi tạo giọng TTS: {result.get('error', 'Unknown')}")
                    # Vẫn tiếp tục với slide này nhưng không có audio
                    slide["duration"] = slide.get("duration_sec", 15.0)
                    continue
                    
            except Exception as e:
                print(f"❌ Lỗi tạo giọng TTS: {e}")
                # Vẫn tiếp tục với slide này nhưng không có audio
                slide["duration"] = slide.get("duration_sec", 15.0)
                continue
            
            slides_with_audio.append(slide)
        
        return slides_with_audio
    
    def _create_final_video(self, slides_with_audio: List[Dict], output_dir: str, 
                          title: str, width: int, height: int) -> Dict:
        """Tạo video hoàn chỉnh"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        clips = []
        timeline = []
        current_time = 0.0
        
        for i, slide in enumerate(slides_with_audio):
            print(f"🎬 Tạo clip cho slide {i+1}...")
            
            # Tạo hình ảnh slide
            slide_image = self._create_slide_image(
                slide, width, height, slide.get("image_path")
            )
            
            if not slide_image:
                continue
            
            # Lấy thời lượng từ AI response (12-18 giây) hoặc từ audio, mặc định 15 giây
            duration_sec = slide.get("duration_sec") or slide.get("duration")
            if duration_sec:
                # Đảm bảo thời lượng trong khoảng 12-18 giây để đạt tổng 2-3 phút
                duration_sec = max(12.0, min(18.0, float(duration_sec)))
            else:
                duration_sec = 15.0  # Mặc định 15 giây
            
            # Tạo video clip với thời lượng cố định
            clip = ImageClip(slide_image).set_duration(duration_sec)
            
            # Thêm audio (nếu có)
            audio_path = slide.get("audio_path")
            if audio_path and os.path.exists(audio_path):
                audio_clip = AudioFileClip(audio_path)
                # Nếu audio ngắn hơn duration_sec, giữ nguyên duration_sec
                # Nếu audio dài hơn, cắt audio hoặc điều chỉnh
                if audio_clip.duration > duration_sec:
                    audio_clip = audio_clip.subclip(0, duration_sec)
                elif audio_clip.duration < duration_sec:
                    # Nếu audio ngắn, giữ nguyên duration của clip (sẽ có khoảng lặng)
                    pass
                clip = clip.set_audio(audio_clip)
            
            # Thêm hiệu ứng mượt mà (ngắn hơn vì clip ngắn)
            fade_duration = min(0.3, duration_sec * 0.1)  # 10% thời lượng hoặc tối đa 0.3s
            clip = clip.fx(vfx.fadein, fade_duration).fx(vfx.fadeout, fade_duration)
            if clip.audio:
                clip = clip.fx(afx.audio_fadein, fade_duration).fx(afx.audio_fadeout, fade_duration)
            
            clips.append(clip)
            
            # Lấy subtitle từ slide (nếu có), nếu không thì dùng script
            subtitle = slide.get("subtitle") or slide.get("content", "")
            script_text = slide.get("script") or slide.get("content", "")
            timeline.append((current_time, current_time + clip.duration, subtitle, script_text))
            current_time += clip.duration
        
        # Ghép video
        if not clips:
            raise ValueError("Không tạo được video từ slides.")
        
        final_video = concatenate_videoclips(clips, method="compose")
        
        # Lưu video
        video_title = title or "AI_Generated_Video"
        video_name = f"{uuid.uuid4()}_{video_title.replace(' ', '_')}.mp4"
        caption_name = video_name.replace(".mp4", ".vtt")
        
        video_path = os.path.join(output_dir, video_name)
        caption_path = os.path.join(output_dir, caption_name)
        
        final_video.write_videofile(
            video_path, fps=24, codec="libx264", audio_codec="aac",
            temp_audiofile=os.path.join(self.temp_dir, "temp_audio.m4a"),
            remove_temp=True
        )
        
        # Tạo captions
        self._create_captions(timeline, caption_path)
        
        return {
            "video_path": video_path,
            "caption_path": caption_path,
            "duration": current_time,
            "slide_count": len(slides_with_audio),
            "title": video_title
        }
    
    def _create_slide_image(self, slide: Dict, width: int, height: int, 
                          background_image: str = None) -> Optional[str]:
        """Tạo hình ảnh slide"""
        
        try:
            from services.doc_video_service import render_slide_image
            
            # Tạo nội dung hiển thị
            content = slide.get("content", "")
            key_points = slide.get("key_points", [])
            
            if key_points:
                content += "\n\nĐiểm quan trọng:\n" + "\n".join(f"• {point}" for point in key_points)
            
            # Render slide
            slide_image = render_slide_image(
                content, w=width, h=height, 
                content_type="educational", 
                image_path=background_image
            )
            
            # Lưu slide
            slide_path = os.path.join(self.temp_dir, f"slide_{len(os.listdir(self.temp_dir)):03d}.png")
            slide_image.save(slide_path)
            
            return slide_path
            
        except Exception as e:
            print(f"❌ Lỗi tạo slide image: {e}")
            return None
    
    def _create_captions(self, timeline: List[Tuple], caption_path: str):
        """Tạo file captions VTT với phụ đề ngắn gọn"""
        
        def format_time(seconds):
            ms = int((seconds - int(seconds)) * 1000)
            s = int(seconds)
            h = s // 3600
            m = (s % 3600) // 60
            s = s % 60
            return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
        
        lines = ["WEBVTT", ""]
        for entry in timeline:
            # Hỗ trợ cả format cũ (3 phần tử) và format mới (4 phần tử)
            if len(entry) >= 4:
                start, end, subtitle, script = entry
                # Sử dụng subtitle (phụ đề ngắn) cho VTT
                text = subtitle.strip()
            else:
                start, end, text = entry[:3]
                text = text.strip()
            
            if text:
                lines.append(f"{format_time(start)} --> {format_time(end)}")
                lines.append(text)
                lines.append("")
        
        with open(caption_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

# Function tiện ích
def process_file_to_video(file_path: str, output_dir: str, title: str = None) -> Dict:
    """
    Function tiện ích để xử lý file thành video
    
    Args:
        file_path: Đường dẫn file nội dung
        output_dir: Thư mục output
        title: Tiêu đề video (optional)
    
    Returns:
        Dict chứa thông tin video đã tạo
    """
    processor = AIContentProcessor()
    return processor.process_file_to_video(file_path, output_dir, title)

# Demo function
def demo_ai_content_processor():
    """Demo AI Content Processor"""
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           🤖 AI CONTENT PROCESSOR - DEMO                       ║
║                                                                ║
║  Luồng công việc hoàn chỉnh:                                  ║
║  ✅ File → AI Gemini tóm tắt → Hình ảnh chân thật            ║
║  ✅ Giọng người thật → Video hoàn chỉnh                       ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Kiểm tra API keys
    if not os.getenv('GEMINI_API_KEY'):
        print("❌ Error: GEMINI_API_KEY not found")
        return
    
    if not is_human_voice_available():
        print("❌ Error: ELEVENLABS_API_KEY not found")
        print("💡 This system requires human voice (ElevenLabs)")
        return
    
    print("✅ All API keys configured")
    
    # Tìm file demo
    demo_files = []
    uploads_dir = "static/uploads"
    
    if os.path.exists(uploads_dir):
        for file in os.listdir(uploads_dir):
            if file.endswith(('.pdf', '.docx', '.pptx')):
                demo_files.append(os.path.join(uploads_dir, file))
    
    if not demo_files:
        print("📂 No demo files found in static/uploads/")
        print("💡 Please add a PDF/DOCX/PPTX file to static/uploads/ and try again.")
        return
    
    # Chọn file demo
    print(f"\n📂 Found {len(demo_files)} demo files:")
    for i, file in enumerate(demo_files[:3], 1):
        size_mb = os.path.getsize(file) / (1024 * 1024)
        print(f"  {i}. {os.path.basename(file)} ({size_mb:.1f} MB)")
    
    demo_file = demo_files[0]
    print(f"\n🎯 Using: {os.path.basename(demo_file)}")
    
    try:
        # Xử lý file
        result = process_file_to_video(
            file_path=demo_file,
            output_dir="static/uploads",
            title="AI Generated Video"
        )
        
        print("\n" + "=" * 60)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📹 Video: {result['video_path']}")
        print(f"📝 Captions: {result['caption_path']}")
        print(f"⏱️ Duration: {result['duration']:.1f} seconds")
        print(f"🎯 Slides: {result['slide_count']}")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Load .env
    try:
        from dotenv import load_dotenv
        if os.path.exists('.env'):
            load_dotenv()
    except ImportError:
        pass
    
    demo_ai_content_processor()
