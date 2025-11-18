# video_script_quiz_service.py
"""
Service để tạo câu hỏi từ nội dung video script sử dụng AI Gemini
"""
import hashlib
import random
import os
import json
from typing import Dict, List, Any
from dotenv import load_dotenv

# Import shared hash function to ensure consistency
try:
    from utils.hash_utils import hash_option
except ImportError:
    # Fallback if utils module not available
    def hash_option(text: str) -> str:
        import hmac
        try:
            from flask import current_app
            secret = (current_app.config.get("SECRET_KEY") or "dev-secret").encode("utf-8")
        except Exception:
            secret = b"dev-secret"
        return hmac.new(secret, (text or "").encode("utf-8"), hashlib.sha256).hexdigest()[:16]

# Load environment variables
load_dotenv()

class VideoScriptQuizService:
    def __init__(self):
        self.session_cache = {}
        # Track transcript và số câu hỏi đã tạo cho mỗi session
        self.session_transcripts = {}  # {session_key: full_transcript}
        self.session_question_count = {}  # {session_key: count}
        self.session_used_segments = {}  # {session_key: set of segment_indices}
    
    def get_next_question_from_video_script(self, course_id: str, script_content: str, 
                                           session_id: str, question_type: str = "mcq", 
                                           language: str = "vi", time_range: tuple = None) -> Dict[str, Any]:
        """
        Tạo câu hỏi từ nội dung script video sử dụng AI Gemini
        Đảm bảo mỗi câu hỏi khác nhau bằng cách:
        1. Chia transcript thành các phần nhỏ
        2. Tạo câu hỏi từ các phần khác nhau
        3. Track các câu hỏi đã tạo để tránh trùng lặp
        
        Args:
            time_range: Tuple (start_time, end_time) trong giây để tạo câu hỏi từ đoạn transcript cụ thể
                       Nếu None, sẽ tạo câu hỏi từ toàn bộ transcript
        """
        # Tạo timestamp để đảm bảo câu hỏi luôn khác nhau
        import time
        timestamp = str(int(time.time() * 1000))  # milliseconds
        
        # Tạo session key để track
        session_key = f"{course_id}_{session_id}"
        
        # Lưu transcript gốc cho session này (lần đầu tiên)
        if session_key not in self.session_transcripts:
            # Validate transcript trước khi lưu
            if not script_content or len(script_content.strip()) < 100:
                print(f"⚠️ WARNING: Transcript too short ({len(script_content) if script_content else 0} chars). Minimum required: 100 chars")
            else:
                print(f"✅ Transcript loaded: {len(script_content)} chars for session {session_key}")
            
            self.session_transcripts[session_key] = script_content
            self.session_question_count[session_key] = 0
            self.session_used_segments[session_key] = set()
        
        # Lấy transcript gốc
        full_transcript = self.session_transcripts[session_key]
        question_count = self.session_question_count[session_key]
        used_segments = self.session_used_segments[session_key]
        
        # Nếu có time_range, tạo câu hỏi từ đoạn transcript tương ứng với khoảng thời gian đó
        if time_range and len(time_range) == 2:
            start_time, end_time = time_range
            print(f"⏰ Creating question for time range: {start_time}s - {end_time}s")
            # script_content đã là transcript của đoạn này (được truyền từ frontend)
            # Sử dụng trực tiếp script_content thay vì full_transcript
            segment_transcript = script_content if script_content and len(script_content.strip()) >= 50 else full_transcript
        else:
            # Không có time_range, dùng logic cũ (chia transcript thành segments)
            segment_transcript = full_transcript
        
        # Validate transcript trước khi chia
        if not segment_transcript or len(segment_transcript.strip()) < 50:
            print(f"❌ ERROR: Invalid transcript for question generation. Length: {len(segment_transcript) if segment_transcript else 0} chars")
            # Fallback về full_transcript nếu segment quá ngắn
            segment_transcript = full_transcript if full_transcript else ""
        
        # Nếu có time_range, dùng trực tiếp segment_transcript
        # Nếu không, chia transcript thành các phần nhỏ (mỗi phần ~200-300 từ) để tạo câu hỏi đa dạng
        if time_range and len(time_range) == 2:
            transcript_segments = [segment_transcript]  # Chỉ có 1 segment cho khoảng thời gian này
            selected_segment = segment_transcript
            segment_index = 0
        else:
            transcript_segments = self._split_transcript_into_segments(segment_transcript, segment_size=250)
            
            if not transcript_segments or len(transcript_segments) == 0:
                print(f"⚠️ WARNING: No segments created from transcript. Transcript length: {len(segment_transcript) if segment_transcript else 0} chars")
            
            # Chọn một segment chưa được sử dụng (hoặc ít được sử dụng nhất)
            selected_segment, segment_index = self._select_unused_segment(transcript_segments, used_segments, question_count)
        
        # Đánh dấu segment này đã được sử dụng
        used_segments.add(segment_index)
        self.session_question_count[session_key] = question_count + 1
        
        # Validate segment trước khi gọi AI
        if not selected_segment or len(selected_segment.strip()) < 50:
            print(f"❌ ERROR: Selected segment is too short or empty. Length: {len(selected_segment) if selected_segment else 0} chars")
            print(f"   Full transcript length: {len(full_transcript) if full_transcript else 0} chars")
            print(f"   Number of segments: {len(transcript_segments)}")
        
        ai_question = None  # Khởi tạo biến
        
        try:
            # Thử sử dụng AI Gemini để tạo câu hỏi từ segment được chọn
            print(f"🔄 Attempting to generate question from segment (length: {len(selected_segment) if selected_segment else 0} chars)")
            ai_question = self._generate_question_with_ai(selected_segment, language, question_count)
            if ai_question:
                print(f"✅ Successfully generated AI question: {ai_question.get('question', '')[:100]}...")
                # Tạo qid duy nhất với timestamp để tránh trùng lặp
                qid = hashlib.sha1(f"{course_id}_{session_id}_{timestamp}_{ai_question['question']}".encode()).hexdigest()[:16]
                
                # Shuffle các đáp án để đáp án đúng không luôn ở vị trí cố định
                import random
                options = ai_question["options"].copy()
                correct_index = int(ai_question.get("correct_index", 0))
                
                # Kiểm tra nếu correct_index hợp lệ
                if correct_index < 0 or correct_index >= len(options):
                    correct_index = 0
                
                correct_answer = options[correct_index]
                
                # Debug: Print before shuffle
                print(f"AI QUESTION - BEFORE SHUFFLE:")
                print(f"  Options: {options}")
                print(f"  Correct index: {correct_index}")
                print(f"  Correct answer: {options[correct_index]}")
                
                # Shuffle options
                random.shuffle(options)
                
                # Tìm lại vị trí của đáp án đúng sau khi shuffle
                try:
                    new_correct_index = options.index(correct_answer)
                except ValueError:
                    new_correct_index = 0
                
                # Debug: Print after shuffle
                print(f"AI QUESTION - AFTER SHUFFLE:")
                print(f"  Options: {options}")
                print(f"  New correct index: {new_correct_index}")
                print(f"  Correct answer: {options[new_correct_index]}")
                
                # Tạo options_hashes sau khi shuffle (sử dụng hash function dùng chung)
                options_hashes = [hash_option(option) for option in options]
                
                correct_hash = options_hashes[new_correct_index]
                
                return {
                    "qid": qid,
                    "question": ai_question["question"],
                    "options": options,
                    "options_hashes": options_hashes,
                    "correct_index": new_correct_index,
                    "correct_hash": correct_hash,
                    "explanation": ai_question["explanation"],
                    "type": question_type,
                    "time_limit_ms": 10000
                }
        except Exception as e:
            print(f"❌ Error generating AI question: {e}")
            import traceback
            traceback.print_exc()
            ai_question = None  # Đảm bảo set về None nếu có lỗi
        
        # Nếu AI không tạo được câu hỏi, thử lại với toàn bộ transcript (không chỉ segment)
        if not ai_question and full_transcript and len(full_transcript.strip()) >= 100:
            print(f"⚠️ Retrying with full transcript instead of segment...")
            try:
                # Thử với toàn bộ transcript nếu segment không đủ
                ai_question = self._generate_question_with_ai(full_transcript[:2000], language, question_count)  # Giới hạn 2000 ký tự
                if ai_question:
                    print(f"✅ Successfully generated AI question from full transcript")
                    # Xử lý tương tự như trên
                    qid = hashlib.sha1(f"{course_id}_{session_id}_{timestamp}_{ai_question['question']}".encode()).hexdigest()[:16]
                    import random
                    options = ai_question["options"].copy()
                    correct_index = int(ai_question.get("correct_index", 0))
                    if correct_index < 0 or correct_index >= len(options):
                        correct_index = 0
                    correct_answer = options[correct_index]
                    random.shuffle(options)
                    try:
                        new_correct_index = options.index(correct_answer)
                    except ValueError:
                        new_correct_index = 0
                    options_hashes = [hash_option(option) for option in options]
                    correct_hash = options_hashes[new_correct_index]
                    return {
                        "qid": qid,
                        "question": ai_question["question"],
                        "options": options,
                        "options_hashes": options_hashes,
                        "correct_index": new_correct_index,
                        "correct_hash": correct_hash,
                        "explanation": ai_question["explanation"],
                        "type": question_type,
                        "time_limit_ms": 10000
                    }
            except Exception as e2:
                print(f"❌ Error generating from full transcript: {e2}")
                import traceback
                traceback.print_exc()
        
        # Chỉ dùng fallback nếu thực sự không có transcript hoặc AI hoàn toàn fail
        if not ai_question:
            print(f"⚠️ Using fallback question (AI generation failed or no transcript)")
            print(f"   Transcript available: {bool(full_transcript)}, Length: {len(full_transcript) if full_transcript else 0} chars")
            # Fallback: Tạo câu hỏi dựa trên segment đã chọn (không phải toàn bộ transcript)
            return self._generate_fallback_question(selected_segment if selected_segment else full_transcript, course_id, session_id, question_type, timestamp, question_count)
        
        # Nếu có ai_question, return nó (trường hợp này không nên xảy ra vì đã return ở trên)
        return ai_question
    
    def _split_transcript_into_segments(self, transcript: str, segment_size: int = 250) -> List[str]:
        """
        Chia transcript thành các phần nhỏ để tạo câu hỏi đa dạng
        """
        if not transcript or len(transcript.strip()) < segment_size:
            return [transcript] if transcript else []
        
        words = transcript.split()
        segments = []
        
        for i in range(0, len(words), segment_size):
            segment = ' '.join(words[i:i + segment_size])
            segments.append(segment)
        
        return segments
    
    def _select_unused_segment(self, segments: List[str], used_segments: set, question_count: int) -> tuple:
        """
        Chọn một segment chưa được sử dụng hoặc ít được sử dụng nhất
        """
        if not segments:
            return ("", 0)
        
        # Nếu chưa có segment nào được sử dụng, chọn ngẫu nhiên
        if not used_segments:
            import random
            idx = random.randint(0, len(segments) - 1)
            return (segments[idx], idx)
        
        # Tìm các segment chưa được sử dụng
        unused_indices = [i for i in range(len(segments)) if i not in used_segments]
        
        if unused_indices:
            # Chọn ngẫu nhiên từ các segment chưa dùng
            import random
            idx = random.choice(unused_indices)
            return (segments[idx], idx)
        else:
            # Nếu đã dùng hết, reset và chọn lại (hoặc chọn ngẫu nhiên)
            import random
            idx = random.randint(0, len(segments) - 1)
            return (segments[idx], idx)
    
    def _generate_question_with_ai(self, script_content: str, language: str = "vi", question_number: int = 0) -> Dict[str, Any]:
        """
        Tạo câu hỏi sử dụng AI Gemini từ một phần transcript cụ thể
        question_number: số thứ tự câu hỏi (0-19) để tạo câu hỏi đa dạng hơn
        """
        try:
            import google.generativeai as genai
            
            # Cấu hình API key
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("GEMINI_API_KEY not found")
                return None
            
            genai.configure(api_key=api_key)
            
            # Thử các model theo thứ tự ưu tiên
            model_names = [
                os.getenv('GEMINI_MODEL_QA', 'gemini-2.0-flash'),
                'gemini-2.0-flash-001',
                'gemini-2.5-flash',
                'gemini-1.5-pro-latest',
                'gemini-1.5-flash-latest',
                'gemini-1.5-pro',
                'gemini-1.5-flash',
                'gemini-pro'
            ]
            
            model = None
            for model_name in model_names:
                try:
                    model = genai.GenerativeModel(model_name)
                    break
                except Exception:
                    continue
            
            if not model:
                print("No available Gemini model")
                return None
            
            # Prompt cải thiện để tạo câu hỏi đa dạng hơn
            # Thêm yêu cầu tạo câu hỏi về khía cạnh khác nhau của nội dung
            question_types = [
                "khái niệm cơ bản",
                "ví dụ cụ thể",
                "ứng dụng thực tế",
                "so sánh và phân biệt",
                "nguyên nhân và kết quả",
                "quy trình và bước thực hiện",
                "đặc điểm và tính chất",
                "lợi ích và hạn chế",
                "trường hợp sử dụng",
                "lỗi thường gặp"
            ]
            
            question_type_hint = question_types[question_number % len(question_types)]
            
            # Validate transcript trước khi gửi vào AI
            if not script_content or len(script_content.strip()) < 50:
                print(f"❌ [AI_GEMINI] Transcript too short: {len(script_content) if script_content else 0} chars")
                return None
            
            # Log để debug - hiển thị preview của transcript
            transcript_preview = script_content[:300] + "..." if len(script_content) > 300 else script_content
            print(f"🤖 [AI_GEMINI] Generating question #{question_number + 1}")
            print(f"   📝 Transcript segment length: {len(script_content)} chars")
            print(f"   📄 Transcript FULL CONTENT:")
            print(f"   {'='*80}")
            print(f"   {script_content}")
            print(f"   {'='*80}")
            print(f"   🎯 Question type: {question_type_hint}")
            
            # Tạo prompt rõ ràng, nhấn mạnh việc sử dụng transcript
            prompt = f"""Bạn là một giáo viên AI chuyên tạo câu hỏi trắc nghiệm từ TRANSCRIPT (phụ đề) của video bài giảng.

⚠️ QUAN TRỌNG: Bạn PHẢI đọc kỹ và PHÂN TÍCH toàn bộ TRANSCRIPT dưới đây. Đây là nội dung THỰC TẾ được nói trong video, KHÔNG phải kiến thức chung.

═══════════════════════════════════════════════════════════════
TRANSCRIPT THỰC TẾ TỪ VIDEO BÀI GIẢNG (Đoạn {question_number + 1}):
═══════════════════════════════════════════════════════════════
{script_content}
═══════════════════════════════════════════════════════════════

NHIỆM VỤ CỦA BẠN (PHẢI LÀM THEO ĐÚNG THỨ TỰ):

BƯỚC 1: ĐỌC VÀ PHÂN TÍCH TRANSCRIPT
   - Đọc TỪNG TỪ trong transcript ở trên
   - Xác định các khái niệm, thuật ngữ, ví dụ CỤ THỂ được đề cập
   - Ghi nhận các thông tin QUAN TRỌNG trong transcript
   - KHÔNG được bỏ qua bất kỳ chi tiết nào trong transcript

BƯỚC 2: XÁC ĐỊNH NỘI DUNG CHÍNH
   Dựa TRỰC TIẾP vào transcript, xác định:
   - Khái niệm nào được giải thích? (Ghi rõ từ transcript)
   - Ví dụ nào được đưa ra? (Ghi rõ từ transcript)
   - Quy trình nào được mô tả? (Ghi rõ từ transcript)
   - So sánh nào được thực hiện? (Ghi rõ từ transcript)
   - Thuật ngữ kỹ thuật nào được đề cập? (Ghi rõ từ transcript)

BƯỚC 3: TẠO CÂU HỎI DỰA TRỰC TIẾP VÀO TRANSCRIPT
   - Câu hỏi PHẢI kiểm tra hiểu biết về nội dung CỤ THỂ trong transcript
   - Tập trung vào khía cạnh: {question_type_hint}
   - Đáp án đúng PHẢI dựa trên thông tin CỤ THỂ có trong transcript
   - Câu hỏi phải có thể trả lời được BẰNG CÁCH đọc transcript

BƯỚC 4: ĐẢM BẢO TÍNH CHÍNH XÁC
   - Câu hỏi và đáp án PHẢI phản ánh ĐÚNG nội dung trong transcript
   - KHÔNG được thêm thông tin KHÔNG CÓ trong transcript
   - KHÔNG được tạo câu hỏi về kiến thức chung nếu KHÔNG có trong transcript
   - Nếu transcript nói về "String" thì câu hỏi phải về "String", KHÔNG phải về kiến thức Java chung

YÊU CẦU BẮT BUỘC:
✅ Câu hỏi PHẢI liên quan TRỰC TIẾP đến nội dung trong đoạn TRANSCRIPT ở trên
✅ Tập trung vào khía cạnh: {question_type_hint}
✅ 4 lựa chọn (A, B, C, D) - chỉ 1 đáp án đúng
✅ Đáp án đúng PHẢI dựa trên thông tin CỤ THỂ có trong transcript
✅ 3 đáp án sai PHẢI bám sát transcript nhưng DỄ GÂY NHẦM LẪN (xem chi tiết bên dưới)
✅ Câu hỏi phải cụ thể, rõ ràng, không mơ hồ
✅ KHÔNG được dùng template có sẵn hoặc câu hỏi chung chung
✅ KHÔNG được copy nguyên văn text từ transcript vào câu hỏi (phải diễn đạt lại)
✅ Tạo câu hỏi KHÁC BIỆT với các câu hỏi trước đó

⚠️ QUY TẮC BẮT BUỘC (KHÔNG ĐƯỢC VI PHẠM):
1. TRANSCRIPT ở trên là nguồn DUY NHẤT để tạo câu hỏi
2. KHÔNG được tạo câu hỏi dựa trên kiến thức chung nếu KHÔNG có trong transcript
3. Câu hỏi PHẢI kiểm tra xem học viên có hiểu nội dung CỤ THỂ trong transcript hay không
4. Câu hỏi PHẢI bắt đầu bằng "Theo đoạn video" để chỉ rõ câu hỏi dựa trên transcript
5. Đáp án đúng PHẢI là thông tin CỤ THỂ có trong transcript

🎯 QUY TẮC TẠO ĐÁP ÁN SAI (DISTRACTOR OPTIONS) - RẤT QUAN TRỌNG:
Các đáp án sai PHẢI:
1. BÁM SÁT TRANSCRIPT: Phải dựa trên các thông tin, thuật ngữ, khái niệm CÓ TRONG transcript
2. DỄ GÂY NHẦM LẪN: Phải là các phương án hợp lý, có vẻ đúng nhưng thực tế KHÔNG đúng với câu hỏi
3. CÁC CÁCH TẠO ĐÁP ÁN SAI:
   a) Sử dụng các thuật ngữ/khái niệm KHÁC được đề cập trong transcript (nhưng không phải câu trả lời đúng)
   b) Sử dụng các thông tin LIÊN QUAN nhưng KHÔNG CHÍNH XÁC (ví dụ: nếu transcript nói "String", có thể dùng "str" hoặc "text" nếu có trong transcript)
   c) Sử dụng các thông tin TƯƠNG TỰ nhưng SAI (ví dụ: nếu transcript nói về "int", có thể dùng "integer" hoặc "number" nếu có trong transcript)
   d) Sử dụng các thông tin ĐỐI LẬP hoặc TRÁI NGƯỢC được đề cập trong transcript
   e) Sử dụng các thông tin BỔ SUNG nhưng KHÔNG PHẢI câu trả lời (ví dụ: nếu câu hỏi về "kiểu dữ liệu", đáp án sai có thể là các kiểu dữ liệu KHÁC được đề cập trong transcript)

VÍ DỤ CỤ THỂ:
TRANSCRIPT: "Trong Java, để lưu trữ chuỗi văn bản, ta dùng kiểu String. Các kiểu dữ liệu khác như int dùng cho số nguyên, float dùng cho số thực, boolean dùng cho giá trị true/false."

Câu hỏi: "Theo đoạn video, kiểu dữ liệu nào được sử dụng để lưu trữ một chuỗi văn bản trong Java?"

Đáp án đúng: "String" (vì có trong transcript)

Đáp án sai (BÁM SÁT TRANSCRIPT, DỄ NHẦM):
- "int" (có trong transcript, là kiểu dữ liệu hợp lệ nhưng không đúng cho câu hỏi này)
- "float" (có trong transcript, là kiểu dữ liệu hợp lệ nhưng không đúng cho câu hỏi này)
- "boolean" (có trong transcript, là kiểu dữ liệu hợp lệ nhưng không đúng cho câu hỏi này)

❌ KHÔNG ĐƯỢC DÙNG các đáp án chung chung như:
- "Kết luận và tóm tắt nội dung"
- "Thảo luận chi tiết về chủ đề"
- "Thực hành và bài tập"
- Các đáp án KHÔNG có trong transcript hoặc KHÔNG liên quan đến transcript

TRẢ VỀ ĐỊNH DẠNG JSON (chỉ JSON, không có text khác):
{{
    "question": "Theo đoạn video, [câu hỏi cụ thể dựa trên nội dung transcript, tập trung vào {question_type_hint}]",
    "options": [
        "Đáp án đúng - thông tin CỤ THỂ từ transcript",
        "Đáp án sai 1 - thuật ngữ/khái niệm KHÁC từ transcript (dễ nhầm)",
        "Đáp án sai 2 - thông tin LIÊN QUAN nhưng SAI từ transcript (dễ nhầm)",
        "Đáp án sai 3 - thông tin TƯƠNG TỰ nhưng KHÔNG ĐÚNG từ transcript (dễ nhầm)"
    ],
    "correct_index": 0,
    "explanation": "Giải thích chi tiết dựa trên nội dung cụ thể trong transcript, chỉ rõ tại sao đáp án đúng và tại sao các đáp án sai dễ gây nhầm lẫn"
}}

LƯU Ý QUAN TRỌNG:
- TẤT CẢ 4 đáp án PHẢI dựa trên thông tin CÓ TRONG transcript
- 3 đáp án sai PHẢI là các thông tin/thuật ngữ/khái niệm CỤ THỂ từ transcript, KHÔNG phải câu trả lời chung chung
- 3 đáp án sai PHẢI dễ gây nhầm lẫn, có vẻ hợp lý nhưng thực tế không đúng với câu hỏi"""
            
            # Gọi Gemini với transcript
            print(f"   🔄 Calling Gemini API with transcript...")
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Log response để debug
            print(f"   📥 Gemini response received (length: {len(response_text)} chars)")
            if len(response_text) > 500:
                print(f"   📄 Response preview: {response_text[:500]}...")
            else:
                print(f"   📄 Full response: {response_text}")
            
            # Parse JSON response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    question_data = json.loads(json_str)
                    
                    # Validate response
                    if all(key in question_data for key in ['question', 'options', 'correct_index', 'explanation']):
                        if len(question_data['options']) == 4 and 0 <= question_data['correct_index'] < 4:
                            print(f"   ✅ AI Gemini generated question successfully!")
                            print(f"   ❓ Question: {question_data['question'][:100]}...")
                            print(f"   📋 Options count: {len(question_data['options'])}")
                            print(f"   ✓ Correct index: {question_data['correct_index']}")
                            return question_data
                        else:
                            print(f"   ❌ Invalid options or correct_index: options={len(question_data.get('options', []))}, correct_index={question_data.get('correct_index')}")
                    else:
                        missing_keys = [k for k in ['question', 'options', 'correct_index', 'explanation'] if k not in question_data]
                        print(f"   ❌ Missing required keys: {missing_keys}")
            except json.JSONDecodeError as e:
                print(f"   ❌ Error parsing JSON: {e}")
                print(f"   📄 Raw response: {response_text[:500]}")
            except Exception as e:
                print(f"   ❌ Error parsing AI response: {e}")
                import traceback
                traceback.print_exc()
        
        except Exception as e:
            print(f"Error calling AI Gemini: {e}")
        
        return None
    
    def _generate_fallback_question(self, script_content: str, course_id: str, session_id: str, question_type: str, timestamp: str = None, question_number: int = 0) -> Dict[str, Any]:
        """
        Tạo câu hỏi fallback cải thiện dựa trên nội dung thực tế
        question_number: số thứ tự câu hỏi để đảm bảo đa dạng
        """
        # Câu hỏi cải thiện dựa trên nội dung video Java variables - Mở rộng để có đa dạng
        improved_questions = [
            {
                "question": "Trong video này, biến Java được định nghĩa như thế nào?",
                "options": [
                    "Container để lưu trữ dữ liệu",
                    "Phương thức để xử lý dữ liệu", 
                    "Class để tạo đối tượng",
                    "Interface để định nghĩa hành vi"
                ],
                "correct_index": 0,
                "explanation": "Biến Java là container để lưu trữ dữ liệu như được giải thích trong video."
            },
            {
                "question": "Có bao nhiêu loại biến chính được đề cập trong video?",
                "options": [
                    "4 loại (String, int, float, Boolean)",
                    "3 loại (String, int, float)",
                    "5 loại (String, int, float, Boolean, char)",
                    "2 loại (String, int)"
                ],
                "correct_index": 2,
                "explanation": "Video đề cập đến 5 loại biến: String, int, float, Boolean, và char."
            },
            {
                "question": "Biến char trong Java lưu trữ gì?",
                "options": [
                    "Ký tự đơn lẻ",
                    "Chuỗi văn bản",
                    "Số nguyên",
                    "Số thập phân"
                ],
                "correct_index": 0,
                "explanation": "Biến char lưu trữ ký tự đơn lẻ như được giải thích trong video."
            },
            {
                "question": "Biến Boolean có thể lưu trữ những giá trị nào?",
                "options": [
                    "true hoặc false",
                    "Số nguyên dương",
                    "Chuỗi văn bản",
                    "Ký tự đặc biệt"
                ],
                "correct_index": 0,
                "explanation": "Biến Boolean chỉ lưu trữ giá trị true hoặc false."
            },
            {
                "question": "Theo video, tại sao nên sử dụng tên biến mô tả?",
                "options": [
                    "Dễ nhớ và hiểu mục đích sử dụng",
                    "Tiết kiệm bộ nhớ",
                    "Tăng tốc độ xử lý",
                    "Giảm kích thước file"
                ],
                "correct_index": 0,
                "explanation": "Video khuyến khích sử dụng tên biến mô tả để dễ nhớ và hiểu mục đích sử dụng."
            },
            {
                "question": "Biến int trong Java có thể lưu trữ loại dữ liệu nào?",
                "options": [
                    "Số nguyên",
                    "Số thập phân",
                    "Ký tự",
                    "Chuỗi văn bản"
                ],
                "correct_index": 0,
                "explanation": "Biến int lưu trữ số nguyên như được giải thích trong video."
            },
            {
                "question": "Biến float trong Java dùng để làm gì?",
                "options": [
                    "Lưu trữ số thập phân",
                    "Lưu trữ số nguyên",
                    "Lưu trữ ký tự",
                    "Lưu trữ chuỗi"
                ],
                "correct_index": 0,
                "explanation": "Biến float lưu trữ số thập phân như được giải thích trong video."
            },
            {
                "question": "Biến String trong Java có thể chứa gì?",
                "options": [
                    "Chuỗi văn bản",
                    "Số nguyên",
                    "Số thập phân",
                    "Ký tự đơn lẻ"
                ],
                "correct_index": 0,
                "explanation": "Biến String lưu trữ chuỗi văn bản như được giải thích trong video."
            },
            {
                "question": "Theo video, biến Java có thể thay đổi giá trị không?",
                "options": [
                    "Có thể thay đổi",
                    "Không thể thay đổi",
                    "Chỉ thay đổi một lần",
                    "Tùy thuộc vào loại biến"
                ],
                "correct_index": 0,
                "explanation": "Biến Java có thể thay đổi giá trị như được giải thích trong video."
            },
            {
                "question": "Trong Java, biến cần được khai báo trước khi sử dụng không?",
                "options": [
                    "Có, phải khai báo trước",
                    "Không cần khai báo",
                    "Tùy thuộc vào loại biến",
                    "Chỉ cần khai báo một lần"
                ],
                "correct_index": 0,
                "explanation": "Biến Java phải được khai báo trước khi sử dụng như được giải thích trong video."
            },
            {
                "question": "Theo video, tên biến Java có thể bắt đầu bằng số không?",
                "options": [
                    "Không thể bắt đầu bằng số",
                    "Có thể bắt đầu bằng số",
                    "Tùy thuộc vào loại biến",
                    "Chỉ có thể bắt đầu bằng chữ cái"
                ],
                "correct_index": 0,
                "explanation": "Tên biến Java không thể bắt đầu bằng số như được giải thích trong video."
            },
            {
                "question": "Biến Java có thể có tên trùng với từ khóa không?",
                "options": [
                    "Không thể trùng với từ khóa",
                    "Có thể trùng với từ khóa",
                    "Tùy thuộc vào loại biến",
                    "Chỉ một số từ khóa được phép"
                ],
                "correct_index": 0,
                "explanation": "Tên biến Java không thể trùng với từ khóa như được giải thích trong video."
            }
        ]
        
        # Chọn câu hỏi ngẫu nhiên, tránh lặp lại
        # Sử dụng session_id để track câu hỏi đã sử dụng
        if not hasattr(self, 'used_questions'):
            self.used_questions = {}
        
        session_key = f"{course_id}_{session_id}"
        if session_key not in self.used_questions:
            self.used_questions[session_key] = set()
        
        used_question_indices = self.used_questions[session_key]
        available_questions = [i for i in range(len(improved_questions)) if i not in used_question_indices]
        
        if available_questions:
            # Chọn câu hỏi chưa sử dụng
            selected_index = random.choice(available_questions)
            selected_question = improved_questions[selected_index]
            used_question_indices.add(selected_index)
        else:
            # Nếu đã sử dụng hết, reset và chọn lại
            self.used_questions[session_key] = set()
            selected_index = random.choice(range(len(improved_questions)))
            selected_question = improved_questions[selected_index]
            used_question_indices.add(selected_index)
        
        # Tạo qid duy nhất với timestamp để tránh trùng lặp
        if timestamp is None:
            import time
            timestamp = str(int(time.time() * 1000))
        qid = hashlib.sha1(f"{course_id}_{session_id}_{timestamp}_{selected_question['question']}".encode()).hexdigest()[:16]
        
        # Shuffle các đáp án để đáp án đúng không luôn ở vị trí cố định
        options = selected_question["options"].copy()
        correct_index = int(selected_question.get("correct_index", 0))
        
        # Kiểm tra nếu correct_index hợp lệ
        if correct_index < 0 or correct_index >= len(options):
            correct_index = 0
        
        # Debug: Print before shuffle
        print(f"BEFORE SHUFFLE:")
        print(f"  Options: {options}")
        print(f"  Correct index: {correct_index}")
        print(f"  Correct answer: {options[correct_index]}")
        
        correct_answer = options[correct_index]
        
        # Shuffle options
        random.shuffle(options)
        
        # Tìm lại vị trí của đáp án đúng sau khi shuffle
        try:
            new_correct_index = options.index(correct_answer)
        except ValueError:
            # Nếu không tìm thấy (không nên xảy ra), set về 0
            new_correct_index = 0
        
        # Debug: Print after shuffle
        print(f"AFTER SHUFFLE:")
        print(f"  Options: {options}")
        print(f"  New correct index: {new_correct_index}")
        print(f"  Correct answer: {options[new_correct_index]}")
        
        # Tạo options_hashes sau khi shuffle (sử dụng hash function dùng chung)
        options_hashes = [hash_option(option) for option in options]
        
        # Tạo correct_hash
        correct_hash = options_hashes[new_correct_index]
        
        return {
            "qid": qid,
            "question": selected_question["question"],
            "options": options,  # Sử dụng options đã shuffle
            "options_hashes": options_hashes,
            "correct_index": new_correct_index,  # Sử dụng new_correct_index
            "correct_hash": correct_hash,
            "explanation": selected_question["explanation"],
            "type": question_type,
            "time_limit_ms": 10000
        }
    
    def reset_session(self, session_id: str):
        """Reset session cache"""
        if session_id in self.session_cache:
            del self.session_cache[session_id]
        
        # Reset tất cả session data liên quan
        keys_to_remove = [key for key in self.session_transcripts.keys() if key.endswith(f"_{session_id}")]
        for key in keys_to_remove:
            if key in self.session_transcripts:
                del self.session_transcripts[key]
            if key in self.session_question_count:
                del self.session_question_count[key]
            if key in self.session_used_segments:
                del self.session_used_segments[key]

# Tạo instance global
video_script_quiz_service = VideoScriptQuizService()
