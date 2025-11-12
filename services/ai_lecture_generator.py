# services/ai_lecture_generator.py
"""
AI Lecture Generator - Tương tự NotebookLM
Tạo video bài giảng từ tài liệu PDF/Word/PowerPoint
"""

import os
import uuid
import json
import re
import tempfile
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
try:
    import google.generativeai as genai
    # Check if GenerativeModel exists
    if not hasattr(genai, 'GenerativeModel'):
        # Fallback for old version
        genai = None
except ImportError:
    genai = None

@dataclass
class LectureSlide:
    """Một slide trong bài giảng"""
    title: str
    content: str
    key_points: List[str]
    duration_sec: float
    slide_number: int

@dataclass
class LectureStructure:
    """Cấu trúc bài giảng"""
    title: str
    introduction: str
    slides: List[LectureSlide]
    conclusion: str
    total_duration: float
    learning_objectives: List[str]

class AILectureGenerator:
    """AI tạo bài giảng từ tài liệu - Tương tự NotebookLM"""
    
    def __init__(self):
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        self.model = None
        self._configure()
    
    def _configure(self):
        """Cấu hình Gemini API"""
        if genai is None:
            return
        
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            return
        
        try:
            genai.configure(api_key=key)
            self.model = genai.GenerativeModel(self.model_name)
        except Exception:
            self.model = None
    
    def analyze_document_content(self, document_text: str) -> Dict[str, any]:
        """
        Phân tích nội dung tài liệu để hiểu cấu trúc và nội dung chính
        Tương tự NotebookLM - AI đọc và hiểu tài liệu
        """
        
        analysis_prompt = f"""
Bạn là chuyên gia tạo nội dung bài giảng chuyên sâu và toàn diện. Hãy phân tích tài liệu dưới đây và tạo nội dung video bài giảng CHUYÊN SÂU và TOÀN DIỆN:

TÀI LIỆU:
<<<BEGIN>>>
{document_text.strip()}
<<<END>>>

YÊU CẦU TẠO NỘI DUNG CHUYÊN SÂU:
1. PHÂN TÍCH SÂU: Không chỉ giới thiệu mà phân tích chi tiết các khái niệm, nguyên lý, và ứng dụng
2. NỘI DUNG TOÀN DIỆN: Bao gồm lý thuyết, thực hành, ví dụ cụ thể, case study thực tế
3. CẤU TRÚC LOGIC: Từ cơ bản đến nâng cao, từ khái niệm đến ứng dụng
4. KIẾN THỨC CHUYÊN MÔN: Trích xuất và trình bày kiến thức chuyên sâu từ tài liệu
5. VÍ DỤ THỰC TẾ: Thêm nhiều ví dụ cụ thể, case study, ứng dụng trong thực tế
6. PHÂN TÍCH CHI TIẾT: Giải thích tại sao, như thế nào, khi nào sử dụng
7. KẾT NỐI KIẾN THỨC: Liên kết các khái niệm với nhau một cách logic
8. ĐỘ SÂU NỘI DUNG: Mỗi phần phải có đủ chi tiết để học viên hiểu sâu
9. THỰC HÀNH: Hướng dẫn cách áp dụng kiến thức vào thực tế
10. TỔNG KẾT CHUYÊN SÂU: Tóm tắt và đưa ra insights quan trọng

Trả về kết quả dưới dạng JSON:
{{
  "main_topic": "string",
  "engaging_hooks": ["string"],
  "learning_objectives": ["string"],
  "content_structure": [
    {{
      "section_title": "string",
      "key_concepts": ["string"],
      "examples": ["string"],
      "difficulty_level": "beginner|intermediate|advanced",
      "estimated_duration_minutes": number,
      "visual_suggestions": ["string"],
      "storytelling_elements": ["string"],
      "detailed_analysis": "string",
      "practical_applications": ["string"],
      "case_studies": ["string"]
    }}
  ],
  "core_concepts": ["string"],
  "practical_examples": ["string"],
  "difficulty_assessment": "string",
  "total_estimated_duration": number,
  "interesting_facts": ["string"],
  "visual_suggestions": ["string"],
  "storytelling_elements": ["string"],
  "deep_insights": ["string"],
  "real_world_applications": ["string"]
}}
"""
        
        try:
            response = self.model.generate_content(analysis_prompt)
            result = json.loads(response.text)
            return result
        except Exception as e:
            # Fallback analysis nếu AI không hoạt động
            return self._fallback_analysis(document_text)
    
    def _fallback_analysis(self, document_text: str) -> Dict[str, any]:
        """Phân tích fallback khi AI không hoạt động"""
        lines = document_text.split('\n')
        main_topic = lines[0][:100] if lines else "Chủ đề chính"
        
        return {
            "main_topic": main_topic,
            "learning_objectives": ["Hiểu được nội dung cơ bản", "Áp dụng kiến thức thực tế"],
            "content_structure": [
                {
                    "section_title": "Giới thiệu",
                    "key_concepts": ["Khái niệm cơ bản"],
                    "examples": ["Ví dụ thực tế"],
                    "difficulty_level": "beginner",
                    "estimated_duration_minutes": 5
                }
            ],
            "core_concepts": ["Khái niệm chính"],
            "practical_examples": ["Ví dụ ứng dụng"],
            "difficulty_assessment": "Trung bình",
            "total_estimated_duration": 10
        }
    
    def generate_lecture_structure(self, analysis: Dict[str, any]) -> LectureStructure:
        """
        Tạo cấu trúc bài giảng từ phân tích tài liệu
        Tương tự NotebookLM - AI tạo outline bài giảng
        """
        
        if genai is None or self.model is None:
            return self._fallback_lecture_structure(analysis)
        
        structure_prompt = f"""
Bạn là chuyên gia thiết kế bài giảng chuyên sâu. Dựa trên phân tích tài liệu dưới đây, hãy tạo cấu trúc bài giảng CHUYÊN SÂU và TOÀN DIỆN:

PHÂN TÍCH TÀI LIỆU:
{json.dumps(analysis, ensure_ascii=False, indent=2)}

YÊU CẦU TẠO BÀI GIẢNG CHUYÊN SÂU:
1. Tạo tiêu đề bài giảng hấp dẫn và chuyên nghiệp
2. Viết phần giới thiệu chi tiết, không chỉ là lời chào
3. Chia nội dung thành các slide logic và chuyên sâu (6-12 slides)
4. Mỗi slide phải có:
   - Tiêu đề rõ ràng và cụ thể
   - Nội dung chính chi tiết (3-5 câu, không chỉ là giới thiệu)
   - Điểm quan trọng sâu sắc (3-5 điểm)
   - Ví dụ cụ thể và case study
   - Thời lượng phù hợp (45-90 giây/slide)
5. Viết phần kết luận tóm tắt và đưa ra insights quan trọng
6. Xác định mục tiêu học tập cụ thể và có thể đo lường được
7. Đảm bảo nội dung từ cơ bản đến nâng cao
8. Bao gồm cả lý thuyết và thực hành
9. Thêm các ví dụ thực tế và ứng dụng cụ thể
10. Tạo câu chuyển tiếp mạch lạc giữa các slide

Trả về kết quả dưới dạng JSON:
{{
  "title": "string",
  "introduction": "string",
  "slides": [
    {{
      "title": "string",
      "content": "string",
      "key_points": ["string"],
      "duration_sec": number,
      "slide_number": number,
      "examples": ["string"],
      "case_studies": ["string"],
      "practical_applications": ["string"]
    }}
  ],
  "conclusion": "string",
  "learning_objectives": ["string"],
  "total_duration": number,
  "deep_insights": ["string"],
  "real_world_applications": ["string"]
}}
"""
        
        try:
            response = self.model.generate_content(structure_prompt)
            result = json.loads(response.text)
            
            # Tạo LectureStructure object
            slides = []
            for slide_data in result.get("slides", []):
                slide = LectureSlide(
                    title=slide_data.get("title", ""),
                    content=slide_data.get("content", ""),
                    key_points=slide_data.get("key_points", []),
                    duration_sec=slide_data.get("duration_sec", 30),
                    slide_number=slide_data.get("slide_number", 1)
                )
                slides.append(slide)
            
            return LectureStructure(
                title=result.get("title", "Bài giảng"),
                introduction=result.get("introduction", ""),
                slides=slides,
                conclusion=result.get("conclusion", ""),
                total_duration=result.get("total_duration", 300),
                learning_objectives=result.get("learning_objectives", [])
            )
            
        except Exception as e:
            # Fallback structure
            return self._create_fallback_structure(analysis)
    
    def _create_fallback_structure(self, analysis: Dict[str, any]) -> LectureStructure:
        """Tạo cấu trúc fallback"""
        main_topic = analysis.get("main_topic", "Chủ đề chính")
        
        slides = [
            LectureSlide(
                title="Giới thiệu",
                content=f"Chào mừng đến với bài giảng về {main_topic}",
                key_points=["Mục tiêu học tập", "Nội dung chính"],
                duration_sec=30,
                slide_number=1
            ),
            LectureSlide(
                title="Nội dung chính",
                content="Nội dung chi tiết của bài giảng",
                key_points=["Điểm quan trọng 1", "Điểm quan trọng 2"],
                duration_sec=60,
                slide_number=2
            )
        ]
        
        return LectureStructure(
            title=f"Bài giảng: {main_topic}",
            introduction="Chào mừng đến với bài giảng",
            slides=slides,
            conclusion="Cảm ơn bạn đã theo dõi",
            total_duration=120,
            learning_objectives=["Hiểu được nội dung cơ bản"]
        )
    
    def enhance_lecture_content(self, structure: LectureStructure) -> LectureStructure:
        """
        Cải thiện nội dung bài giảng với AI
        Tương tự NotebookLM - AI tối ưu hóa nội dung
        """
        
        enhancement_prompt = f"""
Bạn là chuyên gia cải thiện nội dung bài giảng. Hãy cải thiện bài giảng dưới đây để làm cho nó hấp dẫn và hiệu quả hơn:

BÀI GIẢNG HIỆN TẠI:
{{
  "title": "{structure.title}",
  "introduction": "{structure.introduction}",
  "slides": {json.dumps([{
      "title": slide.title,
      "content": slide.content,
      "key_points": slide.key_points
  } for slide in structure.slides], ensure_ascii=False, indent=2)},
  "conclusion": "{structure.conclusion}",
  "learning_objectives": {structure.learning_objectives}
}}

YÊU CẦU CẢI THIỆN:
1. Làm cho nội dung hấp dẫn và dễ hiểu hơn
2. Thêm ví dụ thực tế và case study
3. Cải thiện cách trình bày
4. Đảm bảo logic và mạch lạc
5. Thêm tương tác và câu hỏi

Trả về kết quả dưới dạng JSON với cùng cấu trúc.
"""
        
        try:
            response = self.model.generate_content(enhancement_prompt)
            result = json.loads(response.text)
            
            # Cập nhật structure với nội dung cải thiện
            enhanced_slides = []
            for i, slide_data in enumerate(result.get("slides", [])):
                slide = LectureSlide(
                    title=slide_data.get("title", structure.slides[i].title if i < len(structure.slides) else ""),
                    content=slide_data.get("content", structure.slides[i].content if i < len(structure.slides) else ""),
                    key_points=slide_data.get("key_points", structure.slides[i].key_points if i < len(structure.slides) else []),
                    duration_sec=slide_data.get("duration_sec", structure.slides[i].duration_sec if i < len(structure.slides) else 30),
                    slide_number=slide_data.get("slide_number", i + 1)
                )
                enhanced_slides.append(slide)
            
            return LectureStructure(
                title=result.get("title", structure.title),
                introduction=result.get("introduction", structure.introduction),
                slides=enhanced_slides,
                conclusion=result.get("conclusion", structure.conclusion),
                total_duration=result.get("total_duration", structure.total_duration),
                learning_objectives=result.get("learning_objectives", structure.learning_objectives)
            )
            
        except Exception as e:
            # Trả về structure gốc nếu không cải thiện được
            return structure

    def generate_lecture_script(self, structure: LectureStructure) -> str:
        """
        Tạo script chi tiết cho bài giảng
        Tương tự NotebookLM - AI tạo script tự nhiên
        """

        # Fixed: Do not include invalid Python code inside an f-string
        style = os.getenv('LECTURE_STYLE', '').lower()
        script_prompt = ""
        if style == 'ielts_vocab':
            script_prompt += """
--- PHONG CÁCH 'IELTS VOCAB' ---
• Mỗi slide nêu 1–2 từ vựng then chốt.
• Định dạng: TỪ VỰNG (in HOA) /IPA/ – nghĩa ngắn gọn; 1–2 đồng nghĩa.
• Ví dụ: 1 câu tự nhiên, sát ngữ cảnh học thuật/đời sống.
• Mẹo ghi nhớ: 1 câu liên tưởng ngắn (hình ảnh/âm thanh/câu chuyện).
• Ngôn ngữ giảng: câu ngắn, rõ, nhịp 130–150 từ/phút, tránh liệt kê khô cứng.
"""

        script_prompt += f"""
Bạn là giáo viên chuyên nghiệp với kinh nghiệm sâu sắc. Hãy tạo script chi tiết và chuyên sâu cho bài giảng dưới đây:

BÀI GIẢNG:
{{
  "title": "{structure.title}",
  "introduction": "{structure.introduction}",
  "slides": {json.dumps([{
      "title": slide.title,
      "content": slide.content,
      "key_points": slide.key_points,
      "duration_sec": slide.duration_sec
  } for slide in structure.slides], ensure_ascii=False, indent=2)},
  "conclusion": "{structure.conclusion}",
  "learning_objectives": {structure.learning_objectives}
}}

YÊU CẦU SCRIPT CHUYÊN SÂU:
1. Viết script tự nhiên như giáo viên chuyên nghiệp thực sự giảng
2. Mỗi slide phải có nội dung chi tiết, không chỉ là giới thiệu
3. Thêm giải thích sâu sắc về khái niệm, nguyên lý, và ứng dụng
4. Bao gồm nhiều ví dụ cụ thể, case study thực tế
5. Thêm câu hỏi tương tác và gợi mở tư duy
6. Giải thích tại sao, như thế nào, khi nào sử dụng
7. Liên kết các khái niệm với nhau một cách logic
8. Thêm insights và kinh nghiệm thực tế
9. Đảm bảo thời lượng phù hợp với mỗi slide (45-90 giây)
10. Sử dụng ngôn ngữ chuyên nghiệp nhưng dễ hiểu
11. Thêm các câu chuyển tiếp mạch lạc giữa các slide
12. Bao gồm cả lý thuyết và thực hành
13. Đưa ra các ứng dụng thực tế cụ thể
14. Tạo động lực học tập và khuyến khích tư duy phản biện

Trả về script hoàn chỉnh dưới dạng văn bản thuần túy với nội dung chuyên sâu và toàn diện.
"""
        try:
            response = self.model.generate_content(script_prompt)
            return response.text
        except Exception as e:
            # Fallback script
            return self._create_fallback_script(structure)
    
    def _create_fallback_script(self, structure: LectureStructure) -> str:
        """Tạo script fallback"""
        script_parts = [f"Chào mừng đến với bài giảng: {structure.title}"]
        script_parts.append(structure.introduction)
        
        for slide in structure.slides:
            script_parts.append(f"Bây giờ chúng ta sẽ tìm hiểu về {slide.title}")
            script_parts.append(slide.content)
            if slide.key_points:
                script_parts.append("Những điểm quan trọng cần nhớ:")
                for point in slide.key_points:
                    script_parts.append(f"- {point}")
        
        script_parts.append(structure.conclusion)
        return "\n\n".join(script_parts)
    
    def create_lecture_from_document(self, document_text: str) -> Tuple[LectureStructure, str]:
        """
        Tạo bài giảng hoàn chỉnh từ tài liệu
        Tương tự NotebookLM - Quy trình chính
        """
        
        if genai is None or self.model is None:
            # Fallback khi Gemini không khả dụng
            return self._create_fallback_lecture(document_text)
        
        try:
            # Bước 1: Phân tích tài liệu
            analysis = self.analyze_document_content(document_text)
            
            # Bước 2: Tạo cấu trúc bài giảng
            structure = self.generate_lecture_structure(analysis)
            
            # Bước 3: Cải thiện nội dung
            enhanced_structure = self.enhance_lecture_content(structure)
            
            # Bước 4: Tạo script chi tiết
            script = self.generate_lecture_script(enhanced_structure)
            
            return enhanced_structure, script
            
        except Exception as e:
            # Fallback khi có lỗi
            return self._create_fallback_lecture(document_text)
    
    def _create_fallback_lecture(self, document_text: str) -> Tuple[LectureStructure, str]:
        """
        Tạo bài giảng đơn giản khi Gemini không khả dụng
        """
        # Trích xuất tiêu đề từ tài liệu
        lines = document_text.split('\n')
        title = "Bài giảng AI"
        for line in lines[:10]:  # Tìm trong 10 dòng đầu
            if len(line.strip()) > 10 and len(line.strip()) < 100:
                title = line.strip()
                break
        
        # Tạo slides đơn giản
        slides = []
        content_parts = document_text.split('\n\n')
        for i, part in enumerate(content_parts[:5]):  # Tối đa 5 slides
            if len(part.strip()) > 20:
                slide = LectureSlide(
                    title=f"Phần {i+1}",
                    content=part.strip()[:500],  # Giới hạn độ dài
                    key_points=[f"Điểm quan trọng {j+1}" for j in range(3)],
                    duration_sec=30.0,
                    slide_number=i+1
                )
                slides.append(slide)
        
        # Tạo cấu trúc bài giảng
        lecture = LectureStructure(
            title=title,
            introduction="Chào mừng bạn đến với bài giảng này. Chúng ta sẽ cùng tìm hiểu về chủ đề quan trọng.",
            learning_objectives=[
                "Hiểu được nội dung cơ bản",
                "Nắm vững các khái niệm chính",
                "Áp dụng kiến thức vào thực tế"
            ],
            slides=slides,
            conclusion="Cảm ơn bạn đã theo dõi bài giảng. Hãy tiếp tục học tập và phát triển!",
            total_duration=10
        )
        
        # Tạo script đơn giản
        script = f"""
        Chào mừng bạn đến với bài giảng: {title}
        
        Trong bài giảng này, chúng ta sẽ tìm hiểu về:
        - Các khái niệm cơ bản
        - Ví dụ thực tế
        - Ứng dụng trong cuộc sống
        
        Hãy bắt đầu với phần đầu tiên...
        """
        
        return lecture, script
    
    def _fallback_analysis(self, document_text: str) -> Dict[str, any]:
        """
        Phân tích đơn giản khi Gemini không khả dụng
        """
        lines = document_text.split('\n')
        title = "Bài giảng AI"
        for line in lines[:5]:
            if len(line.strip()) > 10:
                title = line.strip()
                break
        
        return {
            "main_topic": title,
            "learning_objectives": [
                "Hiểu được nội dung cơ bản",
                "Nắm vững các khái niệm chính",
                "Áp dụng kiến thức vào thực tế"
            ],
            "content_structure": [
                {
                    "section_title": "Phần 1: Giới thiệu",
                    "key_concepts": ["Khái niệm cơ bản"],
                    "examples": ["Ví dụ thực tế"],
                    "difficulty_level": "beginner",
                    "estimated_duration_minutes": 5
                }
            ],
            "core_concepts": ["Khái niệm chính"],
            "practical_examples": ["Ví dụ thực tế"],
            "difficulty_assessment": "Cơ bản",
            "total_estimated_duration": 10
        }
    
    def _fallback_lecture_structure(self, analysis: Dict[str, any]) -> LectureStructure:
        """
        Tạo cấu trúc bài giảng đơn giản khi Gemini không khả dụng
        """
        title = analysis.get("main_topic", "Bài giảng AI")
        
        slides = []
        for i, section in enumerate(analysis.get("content_structure", [])[:5]):
            slide = LectureSlide(
                title=section.get("section_title", f"Phần {i+1}"),
                content=section.get("key_concepts", ["Nội dung chính"])[0] if section.get("key_concepts") else "Nội dung chính",
                key_points=section.get("key_concepts", ["Điểm quan trọng"]),
                duration_sec=30.0,
                slide_number=i+1
            )
            slides.append(slide)
        
        return LectureStructure(
            title=title,
            introduction="Chào mừng bạn đến với bài giảng này.",
            learning_objectives=analysis.get("learning_objectives", ["Hiểu được nội dung cơ bản"]),
            slides=slides,
            conclusion="Cảm ơn bạn đã theo dõi bài giảng.",
            total_duration=analysis.get("total_estimated_duration", 10)
        )

# Service instance
ai_lecture_generator = AILectureGenerator()
