import os, json, random
from typing import Optional, Dict, List

try:
    import google.generativeai as genai  # SDK đúng cần dùng
    _GENAI_IMPORT_ERROR = None
except Exception as e:
    genai = None
    _GENAI_IMPORT_ERROR = e
    
GEMINI_MODEL_QA   = os.environ.get("GEMINI_MODEL_QA", "gemini-2.5-flash")
GEMINI_MODEL_GRADE= os.environ.get("GEMINI_MODEL_GRADE", "gemini-2.5-flash")

def clean_transcript_phrases(text: str) -> str:
    """
    Loại bỏ các cụm câu / dòng rác sinh ra từ transcript / prompt
    như 'Dựa trên nội dung video', 'ever heard...', 'Hey there', 'WEBVTT'...
    để câu trả lời trông tự nhiên như trợ giảng bình thường.
    """
    if not text:
        return ""

    import re

    # 1) Xóa hẳn các cụm đầu dòng hay nguyên dòng
    patterns = [
        r'^Dựa trên nội dung video[:\s]*',
        r'^Dựa trên transcript[:\s]*',
        r'^Dựa trên[:\s]*',
        r'WEBVTT[^\n]*',
        r'Hey there![^\n]*',
        r'Hey[^\n]*',
        r'Ever heard of[^\n]*',
        r'ever heard of[^\n]*',
        r'Ever heard[^\n]*',
        r'ever heard[^\n]*',
        r'Well, they\'re[^\n]*',
        r'well, they\'re[^\n]*',
        r'Kind of[^\n]*',
        r'kind of[^\n]*',
        r'Today,[^\n]*',
        r'today,[^\n]*',
        r'Ready\?[^\n]*',
        r'ready\?[^\n]*',
        r'variables they\'re[^\n]*',
        r'Variables they\'re[^\n]*',
        # Nếu bạn muốn cực đoan như bản cũ:
        # r'little[^\n]*',
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

    # 2) Bỏ luôn cả những dòng chỉ toàn mấy cụm vô nghĩa đó
    banned_substrings = [
        "ever heard",
        "hey there",
        "well, they",
        "kind of",
        "today,",
        "ready?",
        "variables they",
        "webvtt",
    ]

    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()
        if any(bad in line_lower for bad in banned_substrings):
            continue
        cleaned_lines.append(line_stripped)

    return "\n".join(cleaned_lines).strip()


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
    Phân tích và trích xuất NỘI DUNG CHÍNH từ tài liệu theo phong cách NotebookLM:
    1. Tóm tắt nội dung chính và tạo dàn ý 8-15 ý (để video dài 2-3 phút)
    2. Viết script chi tiết, tự nhiên như giáo viên (30-50 từ/mục, 10-20 giây)
    3. Lấy hình ảnh liên quan trong file hoặc tự tạo hình AI phù hợp
    4. Tạo giọng đọc TTS tự nhiên
    5. Dựng video: mỗi mục 10-20 giây, kèm hình minh họa và phụ đề ngắn
    6. Tập trung vào tính logic, rõ ràng, không đọc nguyên văn PDF
    7. Phong cách NotebookLM: giải thích chi tiết, có ví dụ, dễ hiểu
    
    Args:
        document_text: Nội dung đầy đủ của tài liệu
    
    Returns:
        Dict chứa nội dung chính, cấu trúc bài giảng (8-15 slides), và gợi ý hình ảnh
        Tổng thời lượng video: 120-180 giây (2-3 phút)
    """
    if not _ensure():
        return None
    
    sys = (
        "Bạn là một giáo viên AI chuyên nghiệp, có nhiệm vụ phân tích tài liệu và tạo video bài giảng "
        "theo phong cách NotebookLM - chi tiết, tự nhiên, và dễ hiểu. QUAN TRỌNG: Tập trung vào tính LOGIC, RÕ RÀNG, KHÔNG đọc nguyên văn PDF. "
        "Nhiệm vụ của bạn: "
        "- Tóm tắt nội dung chính và tạo dàn ý 8-15 ý rõ ràng, logic (để video dài 2-3 phút) "
        "- Viết script chi tiết, tự nhiên như giáo viên thật đang giảng bài (30-50 từ/mục, 10-20 giây) "
        "- Gợi ý hình ảnh phù hợp với nội dung (ưu tiên hình trong file, sau đó là AI-generated) "
        "- Mỗi mục/slide có thời lượng 10-20 giây với phụ đề ngắn gọn "
        "- Đảm bảo nội dung logic, dễ hiểu, không sao chép nguyên văn từ PDF "
        "- Phong cách giống NotebookLM: giải thích chi tiết, có ví dụ, dễ hiểu"
    )
    
    prompt = f"""
TÀI LIỆU NGUỒN: <<<BEGIN>>>
{document_text.strip()}
<<<END>>>

QUY TRÌNH TẠO VIDEO BÀI GIẢNG THEO PHONG CÁCH NOTEBOOKLM (BẮT BUỘC):

1. TÓM TẮT NỘI DUNG CHÍNH VÀ TẠO DÀN Ý 10-15 Ý (BẮT BUỘC):
   - Đọc kỹ toàn bộ tài liệu, hiểu ý chính và chi tiết
   - Tóm tắt nội dung chính thành TỐI THIỂU 10-12 ý lớn (KHÔNG được ít hơn 10)
   - Nếu tài liệu ngắn: Chia nhỏ từng ý thành nhiều slides (ví dụ: "Khái niệm cơ bản" → "Định nghĩa", "Đặc điểm", "Ví dụ")
   - Nếu tài liệu dài: Chọn 12-15 điểm quan trọng nhất
   - Mỗi ý phải logic, rõ ràng, dễ hiểu, có thể giải thích chi tiết
   - Sắp xếp theo thứ tự từ cơ bản đến nâng cao
   - Giữ lại các điểm quan trọng và ví dụ minh họa

2. VIẾT SCRIPT CHI TIẾT, TỰ NHIÊN NHƯ GIÁO VIÊN (PHONG CÁCH NOTEBOOKLM):
   - Script cho mỗi mục: 12-18 giây (khoảng 35-55 từ) - QUAN TRỌNG để đạt tổng 2-3 phút
   - Viết như giáo viên thật đang giảng bài, giải thích chi tiết
   - Sử dụng ngôn ngữ tự nhiên, dễ hiểu, có ví dụ cụ thể
   - Giải thích rõ ràng các khái niệm, không chỉ liệt kê
   - KHÔNG sao chép nguyên văn từ PDF, diễn đạt lại bằng lời của giáo viên
   - Phong cách NotebookLM: Giải thích từng bước, có context, dễ hiểu

3. HÌNH ẢNH PHÙ HỢP VỚI NỘI DUNG:
   - Ưu tiên: Hình ảnh có trong file tài liệu (nếu có)
   - Sau đó: Tự tạo hình AI phù hợp với nội dung từng mục
   - Mỗi mục có 2-3 từ khóa hình ảnh cụ thể, rõ ràng
   - Hình ảnh phải minh họa đúng nội dung, không chỉ trang trí

4. PHỤ ĐỀ NGẮN GỌN:
   - Mỗi mục có phụ đề ngắn (5-10 từ) tóm tắt nội dung
   - Phụ đề hiển thị trong 10-20 giây của mục đó
   - Phụ đề rõ ràng, dễ đọc, không quá dài

5. TÍNH LOGIC VÀ RÕ RÀNG (PHONG CÁCH NOTEBOOKLM):
   - Nội dung phải có logic, mạch lạc, giải thích từng bước
   - Các mục liên kết với nhau một cách tự nhiên
   - Tránh nhảy cóc, đảm bảo học viên dễ theo dõi
   - KHÔNG đọc nguyên văn PDF, phải diễn giải lại
   - Giống NotebookLM: Giải thích chi tiết, có context, dễ hiểu

YÊU CẦU CẤU TRÚC (VIDEO 2-3 PHÚT - BẮT BUỘC):
- Tổng số mục: TỐI THIỂU 10-12 slides (KHÔNG được ít hơn), tối đa 15 slides
- Mỗi mục: 12-18 giây (để đảm bảo tổng thời lượng đạt 2-3 phút)
- Script mỗi mục: 35-55 từ, tự nhiên như giáo viên, giải thích chi tiết
- Phụ đề: 5-10 từ, ngắn gọn
- Tổng thời lượng: PHẢI đạt ít nhất 120 giây (2 phút), tốt nhất là 150-180 giây (2.5-3 phút)
- QUAN TRỌNG: Nếu tài liệu ngắn, chia nhỏ nội dung thành nhiều slides. Nếu tài liệu dài, chọn 12-15 điểm quan trọng nhất.

JSON schema:
{{
  "main_topic": "Chủ đề chính của tài liệu",
  "summary": "Tóm tắt ngắn gọn nội dung chính (2-3 câu)",
  "outline": ["Ý 1", "Ý 2", "Ý 3", "Ý 4", "Ý 5", "Ý 6", "Ý 7", "Ý 8", "Ý 9", "Ý 10"],
  "lecture_title": "Tiêu đề bài giảng hấp dẫn",
  "introduction": {{
    "script": "Script giới thiệu chi tiết (12-15 giây, 35-45 từ), tự nhiên như giáo viên, giải thích rõ ràng",
    "subtitle": "Phụ đề ngắn (5-10 từ)",
    "image_keywords": ["từ khóa hình ảnh 1", "từ khóa hình ảnh 2"],
    "duration_sec": 14
  }},
  "slides": [
    {{
      "slide_number": 1,
      "title": "Tiêu đề mục (ngắn gọn)",
      "script": "Script chi tiết (12-18 giây, 35-55 từ), tự nhiên như giáo viên, giải thích rõ ràng từng bước, có ví dụ, KHÔNG đọc nguyên văn PDF",
      "subtitle": "Phụ đề ngắn (5-10 từ)",
      "key_points": ["Điểm quan trọng 1", "Điểm quan trọng 2"],
      "image_keywords": ["từ khóa hình ảnh cụ thể 1", "từ khóa hình ảnh cụ thể 2"],
      "duration_sec": 15
    }}
  ],
  "conclusion": {{
    "script": "Script kết luận chi tiết (12-15 giây, 35-45 từ)",
    "subtitle": "Phụ đề ngắn (5-10 từ)",
    "key_takeaways": ["Điểm chính 1", "Điểm chính 2"],
    "image_keywords": ["từ khóa hình ảnh"],
    "duration_sec": 14
  }},
  "total_duration_seconds": 180
}}
"""
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_QA)
        resp = model.generate_content(
            sys + "\n" + prompt,
            generation_config={
                "temperature": 0.2,  # Tăng một chút để có sự đa dạng
                "top_p": 0.9, 
                "max_output_tokens": 8192,  # Tăng để đảm bảo tạo đủ 8-15 slides chi tiết
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

    # ---- Lịch sử hội thoại ----
    history = history or []
    conv_lines: List[str] = []
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

    q_lower = question.lower()

    # ---- 1) Nhận diện câu hỏi TÓM TẮT -> dùng transcript ----
    summarize_keywords = [
        "tóm tắt", "tom tat",
        "tóm tắt đoạn", "tom tat doan",
        "tổng hợp", "tong hop",
        "tóm gọn", "tom gon",
        "tóm lại", "tom lai",
    ]
    is_summarize = any(kw in q_lower for kw in summarize_keywords)

    model = genai.GenerativeModel(GEMINI_MODEL_QA)

    try:
        # ===== MODE 1: TÓM TẮT DỰA TRÊN TRANSCRIPT =====
        if is_summarize and transcript:
            sys_prompt = (
                "Bạn là TRỢ GIẢNG AI của một khóa học online.\n"
                "Nhiệm vụ: tóm tắt / diễn giải lại nội dung video DỰA TRÊN TRANSCRIPT dưới đây.\n"
                "- Chỉ sử dụng thông tin có trong transcript; không bịa thêm kiến thức khác.\n"
                "- Trả lời ngắn gọn, súc tích, đúng trọng tâm câu hỏi của học viên.\n"
                "- Viết bằng tiếng Việt, dễ hiểu với người mới học.\n"
            )
            prompt = f"""
TRANSCRIPT VIDEO BÀI GIẢNG:
<<<TRANSCRIPT>>>
{transcript}
<<<END_TRANSCRIPT>>>

CÂU HỎI CỦA HỌC VIÊN:
{question}

LỊCH SỬ HỘI THOẠI (nếu có):
{history_text}
"""
            resp = model.generate_content(
                sys_prompt + "\n\n" + prompt,
                generation_config={"temperature": 0.4, "max_output_tokens": 1024},
            )
            answer = (getattr(resp, "text", "") or "").strip()
            answer = clean_transcript_phrases(answer)
            return {"related": True, "answer": answer}

        # ===== MODE 2: CÂU HỎI GIẢI THÍCH / MỞ RỘNG =====
        # Không dùng transcript để trả lời, chỉ dùng để biết CHỦ ĐỀ
        if transcript:
            topic_summary = transcript[:800]  # lấy khoảng 800 ký tự đầu làm mô tả chủ đề
        else:
            topic_summary = "Lập trình / khoa học máy tính cơ bản."

        sys_prompt = """
Bạn là TRỢ GIẢNG AI chuyên nghiệp trong một khóa học lập trình.

BẠN KHÔNG CÓ TRANSCRIPT CHI TIẾT CỦA VIDEO.
Bạn CHỈ có mô tả rất ngắn về CHỦ ĐỀ BÀI HỌC (TOPIC) ở dưới.

NHIỆM VỤ:
1. Xác định xem câu hỏi của học viên có LIÊN QUAN đến chủ đề bài học hoặc kiến thức nền xung quanh hay không.
2. Nếu LIÊN QUAN → giải thích chi tiết cho người mới học, bằng tiếng Việt, có ví dụ dễ hiểu.
3. Nếu HOÀN TOÀN KHÔNG LIÊN QUAN (tình yêu, ăn uống, du lịch, thời tiết, bóng đá, showbiz, v.v.) → đánh dấu là không liên quan, KHÔNG trả lời nội dung.

QUY TẮC TRẢ LỜI:
- Tuyệt đối KHÔNG được bắt đầu bằng: "Dựa trên nội dung video", "Dựa trên transcript", "Dựa trên...", v.v.
- Tuyệt đối KHÔNG dùng các cụm: "Ever heard of", "Hey there", "Well, they're", "Today,", "Ready?", "variables they're little".
- Trả lời TRỰC TIẾP như một trợ lý ảo bình thường.
- Bắt đầu ngay với nội dung trả lời (ví dụ: "String (chuỗi) là...", "Trong Python, kiểu dữ liệu string...").

HÃY TRẢ LỜI ĐÚNG ĐỊNH DẠNG SAU (bắt buộc, không thêm ký hiệu khác):
RELATED: yes/no
ANSWER: <câu trả lời tiếng Việt, để trống nếu RELATED: no>
"""

        prompt = f"""
TOPIC (chỉ để bạn biết đang học về gì, KHÔNG được trích nguyên văn):
{topic_summary}

LỊCH SỬ HỘI THOẠI:
{history_text}

CÂU HỎI CỦA HỌC VIÊN:
{question}
"""

        resp = model.generate_content(
            sys_prompt + "\n\n" + prompt,
            generation_config={"temperature": 0.5, "max_output_tokens": 1024},
        )
        raw = (getattr(resp, "text", "") or "").strip()
        if not raw:
            return {"related": False, "answer": ""}

        # ---- Parse RELATED/ANSWER ----
        lower = raw.lower()
        related = True
        answer = raw

        if "related:" in lower:
            rel_line = lower.split("related:", 1)[1].splitlines()[0]
            if "no" in rel_line:
                related = False
            elif "yes" in rel_line:
                related = True

            if "answer:" in lower:
                ans_idx = lower.find("answer:")
                answer = raw[ans_idx + len("answer:"):].strip()
        else:
            # Không đúng format → coi như liên quan và dùng toàn bộ câu trả lời
            related = True
            answer = raw

        # Làm sạch mấy câu mở đầu khó chịu
        answer = clean_transcript_phrases(answer)

        # ---- Override: nếu câu hỏi rõ ràng là học tập thì luôn coi là related ----
        learning_keywords_extended = [
            "tóm tắt", "tom tat", "giải thích", "giai thich", "ví dụ", "vi du",
            "khái niệm", "khai niem", "nội dung", "noi dung", "video", "bài học", "bai hoc",
            "học", "hoc", "giảng", "giang", "dạy", "day", "nói", "noi", "chi tiết", "chi tiet",
            "kiểu", "kieu", "dữ liệu", "du lieu", "biến", "bien", "hàm", "ham", "số", "so",
            "nguyên", "nguyen", "thực", "thuc", "chuỗi", "chuoi", "danh sách", "danh sach",
            "là gì", "la gi", "như thế nào", "nhu the nao", "cách", "cach", "thế nào", "the nao",
        ]
        if not related and any(kw in q_lower for kw in learning_keywords_extended):
            print("[GEMINI-CHAT] Override: câu hỏi có từ khóa học tập, force related=True")
            related = True
            if not answer:
                try:
                    retry = model.generate_content(
                        "Bạn là trợ giảng lập trình. "
                        "Hãy giải thích chi tiết, dễ hiểu bằng tiếng Việt cho người mới học:\n\n"
                        + question,
                        generation_config={"temperature": 0.5, "max_output_tokens": 1024},
                    )
                    answer = (getattr(retry, "text", "") or "").strip()
                    answer = clean_transcript_phrases(answer)
                except Exception as e2:
                    print(f"[GEMINI-CHAT] Retry error: {e2}")
                    answer = ""

        print(
            f"[GEMINI-CHAT] related={related}, "
            f"answer_len={len(answer)}, "
            f"answer_preview={answer[:100]!r}, "
            f"transcript_len={len(transcript)}, "
            f"question={question[:80]!r}"
        )

        if not related:
            return {"related": False, "answer": ""}

        return {"related": True, "answer": answer}

    except Exception as e:
        # QUAN TRỌNG: KHÔNG fallback sang việc cắt 100 từ đầu transcript nữa
        # để tránh kiểu trả lời "Dựa trên nội dung video: ever heard variables they're little"
        print(f"⚠️ chat_about_transcript error: {e}")
        import traceback
        traceback.print_exc()

        # Nếu lỗi nhưng câu hỏi rõ ràng là học tập → báo lỗi mềm
        if any(kw in q_lower for kw in ["tóm tắt", "tom tat", "giải thích", "giai thich",
                                        "khái niệm", "khai niem", "bài học", "bai hoc"]):
            return {
                "related": True,
                "answer": (
                    "Xin lỗi, trợ giảng AI đang gặp sự cố khi kết nối tới mô hình Gemini. "
                    "Bạn hãy thử lại sau ít phút hoặc hỏi trực tiếp giảng viên nhé."
                ),
            }

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
    


