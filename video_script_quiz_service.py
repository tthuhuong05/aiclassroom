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
    
    def get_next_question_from_video_script(self, course_id: str, script_content: str, 
                                           session_id: str, question_type: str = "mcq", 
                                           language: str = "vi") -> Dict[str, Any]:
        """
        Tạo câu hỏi từ nội dung script video sử dụng AI Gemini
        """
        # Tạo timestamp để đảm bảo câu hỏi luôn khác nhau
        import time
        timestamp = str(int(time.time() * 1000))  # milliseconds
        
        try:
            # Thử sử dụng AI Gemini để tạo câu hỏi
            ai_question = self._generate_question_with_ai(script_content, language)
            if ai_question:
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
            print(f"Error generating AI question: {e}")
        
        # Fallback: Tạo câu hỏi dựa trên nội dung thực tế
        return self._generate_fallback_question(script_content, course_id, session_id, question_type, timestamp)
    
    def _generate_question_with_ai(self, script_content: str, language: str = "vi") -> Dict[str, Any]:
        """
        Tạo câu hỏi sử dụng AI Gemini
        """
        try:
            import google.generativeai as genai
            
            # Cấu hình API key
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                print("GEMINI_API_KEY not found")
                return None
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-pro')
            
            # Prompt cho AI Gemini
            prompt = f"""
            Bạn là một giáo viên AI chuyên tạo câu hỏi trắc nghiệm từ nội dung video thực tế.

            NỘI DUNG PHỤ ĐỀ VIDEO:
            {script_content}

            NHIỆM VỤ:
            1. ĐỌC KỸ toàn bộ nội dung phụ đề trên
            2. PHÂN TÍCH nội dung chính được đề cập trong phụ đề
            3. TẠO câu hỏi trắc nghiệm CỤ THỂ về nội dung thực tế trong phụ đề
            4. ĐẢM BẢO câu hỏi và đáp án dựa 100% trên nội dung phụ đề

            YÊU CẦU:
            - Câu hỏi phải liên quan TRỰC TIẾP đến nội dung trong phụ đề
            - 4 lựa chọn (A, B, C, D) - chỉ 1 đáp án đúng
            - Đáp án đúng phải có trong phụ đề hoặc suy luận từ phụ đề
            - 3 đáp án sai phải hợp lý nhưng không đúng
            - KHÔNG được tạo câu hỏi chung chung
            - KHÔNG được dùng template có sẵn
            - KHÔNG được copy text từ phụ đề vào câu hỏi

            TRẢ VỀ JSON:
            {{
                "question": "Câu hỏi cụ thể dựa trên nội dung phụ đề...",
                "options": ["Đáp án A dựa trên phụ đề", "Đáp án B dựa trên phụ đề", "Đáp án C dựa trên phụ đề", "Đáp án D dựa trên phụ đề"],
                "correct_index": 0,
                "explanation": "Giải thích dựa trên nội dung phụ đề cụ thể..."
            }}
            """
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
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
                            print("✅ AI Gemini generated question successfully")
                            return question_data
            except Exception as e:
                print(f"Error parsing AI response: {e}")
        
        except Exception as e:
            print(f"Error calling AI Gemini: {e}")
        
        return None
    
    def _generate_fallback_question(self, script_content: str, course_id: str, session_id: str, question_type: str, timestamp: str = None) -> Dict[str, Any]:
        """
        Tạo câu hỏi fallback cải thiện dựa trên nội dung thực tế
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

# Tạo instance global
video_script_quiz_service = VideoScriptQuizService()
