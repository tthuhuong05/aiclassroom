import os, json, random
from typing import Optional, Dict, List

try:
    import google.generativeai as genai  # SDK đúng cần dùng
    _GENAI_IMPORT_ERROR = None
except Exception as e:
    genai = None
    _GENAI_IMPORT_ERROR = e
    
GEMINI_MODEL_QA   = os.environ.get("GEMINI_MODEL_QA", "gemini-1.5-flash")
GEMINI_MODEL_GRADE= os.environ.get("GEMINI_MODEL_GRADE", "gemini-1.5-flash")

def _gemini_configured() -> bool:
    return bool(genai and os.getenv("GEMINI_API_KEY"))

def _gemini_ensure() -> bool:
    if not _gemini_configured():
        return False
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        return True
    except Exception as e:
        print(f"⚠️ Gemini configure failed: {e}")
        return False
    
def _configured():
    key = os.environ.get("GEMINI_API_KEY", "")
    return bool(key and genai)

def _ensure():
    if not _configured():
        return False
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return True

def mcq_from_snippet(snippet: str, seed: Optional[int] = None) -> Optional[Dict]:
    """
    Sinh một câu MCQ đa dạng dựa trên NỘI DUNG THỰC TẾ của video bài giảng.
    Tập trung vào khái niệm cốt lõi, nguyên lý, và ứng dụng thực tế.
    Trả: {question, options:list[str], correct_index:int, explanation}
    """
    if not _ensure():
        return None
    
    # Các chiến lược tạo câu hỏi dựa trên nội dung thực tế
    content_strategies = [
        "- Tập trung vào KHÁI NIỆM CỐT LÕI và nguyên lý cơ bản được giảng dạy.",
        "- Hỏi về ỨNG DỤNG THỰC TẾ và tình huống sử dụng trong thực tế.",
        "- Kiểm tra hiểu biết về MỐI QUAN HỆ giữa các khái niệm được đề cập.",
        "- Đánh giá khả năng PHÂN TÍCH và áp dụng kiến thức vào tình huống mới.",
        "- Tập trung vào ĐIỂM QUAN TRỌNG và lưu ý chính được nhấn mạnh trong bài giảng."
    ]
    
    sys = (
        "Bạn là chuyên gia tạo câu hỏi trắc nghiệm cho video bài giảng. "
        "Dựa trên NỘI DUNG THỰC TẾ của bài giảng, tạo câu hỏi tập trung vào: "
        "- Khái niệm cốt lõi và nguyên lý cơ bản "
        "- Ứng dụng thực tế và tình huống sử dụng "
        "- Mối quan hệ giữa các khái niệm "
        "- Điểm quan trọng được nhấn mạnh trong bài giảng"
    )
    
    prompt = f"""
NỘI DUNG BÀI GIẢNG (dựa trên video thực tế): <<<BEGIN>>>
{snippet.strip()}
<<<END>>>

YÊU CẦU TẠO CÂU HỎI:
- Tạo 1 câu hỏi trắc nghiệm 4 lựa chọn dựa trên NỘI DUNG THỰC TẾ của bài giảng
- Tập trung vào KHÁI NIỆM CỐT LÕI, NGUYÊN LÝ, và ỨNG DỤNG THỰC TẾ
- 1 đáp án đúng duy nhất, 3 nhiễu hợp lý và có tính thách thức
- Câu hỏi phải kiểm tra HIỂU BIẾT SÂU về nội dung bài giảng
- Không chỉ hỏi về từ khóa mà hỏi về Ý NGHĨA và ỨNG DỤNG
{random.choice(content_strategies)}

JSON schema:
{{
 "question": "string",
 "options": ["A","B","C","D"],
 "correct_index": 0,
 "explanation": "string"
}}
"""
    # Tăng tính ngẫu nhiên với temperature và top_p, và có thể seed shuffle lại lựa chọn
    temperature = 0.7 + random.uniform(-0.2, 0.3)
    top_p = 0.85 + random.uniform(-0.1, 0.1)
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(
            sys + "\n" + prompt,
            generation_config={"temperature": temperature, "top_p": top_p, "max_output_tokens": 512}
        )
        text = resp.text or ""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        data = json.loads(text[start:end+1])
        if not isinstance(data.get("options"), list) or len(data["options"]) != 4:
            return None
        if not isinstance(data.get("correct_index"), int):
            return None
        # Nếu truyền seed, shuffle phương án để đa dạng hơn nữa
        options = data["options"]
        idx = data["correct_index"]
        if seed is not None:
            random.seed(seed)
            zipped = list(zip(options, range(4)))
            random.shuffle(zipped)
            options_shuffled, indices = zip(*zipped)
            idx_new = indices.index(idx)
            data["options"] = list(options_shuffled)
            data["correct_index"] = idx_new
        return data
    except Exception:
        return None

def keywords_from_snippet(snippet: str, k: int = 5) -> Optional[List[str]]:
    """
    Trích xuất keywords/cụm ý từ NỘI DUNG THỰC TẾ của video bài giảng.
    Tập trung vào khái niệm cốt lõi, nguyên lý, và điểm quan trọng.
    """
    if not _ensure():
        return None
    
    # Các hướng dẫn tập trung vào nội dung thực tế
    content_focus = random.choice([
        "Tập trung vào các KHÁI NIỆM CỐT LÕI và nguyên lý cơ bản được giảng dạy.",
        "Ưu tiên các ĐIỂM QUAN TRỌNG và lưu ý chính được nhấn mạnh trong bài giảng.",
        "Chọn các từ khóa thể hiện ỨNG DỤNG THỰC TẾ và tình huống sử dụng.",
        "Tập trung vào MỐI QUAN HỆ giữa các khái niệm và nguyên lý được đề cập.",
        "Chọn các cụm từ thể hiện HIỂU BIẾT SÂU về nội dung bài giảng."
    ])
    
    prompt = f"""
NỘI DUNG BÀI GIẢNG (dựa trên video thực tế): <<<BEGIN>>>
{snippet.strip()}
<<<END>>>

YÊU CẦU TRÍCH XUẤT TỪ KHÓA:
- Trích xuất {k} từ khóa/cụm ý từ NỘI DUNG THỰC TẾ của bài giảng
- Tập trung vào KHÁI NIỆM CỐT LÕI, NGUYÊN LÝ, và ĐIỂM QUAN TRỌNG
- Các từ khóa phải thể hiện HIỂU BIẾT SÂU về nội dung bài giảng
- Không chỉ là từ khóa đơn lẻ mà là các CỤM Ý có ý nghĩa
- Ưu tiên các từ khóa thể hiện ỨNG DỤNG THỰC TẾ và tình huống sử dụng

{content_focus}

Xuất JSON array: ["từ_khóa_1", "từ_khóa_2", ...]
"""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(prompt, generation_config={"temperature":0.35, "max_output_tokens": 128})
        text = resp.text or "[]"
        start = text.find("[")
        end = text.rfind("]")
        if start == -1 or end == -1:
            return None
        arr = json.loads(text[start:end+1])
        arr = [str(x).strip() for x in arr if str(x).strip()]
        random.shuffle(arr)
        return arr[:max(3, min(6, k))] or None
    except Exception:
        return None

def grade_free_text(answer: str, keywords: List[str]) -> Dict:
    """
    Chấm tự luận/vấn đáp bằng Gemini.
    Trả: {"correct":bool, "score":0-1, "feedback":str}
    Nếu lỗi hoặc thiếu từ khóa thì đối chiếu thủ công.
    """
    def _fallback():
        a = (answer or "").lower()
        keywords_set = set(keywords or [])
        hits = sum(1 for k in keywords_set if k.lower() in a)
        need = max(2, len(keywords_set)//2)
        ok = hits >= need
        score = hits / max(1, len(keywords_set))
        return {
            "correct": ok,
            "score": round(score, 2),
            "feedback": f"Đạt {hits} từ khóa/{len(keywords_set)}."
        }

    if not _ensure() or not keywords:
        return _fallback()

    rubric = ", ".join(keywords)
    prompt = f"""
Đáp án của học viên:
<<<ANS>>>
{answer.strip()}
<<<END>>

Rubric (từ khóa/các ý cần có): {rubric}

Chấm theo tiêu chí:
- Độ đúng nội dung so với RUBRIC (không cần đúng chính tả tuyệt đối).
- Cho "score" trong [0,1].
- "correct": true nếu score >= 0.6.
- Trả JSON: {{"correct": true/false, "score": 0.xx, "feedback": "ngắn gọn"}}.
"""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_GRADE)
        resp = model.generate_content(prompt, generation_config={"temperature":0.0, "max_output_tokens": 256})
        text = resp.text or ""
        s = text.find("{")
        e = text.rfind("}")
        if s == -1 or e == -1:
            return _fallback()
        data = json.loads(text[s:e+1])
        if "correct" not in data:
            return _fallback()
        return {
            "correct": bool(data.get("correct")),
            "score": float(data.get("score", 0.0)),
            "feedback": str(data.get("feedback",""))
        }
    except Exception:
        return _fallback()

def generate_comprehensive_video_questions(video_content: str, question_types: List[str] = None, n_questions_per_type: int = 2) -> Optional[Dict]:
    """
    Tạo câu hỏi tổng hợp dựa trên NỘI DUNG VIDEO BÀI HỌC.
    Tạo nhiều loại câu hỏi (MCQ, Essay, Oral) không lặp lại nội dung.
    
    Args:
        video_content: Nội dung thực tế của video bài giảng
        question_types: Danh sách loại câu hỏi ["mcq", "essay", "oral"]
        n_questions_per_type: Số câu hỏi mỗi loại
    
    Returns:
        Dict chứa câu hỏi đa dạng không lặp lại
    """
    if not _ensure():
        return None
    
    if question_types is None:
        question_types = ["mcq", "essay", "oral"]
    
    # Các chiến lược tạo câu hỏi đa dạng dựa trên nội dung video
    comprehensive_strategies = [
        "Tập trung vào KHÁI NIỆM CỐT LÕI và nguyên lý cơ bản được giảng dạy trong video.",
        "Hỏi về ỨNG DỤNG THỰC TẾ và tình huống sử dụng được đề cập trong bài giảng.",
        "Kiểm tra hiểu biết về MỐI QUAN HỆ giữa các khái niệm được trình bày trong video.",
        "Đánh giá khả năng PHÂN TÍCH và áp dụng kiến thức vào tình huống mới dựa trên nội dung video.",
        "Tập trung vào ĐIỂM QUAN TRỌNG và lưu ý chính được nhấn mạnh trong video bài giảng.",
        "Kiểm tra khả năng SO SÁNH và đối chiếu các khái niệm trong video.",
        "Đánh giá hiểu biết về QUY TRÌNH và các bước thực hiện được trình bày trong video.",
        "Tập trung vào VÍ DỤ CỤ THỂ và case study được đề cập trong bài giảng."
    ]
    
    sys = (
        "Bạn là chuyên gia tạo câu hỏi tổng hợp cho video bài giảng. "
        "Dựa trên NỘI DUNG THỰC TẾ của video bài giảng, tạo câu hỏi đa dạng tập trung vào: "
        "- Khái niệm cốt lõi và nguyên lý cơ bản được giảng dạy "
        "- Ứng dụng thực tế và tình huống sử dụng trong video "
        "- Mối quan hệ giữa các khái niệm được trình bày "
        "- Điểm quan trọng được nhấn mạnh trong video bài giảng "
        "- Đảm bảo KHÔNG LẶP LẠI nội dung câu hỏi giữa các loại"
    )
    
    prompt = f"""
NỘI DUNG VIDEO BÀI GIẢNG (thực tế): <<<BEGIN>>>
{video_content.strip()}
<<<END>>>

YÊU CẦU TẠO CÂU HỎI TỔNG HỢP:
- Tạo câu hỏi đa dạng dựa trên NỘI DUNG THỰC TẾ của video bài giảng
- Tập trung vào KHÁI NIỆM CỐT LÕI, NGUYÊN LÝ, và ỨNG DỤNG THỰC TẾ
- Đảm bảo KHÔNG LẶP LẠI nội dung câu hỏi giữa các loại (MCQ, Essay, Oral)
- Mỗi loại câu hỏi tập trung vào khía cạnh khác nhau của nội dung video
- Câu hỏi phải kiểm tra HIỂU BIẾT SÂU về nội dung video bài giảng

LOẠI CÂU HỎI CẦN TẠO:
- MCQ: {n_questions_per_type} câu hỏi trắc nghiệm 4 lựa chọn
- Essay: {n_questions_per_type} câu hỏi tự luận
- Oral: {n_questions_per_type} câu hỏi vấn đáp

{random.choice(comprehensive_strategies)}

JSON schema:
{{
 "mcq_questions": [
   {{
     "question": "string",
     "options": ["A","B","C","D"],
     "correct_index": 0,
     "explanation": "string"
   }}
 ],
 "essay_questions": [
   {{
     "question": "string",
     "keywords": ["từ_khóa_1", "từ_khóa_2", ...],
     "explanation": "string"
   }}
 ],
 "oral_questions": [
   {{
     "question": "string",
     "keywords": ["từ_khóa_1", "từ_khóa_2", ...],
     "explanation": "string"
   }}
 ]
}}
"""
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(
            sys + "\n" + prompt,
            generation_config={"temperature": 0.8, "top_p": 0.9, "max_output_tokens": 2048}
        )
        text = resp.text or ""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        
        data = json.loads(text[start:end+1])
        return data
        
    except Exception:
        return None

def extract_main_content_from_document(document_text: str) -> Optional[Dict]:
    """
    Phân tích và trích xuất NỘI DUNG CHÍNH từ tài liệu với độ chính xác cao.
    Tập trung vào: khái niệm cốt lõi, nguyên lý quan trọng, ứng dụng thực tế.
    
    Args:
        document_text: Nội dung đầy đủ của tài liệu
    
    Returns:
        Dict chứa nội dung chính, cấu trúc bài giảng, và gợi ý hình ảnh
    """
    if not _ensure():
        return None
    
    sys = (
        "You are a professional document analysis and video lecture creation expert with deep experience. "
        "Task: Analyze documents and extract MAIN and MOST IMPORTANT content with high accuracy. "
        "Focus on: "
        "- Extract ONLY the main and most important concepts (tổng quát và tập trung vào nội dung chính) "
        "- Prioritize core knowledge and essential principles, skip minor details "
        "- Create simplified structure focusing on key concepts and important points "
        "- Focus on practical understanding and key takeaways "
        "- Suggest diverse, specific and matching images for each section "
        "- Ensure content is general but covers essential points "
        "- Avoid overwhelming details, focus on what matters most "
        "- Keep each slide clear, focused, and easy to understand"
    )
    
    prompt = f"""
SOURCE DOCUMENT: <<<BEGIN>>>
{document_text.strip()}
<<<END>>>

REQUIREMENTS FOR MAIN CONTENT EXTRACTION (Focus on Core and Important Points):

1. FOCUSED EXTRACTION (Tổng quát và tập trung nội dung chính):
   - Identify the SINGLE MAIN TOPIC of the document clearly
   - Extract 3-5 CORE CONCEPTS most important (only essentials, skip minor details)
   - Focus on main principles and key takeaways
   - Keep content GENERAL but cover important points
   - Prioritize understanding over details

2. SIMPLIFIED LECTURE STRUCTURE (Nội dung chính):
   - Divide into 5-8 focused slides, each slide covers ONE main idea clearly
   - Each slide: Clear title + Main content (2-3 clear sentences) + 2-3 key points
   - Natural and engaging reading script for each slide (40-60 seconds/slide)
   - Coherent transitions between slides focusing on main flow
   - From basic understanding to practical application

3. DIVERSE AND MATCHING IMAGE SUGGESTIONS (Hình ảnh đa dạng trùng khớp):
   - Each slide suggests 3-4 diverse, specific and accurate image keywords
   - Images must MATCH slide content accurately, not just decorative
   - Keywords should be VARIED and DIVERSE to get different image types
   - Prioritize: realistic photos, illustrations, diagrams, charts that match content
   - Keywords must be specific enough to find high-quality matching images on Unsplash/Pexels
   - Ensure images are SHARP and CLEAR in search results (prioritize "high quality", "sharp", "clear")

4. NATURAL HUMAN-LIKE READING VOICE (Giọng người thật):
   - Script written like a natural human teacher speaking
   - Conversational tone, NOT robotic or mechanical
   - Use natural pauses and expressions
   - Keep language simple but professional
   - Avoid formal/academic tone that sounds like AI
   - Make it sound like a real person explaining concepts

JSON schema:
{{
  "main_topic": "Single main topic (accurate)",
  "core_concepts": ["Concept 1", "Concept 2", "Concept 3"],
  "lecture_title": "Engaging lecture title",
  "introduction": {{
    "script": "Natural introduction script (30-40 seconds)",
    "key_points": ["Point 1", "Point 2"],
    "image_keywords": ["keyword 1", "keyword 2"]
  }},
  "slides": [
    {{
      "slide_number": 1,
      "title": "Clear slide title",
      "main_content": "Core content (2-3 accurate sentences)",
      "key_points": ["Important point 1", "Important point 2"],
      "script": "Natural reading script (40-60 seconds)",
      "image_keywords": ["specific keyword 1", "specific keyword 2"],
      "duration_sec": 50
    }}
  ],
  "conclusion": {{
    "script": "Summary conclusion script (30-40 seconds)",
    "key_takeaways": ["Key point 1", "Key point 2"],
    "image_keywords": ["keyword"]
  }},
  "total_duration_minutes": 8
}}
"""
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(
            sys + "\n" + prompt,
            generation_config={
                "temperature": 0.1, 
                "top_p": 0.8, 
                "max_output_tokens": 4096,
                "response_mime_type": "application/json"
            }
        )
        text = resp.text or ""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        
        data = json.loads(text[start:end+1])
        return data
        
    except Exception as e:
        print(f"Error extracting main content: {e}")
        return None

def generate_questions_from_transcript(transcript: str, question_type: str = "mcq", n_questions: int = 1) -> Optional[Dict]:
    """
    Tạo câu hỏi dựa trên TRANSCRIPT video bài giảng.
    AI Gemini phân tích ý nghĩa, khái niệm, và ứng dụng thực tế từ transcript.
    TUYỆT ĐỐI KHÔNG lấy y nguyên text từ transcript.
    
    Args:
        transcript: Nội dung transcript của video bài giảng
        question_type: Loại câu hỏi ("mcq", "essay", "oral")
        n_questions: Số lượng câu hỏi cần tạo
    
    Returns:
        Dict chứa câu hỏi và đáp án
    """
    if not _ensure():
        return None
    
    # Các chiến lược tạo câu hỏi dựa trên ý nghĩa transcript
    transcript_strategies = [
        "Tập trung vào KHÁI NIỆM và NGUYÊN LÝ được đề cập trong transcript.",
        "Hỏi về ỨNG DỤNG THỰC TẾ và tình huống sử dụng được mô tả trong video.",
        "Kiểm tra hiểu biết về MỐI QUAN HỆ giữa các khái niệm được trình bày.",
        "Đánh giá khả năng PHÂN TÍCH và áp dụng kiến thức vào tình huống mới.",
        "Tập trung vào ĐIỂM QUAN TRỌNG và lưu ý chính được nhấn mạnh trong video.",
        "Kiểm tra khả năng SO SÁNH và đối chiếu các khái niệm được đề cập.",
        "Đánh giá hiểu biết về QUY TRÌNH và các bước thực hiện được trình bày.",
        "Tập trung vào VÍ DỤ CỤ THỂ và case study được đề cập trong transcript."
    ]
    
    if question_type == "mcq":
        sys = (
            "Bạn là chuyên gia tạo câu hỏi trắc nghiệm cho video bài giảng. "
            "Dựa trên TRANSCRIPT của video bài giảng, tạo câu hỏi tập trung vào: "
            "- Khái niệm và nguyên lý được đề cập trong video "
            "- Ứng dụng thực tế và tình huống sử dụng "
            "- Mối quan hệ giữa các khái niệm được trình bày "
            "- Điểm quan trọng được nhấn mạnh trong video bài giảng "
            "- TUYỆT ĐỐI KHÔNG lấy y nguyên text từ transcript"
        )
        
        prompt = f"""
TRANSCRIPT VIDEO BÀI GIẢNG: <<<BEGIN>>>
{transcript.strip()}
<<<END>>>

YÊU CẦU TẠO CÂU HỎI TRẮC NGHIỆM:
- Tạo {n_questions} câu hỏi trắc nghiệm 4 lựa chọn dựa trên TRANSCRIPT video bài giảng
- Tập trung vào KHÁI NIỆM, NGUYÊN LÝ, và ỨNG DỤNG THỰC TẾ được trình bày trong video
- Mỗi câu có 1 đáp án đúng duy nhất, 3 nhiễu hợp lý và có tính thách thức
- Câu hỏi phải kiểm tra HIỂU BIẾT SÂU về nội dung video bài giảng
- Không chỉ hỏi về từ khóa mà hỏi về Ý NGHĨA và ỨNG DỤNG thực tế
- Ưu tiên các câu hỏi về TÌNH HUỐNG SỬ DỤNG và ỨNG DỤNG THỰC TẾ
- TUYỆT ĐỐI KHÔNG lấy y nguyên text từ transcript
- Câu hỏi phải dựa trên Ý NGHĨA và KHÁI NIỆM được trình bày

{random.choice(transcript_strategies)}

JSON schema:
{{
 "questions": [
   {{
     "question": "string",
     "options": ["A","B","C","D"],
     "correct_index": 0,
     "explanation": "string"
   }}
 ]
}}
"""
    
    elif question_type in ["essay", "oral"]:
        sys = (
            "Bạn là chuyên gia tạo câu hỏi tự luận/vấn đáp cho video bài giảng. "
            "Dựa trên TRANSCRIPT của video bài giảng, tạo câu hỏi tập trung vào: "
            "- Khái niệm và nguyên lý được đề cập trong video "
            "- Ứng dụng thực tế và tình huống sử dụng "
            "- Phân tích và đánh giá nội dung bài giảng "
            "- TUYỆT ĐỐI KHÔNG lấy y nguyên text từ transcript"
        )
        
        prompt = f"""
TRANSCRIPT VIDEO BÀI GIẢNG: <<<BEGIN>>>
{transcript.strip()}
<<<END>>>

YÊU CẦU TẠO CÂU HỎI TỰ LUẬN/VẤN ĐÁP:
- Tạo {n_questions} câu hỏi tự luận/vấn đáp dựa trên TRANSCRIPT video bài giảng
- Tập trung vào KHÁI NIỆM, NGUYÊN LÝ, và ỨNG DỤNG THỰC TẾ
- Câu hỏi phải yêu cầu PHÂN TÍCH, ĐÁNH GIÁ, và ÁP DỤNG kiến thức từ video
- Không chỉ hỏi về từ khóa mà hỏi về HIỂU BIẾT SÂU và ỨNG DỤNG THỰC TẾ
- Ưu tiên các câu hỏi về TÌNH HUỐNG SỬ DỤNG và ỨNG DỤNG THỰC TẾ
- TUYỆT ĐỐI KHÔNG lấy y nguyên text từ transcript
- Câu hỏi phải dựa trên Ý NGHĨA và KHÁI NIỆM được trình bày

{random.choice(transcript_strategies)}

JSON schema:
{{
 "questions": [
   {{
     "question": "string",
     "keywords": ["từ_khóa_1", "từ_khóa_2", ...],
     "explanation": "string"
   }}
 ]
}}
"""
    
    else:
        return None
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(
            sys + "\n" + prompt,
            generation_config={"temperature": 0.7, "top_p": 0.9, "max_output_tokens": 1024}
        )
        text = resp.text or ""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        
        data = json.loads(text[start:end+1])
        return data
        
    except Exception:
        return None
    
    
def chat_about_transcript(
    transcript: str,
    question: str,
    history: Optional[List[Dict]] = None
) -> Optional[Dict]:
    """
    Trợ giảng AI cho video bài học.

    - 'related' = True  nếu câu hỏi thuộc phạm vi nội dung bài học
      (chủ đề, khái niệm, ví dụ, kiến thức nền trực tiếp liên quan).
    - Khi related=True, AI được phép trả lời chi tiết, có thể dùng kiến thức ngoài transcript,
      nhưng KHÔNG được mâu thuẫn với transcript.
    - Khi related=False, backend sẽ chặn và không trả lời.

    Returns:
        {"related": bool, "answer": str}
    """
    question = (question or "").strip()
    transcript = (transcript or "").strip()
    if not question:
        return {"related": False, "answer": ""}

    if not _ensure():
        # Không có GEMINI_API_KEY hoặc lỗi import SDK
        return {"related": False, "answer": ""}

    history = history or []
    conv_lines = []
    for turn in history:
        role = (turn.get("role") or "").strip()
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            conv_lines.append(f"Người học: {content}")
        elif role == "assistant":
            conv_lines.append(f"Trợ giảng AI: {content}")
        else:
            conv_lines.append(content)
    history_text = "\n".join(conv_lines) if conv_lines else "Không có hội thoại trước đó."

    sys = (
        "Bạn là TRỢ GIẢNG AI trong một khóa học lập trình.\n"
        "Bạn nhận được TRANSCRIPT (có thể không đầy đủ) của video bài học "
        "và LỊCH SỬ HỘI THOẠI với học viên.\n"
        "Nhiệm vụ của bạn:\n"
        "1) Quyết định xem câu hỏi cuối cùng của học viên có thuộc phạm vi bài học hay không "
        "(chủ đề, khái niệm, ví dụ, kiến thức nền trực tiếp liên quan).\n"
        "2) Nếu CÓ thuộc phạm vi bài học (related=true): hãy trả lời chi tiết bằng tiếng Việt, "
        "có thể dùng kiến thức lập trình chung bên ngoài transcript, nhưng TUYỆT ĐỐI không "
        "mâu thuẫn với nội dung transcript.\n"
        "3) Nếu KHÔNG thuộc phạm vi bài học (related=false): không trả lời nội dung, chỉ đánh dấu là không liên quan.\n"
    )

    prompt = f"""
TRANSCRIPT VIDEO (có thể chưa đầy đủ):
<<<TRANSCRIPT>>>
{transcript}
<<<END_TRANSCRIPT>>>

LỊCH SỬ HỘI THOẠI:
<<<HISTORY>>>
{history_text}
<<<END_HISTORY>>>

CÂU HỎI MỚI NHẤT CỦA HỌC VIÊN:
<<<QUESTION>>>
{question}
<<<END_QUESTION>>>

HÃY TRẢ VỀ DUY NHẤT JSON:

{{
  "related": true hoặc false,
  "answer": "câu trả lời chi tiết bằng tiếng Việt nếu related=true, ngược lại để chuỗi rỗng"
}}
"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(
            sys + "\n" + prompt,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.8,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json",
            },
        )
        text = resp.text or ""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {"related": False, "answer": ""}

        data = json.loads(text[start : end + 1])
        related = bool(data.get("related"))
        answer = str(data.get("answer") or "").strip()
        if not related:
            return {"related": False, "answer": ""}
        return {"related": True, "answer": answer}
    except Exception as e:
        print(f"⚠️ chat_about_transcript error: {e}")
        # Lỗi thì chặn cho an toàn
        return {"related": False, "answer": ""}


def generate_questions_from_video_content(video_content: str, question_type: str = "mcq", n_questions: int = 1) -> Optional[Dict]:
    """
    Tạo câu hỏi dựa trên NỘI DUNG THỰC TẾ của video bài giảng.
    Tập trung vào khái niệm cốt lõi, nguyên lý, và ứng dụng thực tế.
    
    Args:
        video_content: Nội dung thực tế của video bài giảng
        question_type: Loại câu hỏi ("mcq", "essay", "oral")
        n_questions: Số lượng câu hỏi cần tạo
    
    Returns:
        Dict chứa câu hỏi và đáp án
    """
    if not _ensure():
        return None
    
    # Các chiến lược tạo câu hỏi dựa trên nội dung video
    video_strategies = [
        "Tập trung vào KHÁI NIỆM CỐT LÕI và nguyên lý cơ bản được giảng dạy trong video.",
        "Hỏi về ỨNG DỤNG THỰC TẾ và tình huống sử dụng được đề cập trong bài giảng.",
        "Kiểm tra hiểu biết về MỐI QUAN HỆ giữa các khái niệm được trình bày trong video.",
        "Đánh giá khả năng PHÂN TÍCH và áp dụng kiến thức vào tình huống mới dựa trên nội dung video.",
        "Tập trung vào ĐIỂM QUAN TRỌNG và lưu ý chính được nhấn mạnh trong video bài giảng."
    ]
    
    if question_type == "mcq":
        sys = (
            "Bạn là chuyên gia tạo câu hỏi trắc nghiệm cho video bài giảng. "
            "Dựa trên NỘI DUNG THỰC TẾ của video bài giảng, tạo câu hỏi tập trung vào: "
            "- Khái niệm cốt lõi và nguyên lý cơ bản được giảng dạy "
            "- Ứng dụng thực tế và tình huống sử dụng trong video "
            "- Mối quan hệ giữa các khái niệm được trình bày "
            "- Điểm quan trọng được nhấn mạnh trong video bài giảng"
        )
        
        prompt = f"""
NỘI DUNG VIDEO BÀI GIẢNG (thực tế): <<<BEGIN>>>
{video_content.strip()}
<<<END>>>

YÊU CẦU TẠO CÂU HỎI TRẮC NGHIỆM:
- Tạo {n_questions} câu hỏi trắc nghiệm 4 lựa chọn dựa trên NỘI DUNG THỰC TẾ của video bài giảng
- Tập trung vào KHÁI NIỆM CỐT LÕI, NGUYÊN LÝ, và ỨNG DỤNG THỰC TẾ được trình bày trong video
- Mỗi câu có 1 đáp án đúng duy nhất, 3 nhiễu hợp lý và có tính thách thức
- Câu hỏi phải kiểm tra HIỂU BIẾT SÂU về nội dung video bài giảng
- Không chỉ hỏi về từ khóa mà hỏi về Ý NGHĨA và ỨNG DỤNG thực tế
- Ưu tiên các câu hỏi về TÌNH HUỐNG SỬ DỤNG và ỨNG DỤNG THỰC TẾ

{random.choice(video_strategies)}

JSON schema:
{{
 "questions": [
   {{
     "question": "string",
     "options": ["A","B","C","D"],
     "correct_index": 0,
     "explanation": "string"
   }}
 ]
}}
"""
    
    elif question_type in ["essay", "oral"]:
        sys = (
            "Bạn là chuyên gia tạo câu hỏi tự luận/vấn đáp cho video bài giảng. "
            "Dựa trên NỘI DUNG THỰC TẾ của video bài giảng, tạo câu hỏi tập trung vào: "
            "- Khái niệm cốt lõi và nguyên lý cơ bản "
            "- Ứng dụng thực tế và tình huống sử dụng "
            "- Phân tích và đánh giá nội dung bài giảng"
        )
        
        prompt = f"""
NỘI DUNG VIDEO BÀI GIẢNG (thực tế): <<<BEGIN>>>
{video_content.strip()}
<<<END>>>

YÊU CẦU TẠO CÂU HỎI TỰ LUẬN/VẤN ĐÁP:
- Tạo {n_questions} câu hỏi tự luận/vấn đáp dựa trên NỘI DUNG THỰC TẾ của video bài giảng
- Tập trung vào KHÁI NIỆM CỐT LÕI, NGUYÊN LÝ, và ỨNG DỤNG THỰC TẾ
- Câu hỏi phải yêu cầu PHÂN TÍCH, ĐÁNH GIÁ, và ÁP DỤNG kiến thức từ video
- Không chỉ hỏi về từ khóa mà hỏi về HIỂU BIẾT SÂU và ỨNG DỤNG THỰC TẾ
- Ưu tiên các câu hỏi về TÌNH HUỐNG SỬ DỤNG và ỨNG DỤNG THỰC TẾ

{random.choice(video_strategies)}

JSON schema:
{{
 "questions": [
   {{
     "question": "string",
     "keywords": ["từ_khóa_1", "từ_khóa_2", ...],
     "explanation": "string"
   }}
 ]
}}
"""
    
    else:
        return None
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(
            sys + "\n" + prompt,
            generation_config={"temperature": 0.7, "top_p": 0.9, "max_output_tokens": 1024}
        )
        text = resp.text or ""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None
        
        data = json.loads(text[start:end+1])
        return data
        
    except Exception:
        return None
    


