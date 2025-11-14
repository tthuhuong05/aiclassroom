import base64
import sys
from services.camera_capture_service import get_camera_capture_service
print(f"[APP_INIT] Python: {sys.executable}")
print(f"[APP_INIT] Version: {sys.version}")

from functools import wraps
from urllib.parse import quote
from flask import (
    Blueprint, Flask, render_template, request, session,
    redirect, url_for, abort, jsonify, current_app
)
import json
import math
import hashlib
import random
import re
import os
import mimetypes
import time, datetime, cv2
# Load biến môi trường từ file .env
try:
    from load_env import load_env_file
    load_env_file()
except Exception:
    def _load_env_file(path=".env"):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s=line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k,v=s.split("=",1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    _load_env_file()
    
from flask import request, jsonify, session, current_app, g

from controller.auth_controller import AuthController
from controller.user_controller import UserController
from controller.course_controller import CourseController
from controller.assignment_controller import AssignmentController
from controller.progress_controller import ProgressController
from services.face_recognition_service import get_face_recognition_service
from ai_gemini import chat_about_transcript


app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_IN_PRODUCTION"
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["EXPLAIN_TEMPLATE_LOADING"] = True
# app.register_blueprint(auto_captions_bp)  # Commented out as the module doesn't exist
print("Jinja search path:", app.jinja_loader.searchpath)

# Import quiz config
try:
    from quiz_config import get_quiz_interval
    QUIZ_INTERVAL_SEC = get_quiz_interval()
except ImportError:
    QUIZ_INTERVAL_SEC = 50

# Controllers
auth_controller = AuthController()
user_controller = UserController()
course_controller = CourseController()
assignment_controller = AssignmentController()
progress_controller = ProgressController()
face_recognition_service = get_face_recognition_service()

# Uploads
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

STORE_DIR = os.path.join(os.getcwd(), "data_quiz")
os.makedirs(STORE_DIR, exist_ok=True)
mimetypes.add_type("text/vtt", ".vtt")

CHEAT_SCREENSHOT_ROOT = os.getenv("CHEAT_SCREENSHOT_ROOT", "cheat_screenshots")

def save_cheat_frame(frame_bgr, user_identifier: str, cheating_reason: str = None) -> str:
    """
    Lưu frame khi phát hiện gian lận vào thư mục theo tên tài khoản + ngày + giờ cụ thể
    Format: cheat_screenshots/username_YYYYMMDD_HHMMSS/filename.jpg
    
    Args:
        frame_bgr: OpenCV image (BGR format)
        user_identifier: username hoặc user_id
        cheating_reason: Lý do gian lận (để thêm vào tên file)
    
    Returns:
        Đường dẫn file đã lưu
    """
    now = datetime.datetime.now()
    # Tạo tên thư mục: username_YYYYMMDD_HHMMSS
    safe_name = "".join(c for c in str(user_identifier) if c.isalnum() or c in ('-', '_')).strip()
    if not safe_name:
        safe_name = "unknown_user"
    
    # Format: username_YYYYMMDD_HHMMSS
    folder_timestamp = now.strftime("%Y%m%d_%H%M%S")
    folder_name = f"{safe_name}_{folder_timestamp}"
    
    # Tạo thư mục
    user_folder = os.path.join(CHEAT_SCREENSHOT_ROOT, folder_name)
    os.makedirs(user_folder, exist_ok=True)
    
    # Tạo tên file với timestamp chi tiết và lý do (nếu có)
    file_timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
    if cheating_reason:
        # Làm sạch lý do để dùng làm tên file
        safe_reason = "".join(c for c in cheating_reason[:30] if c.isalnum() or c in ('-', '_', ' ')).strip().replace(' ', '_')
        filename = f"{file_timestamp}_{safe_reason}.jpg"
    else:
        filename = f"{file_timestamp}.jpg"
    
    path = os.path.join(user_folder, filename)
    cv2.imwrite(path, frame_bgr)
    return path

def _store_path(video_id: str) -> str:
    return os.path.join(STORE_DIR, f"{video_id}.json")

def _load_store(video_id: str) -> dict:
    path = _store_path(video_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_store(video_id: str, data: dict) -> None:
    with open(_store_path(video_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

_QUIZ_STORE = {}

def _key(video_id: str, t_sec: int) -> str:
    return f"{video_id}:{int(t_sec)}"

def _stable_shuffle_50s(item: dict, video_id: str, t_sec: int) -> dict:
    # Deprecated: shuffling only at 50s; better to shuffle on demand for all.
    return item

def _norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    return re.sub(r'\s+', ' ', s)


# ==== HASH HELPERS (đặt ở đầu file app.py, gần _norm_text/_hash_text) ====
def _hash_hmac256_16(text: str) -> str:
    """Hash đúng kiểu CourseController: HMAC-SHA256 + SECRET_KEY, lấy 16 hex."""
    import hmac, hashlib
    try:
        from flask import current_app
        key = (current_app.config.get("SECRET_KEY") or "dev-secret").encode("utf-8")
    except Exception:
        key = b"dev-secret"
    return hmac.new(key, (text or "").encode("utf-8"), hashlib.sha256).hexdigest()[:16]

def _hash_sha1_legacy(text: str) -> str:
    """Hash cũ kiểu SHA1(lowercase, strip) – dùng để tương thích nếu có dữ liệu cũ."""
    import hashlib, re, unicodedata as ud
    norm = (text or "").strip().lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]
def _hash_option(text: str) -> str:
    """
    Hàm băm chuẩn cho mọi nơi trong hệ thống.
    """
    return _hash_hmac256_16(text)

def _option_hashes_both(options: list[str]) -> tuple[list[str], list[str]]:
    """Trả về (hash_hmac, hash_sha1) cho toàn bộ options."""
    opts = list(options or [])
    return ([_hash_hmac256_16(o) for o in opts],
            [_hash_sha1_legacy(o) for o in opts])


def _shuffle_options(item: dict) -> dict:
    """Truly shuffle, update answer_index to match new order."""
    opts = list(item.get("options") or [])
    if not opts:
        return item
    correct_idx = int(item.get("answer_index", 0))
    indexed = list(enumerate(opts))
    random.SystemRandom().shuffle(indexed)
    item["options"] = [t for (_i, t) in indexed]
    try:
        item["answer_index"] = next(
            i for i, (orig_i, _t) in enumerate(indexed) if orig_i == correct_idx
        )
    except StopIteration:
        item["answer_index"] = 0
    return item

def _finalize_hashes(item: dict) -> dict:
    """Add option hashes & correct hash, for safe client-side grading."""
    opts = list(item.get("options") or [])
    item["options_hashes"] = [_hash_text(o) for o in opts]
    ai = int(item.get("answer_index", 0))
    if 0 <= ai < len(opts):
        item["correct_hash"] = item["options_hashes"][ai]
        item["correct_text"] = opts[ai]
    else:
        item["correct_hash"] = _hash_text(opts[0] if opts else "")
        item["correct_text"] = opts[0] if opts else ""
    return item

@app.post("//api/proctor/analyze/ai-quiz/prefill")
def api_ai_quiz_prefill():
    """
    Pre-create the first 50s quiz question for a video from REAL subtitles (or provided text),
    using Gemini with a safe fallback.
    Body JSON: {video_id, duration, caption_path?, caption_url?, subtitle_text?, language?}
    """
    p = request.get_json(force=True) or {}
    video_id   = p.get("video_id") or "no-video-id"
    language   = p.get("language") or "vi"
    # 0–50s đoạn đầu
    start_sec, end_sec = 0, QUIZ_INTERVAL_SEC

    # 1) Lấy phụ đề: ưu tiên subtitle_text do FE gửi; nếu không có thì đọc từ caption_path/url
    subtitle_text = (p.get("subtitle_text") or "").strip()
    caption_p = p.get("caption_path") or (p.get("caption_url") or "").lstrip("/")
    if not subtitle_text and caption_p:
        # đọc toàn bộ file phụ đề (đơn giản); nếu cần chia khoảng thời gian, có thể nâng cấp parser .vtt
        subtitle_text = _read_vtt_as_text(caption_p)

    if not subtitle_text or len(subtitle_text) < 10:
        # vẫn tạo 1 câu hỏi để không vỡ luồng, nhưng log cảnh báo cho dev
        current_app.logger.warning("[prefill] No subtitles provided. Falling back.")
        qa = create_fallback_question_from_subtitles("intro")
    else:
        # 2) Gọi pipeline Gemini-based (có backoff + fallback sẵn)
        qa = generate_question_from_subtitles(
            subtitle_text=subtitle_text,
            time_range=f"{start_sec}-{end_sec} seconds",
            language=language
        )

    # 3) Chuẩn hoá & lưu vào store 50s cho FE hiển thị
    item = {
        "t_sec": end_sec,
        "question": qa["question"],
        "options": qa["options"],
        "answer_index": int(qa.get("correct_index", 0)),
        "explanation": qa.get("explanation", ""),
    }
    item = _shuffle_options(item)
    item = _finalize_hashes(item)
    _QUIZ_STORE[_key(video_id, end_sec)] = item
    return jsonify({"ok": True, "count": 1})


@app.post("/api/ai-quiz/question")
def api_ai_quiz_question():
    """
    TRIỆT ĐỂ: Chỉ dùng Gemini-from-SCRIPT.
    - Ưu tiên script_text từ client; nếu thiếu -> ghép từ caption_url (.vtt)
    - Không fallback transcript/cloze nữa.
    """
    p = request.get_json(force=True) or {}
    video_id   = p.get("video_id") or "no-video-id"
    attempt_id = session.get("user", {}).get("id", "anonymous")
    qtype      = (p.get("type") or "mcq").strip().lower()
    caption_p  = p.get("caption_path")
    caption_u  = p.get("caption_url")
    script_txt = (p.get("script_text") or "").strip()

    # lấy caption path nếu chỉ có URL
    if not caption_p and caption_u:
        caption_p = caption_u.lstrip("/")

    # TUYỆT ĐỐI KHÔNG lấy text từ transcript - Chỉ sử dụng script_text từ client
    if not script_txt:
        return jsonify({"ok": False, "error": "Script content is required. Please provide script_text parameter."}), 400

    # Try to use video_script_quiz_service, fallback if not available
    try:
        from video_script_quiz_service import video_script_quiz_service
        item = video_script_quiz_service.get_next_question_from_video_script(
            course_id=str(video_id),
            script_content=script_txt,
            session_id=str(attempt_id),
            question_type=(qtype if qtype in ("mcq","essay","oral") else "mcq"),
            language="vi"
        )
        return jsonify({"ok": True, "qid": item.get("qid") or hashlib.sha1(item["question"].encode()).hexdigest()[:16], "qa": item})
    except (ImportError, Exception) as e:
        current_app.logger.exception("Video script analysis failed: %s", e)
        # Return a fallback response
        item = {
            "qid": hashlib.sha1(script_txt.encode()).hexdigest()[:16],
            "question": "Câu hỏi về nội dung video",
            "options": ["Lựa chọn A", "Lựa chọn B", "Lựa chọn C", "Lựa chọn D"],
            "correct_index": 0,
            "explanation": "Giải thích dựa trên nội dung video"
        }
        return jsonify({"ok": True, "qid": item["qid"], "qa": item})

@app.post("/api/ai-quiz/grade")
def api_ai_quiz_grade():
    """
    Grade answer: Body JSON {video_id, t_sec, user_answer_index}
    """
    p = request.get_json(force=True) or {}
    video_id = p.get("video_id") or "no-video-id"
    t_sec = int(p.get("t_sec") or 0)
    raw_user_idx = p.get("user_answer_index")
    try:
        user_idx = int(raw_user_idx)
    except Exception:
        user_idx = -1  # invalid
    item = _QUIZ_STORE.get(_key(video_id, t_sec))
    if not item:
        return jsonify({"ok": False, "error": "Không có câu hỏi ở mốc này."}), 404
    correct_index = int(item.get("answer_index", 0))
    correct = (user_idx == correct_index)
    return jsonify({
        "ok": True,
        "correct": correct,
        "correct_index": correct_index,
        "explanation": item.get("explanation") or ""
    })

@app.post("/api/ai-quiz/generate-from-subtitles")
def api_ai_quiz_generate_from_subtitles():
    """
    Tạo câu hỏi từ phụ đề sử dụng AI Gemini
    Body JSON: {subtitle_text, time_range, language}
    """
    try:
        p = request.get_json(force=True) or {}
        subtitle_text = p.get("subtitle_text", "")
        time_range = p.get("time_range", "0-50 seconds")
        language = p.get("language", "vi")
        
        if not subtitle_text or len(subtitle_text.strip()) < 10:
            return jsonify({
                "ok": False, 
                "error": "Không có đủ nội dung phụ đề để tạo câu hỏi"
            }), 400
        
        # Tạo câu hỏi từ phụ đề sử dụng AI Gemini
        question_data = generate_question_from_subtitles(subtitle_text, time_range, language)
        
        return jsonify({
            "ok": True,
            "question": question_data["question"],
            "options": question_data["options"],
            "correct_index": question_data["correct_index"],
            "explanation": question_data["explanation"],
            "type": "mcq"
        })
        
    except Exception as e:
        print(f"❌ Error in generate-from-subtitles: {e}")
        return jsonify({
            "ok": False,
            "error": f"Lỗi khi tạo câu hỏi: {str(e)}"
        }), 500

def generate_question_from_subtitles(subtitle_text, time_range, language="vi"):
    """
    Tạo câu hỏi từ phụ đề sử dụng AI Gemini
    """
    try:
        # Import AI Gemini
        try:
           import google.generativeai as genai  # ✅ SDK đúng
        except Exception as _e:
           genai = None
           print(f"⚠️ Gemini SDK import failed: {_e}")
        
        # Cấu hình API key (cần thêm vào environment variables)
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️ GEMINI_API_KEY not found, using fallback")
            return create_fallback_question_from_subtitles(subtitle_text)
        
        genai.configure(api_key=api_key)
        # Sử dụng model từ environment hoặc fallback (giống ai_gemini.py)
        # Default sử dụng gemini-2.0-flash (model mới nhất có sẵn)
        model_name = os.getenv('GEMINI_MODEL_QA', 'gemini-2.0-flash')
        try:
            model = genai.GenerativeModel(model_name)
            print(f"✅ Using Gemini model: {model_name}")
        except Exception as e:
            print(f"⚠️ Model {model_name} not available: {e}")
            # Thử các model khác theo thứ tự ưu tiên
            fallback_models = [
                'gemini-2.0-flash',      # Model mới nhất
                'gemini-2.0-flash-001',
                'gemini-2.5-flash',      # Theo ai_gemini.py default
                'gemini-1.5-flash-latest',
                'gemini-1.5-pro-latest',
                'gemini-1.5-flash',
                'gemini-1.5-pro'
            ]
            model = None
            for fallback in fallback_models:
                try:
                    print(f"⚠️ Trying fallback model: {fallback}")
                    model = genai.GenerativeModel(fallback)
                    print(f"✅ Using model: {fallback}")
                    break
                except Exception as e2:
                    print(f"⚠️ {fallback} failed: {str(e2)[:100]}")
                    continue
            
            if not model:
                print("❌ No available Gemini model found, using fallback question")
                return create_fallback_question_from_subtitles(subtitle_text)
        
        # Prompt cho AI Gemini - Phân tích phụ đề thực tế
        prompt = f"""
        Bạn là một giáo viên AI chuyên tạo câu hỏi trắc nghiệm từ nội dung video thực tế.

        PHỤ ĐỀ VIDEO THỰC TẾ (đoạn {time_range}):
        {subtitle_text}

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

        TRẢ VỀ JSON:
        {{
            "question": "Câu hỏi cụ thể dựa trên nội dung phụ đề...",
            "options": ["Đáp án A dựa trên phụ đề", "Đáp án B dựa trên phụ đề", "Đáp án C dựa trên phụ đề", "Đáp án D dựa trên phụ đề"],
            "correct_index": 0,
            "explanation": "Giải thích dựa trên nội dung phụ đề cụ thể..."
        }}
        """
        
        # Retry logic với exponential backoff cho rate limiting
        import time
        max_retries = 5
        base_delay = 2  # Bắt đầu với 2 giây
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Parse JSON response
                import json
                try:
                    # Tìm JSON trong response
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
                    print(f"⚠️ Error parsing AI response: {e}")
                
                # Fallback nếu AI response không hợp lệ
                return create_fallback_question_from_subtitles(subtitle_text)
                
            except Exception as e:
                error_str = str(e)
                # Kiểm tra nếu là lỗi rate limiting (429)
                if "429" in error_str or "Resource exhausted" in error_str or "quota" in error_str.lower():
                    if attempt < max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s, 16s, 32s
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ Rate limit hit (429). Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"❌ Max retries reached for rate limiting. Using fallback.")
                        return create_fallback_question_from_subtitles(subtitle_text)
                else:
                    # Lỗi khác, không retry
                    print(f"❌ Error calling AI Gemini: {e}")
                    return create_fallback_question_from_subtitles(subtitle_text)
        
        # Fallback nếu tất cả retries đều fail
        return create_fallback_question_from_subtitles(subtitle_text)
        
    except Exception as e:
        print(f"❌ Error calling AI Gemini: {e}")
        return create_fallback_question_from_subtitles(subtitle_text)

def create_fallback_question_from_subtitles(subtitle_text):
    """
    Tạo câu hỏi fallback từ phụ đề - Cải thiện để dựa trên nội dung thực tế
    """
    # Phân tích nội dung phụ đề đơn giản
    words = subtitle_text.lower().split()
    
    # Tìm từ khóa chính
    keywords = []
    for word in words:
        if len(word) > 3 and word not in ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use']:
            keywords.append(word)
    
    # Tạo câu hỏi dựa trên nội dung thực tế
    if keywords and len(keywords) >= 3:
        # Lấy 3 từ khóa chính
        main_keywords = keywords[:3]
        main_topic = " ".join(main_keywords)
        
        # Tạo câu hỏi cụ thể dựa trên nội dung
        if any(word in subtitle_text.lower() for word in ['variable', 'variables']):
            question = "Trong đoạn video này, nội dung chính nói về gì?"
            options = [
                f"Giới thiệu về {main_topic}",
                "Cách sử dụng biến trong lập trình",
                "Kết luận và tóm tắt",
                "Thực hành và bài tập"
            ]
        elif any(word in subtitle_text.lower() for word in ['function', 'functions']):
            question = "Chủ đề chính của đoạn video này là gì?"
            options = [
                f"Giải thích về {main_topic}",
                "Cách tạo và sử dụng hàm",
                "Kết luận và tóm tắt",
                "Thực hành và bài tập"
            ]
        elif any(word in subtitle_text.lower() for word in ['class', 'classes', 'object', 'objects']):
            question = "Nội dung video tập trung vào chủ đề gì?"
            options = [
                f"Hướng dẫn về {main_topic}",
                "Lập trình hướng đối tượng",
                "Kết luận và tóm tắt",
                "Thực hành và bài tập"
            ]
        else:
            # Tạo câu hỏi chung dựa trên từ khóa
            question = f"Đoạn video này chủ yếu nói về {main_topic} - đúng hay sai?"
            options = [
                "Đúng - đây là chủ đề chính",
                "Sai - chủ đề khác",
                "Chưa rõ - cần xem thêm",
                "Có thể - cần xác nhận"
            ]
    else:
        # Fallback cuối cùng
        question = "Trong đoạn video này, nội dung chính nói về gì?"
        options = [
            "Giới thiệu tổng quan về chủ đề",
            "Kết luận và tóm tắt", 
            "Thảo luận chi tiết",
            "Thực hành và bài tập"
        ]
    
    return {
        "question": question,
        "options": options,
        "correct_index": 0,
        "explanation": "Dựa trên nội dung phụ đề, đây là phần giới thiệu tổng quan về chủ đề."
    }


def _gemini_model_candidates():
    """
    Danh sách model Gemini hợp lệ, tự sửa lại các alias cũ (gemini-flash, models/gemini-flash, gemini-pro...).
    Dùng chung cho mọi chỗ gọi Gemini để tránh 404.
    """
    import os as _os
    raw = (_os.getenv("GEMINI_MODEL_QA") or "gemini-2.0-flash").strip()
    # Nếu người dùng copy nguyên "models/xxx" từ REST API thì bỏ prefix đi
    if raw.startswith("models/"):
        raw = raw.split("/", 1)[1]

    # Map các tên cũ sang model mới
    bad_aliases = {
        "gemini-flash",
        "gemini-pro",
    }
    if raw in bad_aliases:
        raw = "gemini-2.0-flash"

    return [
        raw,
        "gemini-2.0-flash-001",
        "gemini-2.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]


# --- AI-safe explanation helper ---
def safe_generate_explanation(question_text, options, correct_index, user_index):
    """
    Luôn trả về chuỗi giải thích. Nếu AI không khả dụng, sinh fallback có nghĩa.
    """
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("No API key")
        genai.configure(api_key=api_key)
        # Ưu tiên tên mới; nếu lỗi sẽ thử dần
        for name in [os.getenv("GEMINI_MODEL_QA", "gemini-2.0-flash"),
                     "gemini-2.0-flash-001",
                     "gemini-2.5-flash",
                     "gemini-1.5-flash-latest",
                     "gemini-1.5-pro-latest"]:
            try:
                model = genai.GenerativeModel(name)
                prompt = f"""
Bạn là trợ giảng. Câu hỏi: {question_text}
Các lựa chọn: {options}
Đáp án đúng: {options[correct_index]}
Đáp án học viên: {(options[user_index] if isinstance(user_index,int) and 0<=user_index<len(options) else "—")}
Giải thích ngắn gọn, chỉ dựa trên dữ kiện trong câu & kiến thức nền tảng, tránh lan man.
"""
                resp = model.generate_content(prompt)
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                continue
        # nếu tất cả model fail -> fallback
        raise RuntimeError("All models failed")
    except Exception:
        correct = options[correct_index] if options and 0 <= correct_index < len(options) else "—"
        chosen  = options[user_index] if options and isinstance(user_index,int) and 0 <= user_index < len(options) else "—"
        base = f"Đáp án đúng là: {correct}."
        if chosen != "—" and chosen != correct:
            base += f" Bạn chọn: {chosen}. So sánh nội dung/định nghĩa cho thấy {correct} khớp yêu cầu của câu hỏi hơn."
        else:
            base += " Lý do: đáp án này thỏa điều kiện của câu hỏi theo khái niệm/định nghĩa chuẩn."
        return base

# --- TEACHER REPORT (Gemini + fallback) ---
def _fetch_courses_catalog() -> list[dict]:
    """
    Cố gắng lấy danh mục khóa học dưới dạng list[dict] {id,title,category,tags,...}
    Ưu tiên qua controller/model; luôn trả list (có thể rỗng) – không raise.
    """
    catalog = []
    # 1) thử các hàm thường gặp ở CourseController
    try:
        names = ["get_all_courses", "list_courses", "get_courses", "all", "fetch_all"]
        for name in names:
            fn = getattr(course_controller, name, None)
            if callable(fn):
                data = fn()
                if isinstance(data, list):
                    catalog = data
                    break
                if isinstance(data, dict) and "courses" in data:
                    catalog = data["courses"]
                    break
    except Exception:
        pass

    # 2) fallback sang CourseModel nếu có
    if not catalog:
        try:
            cm = course_controller.course_model
            for name in ["get_all_courses", "list_courses", "all", "fetch_all"]:
                fn = getattr(cm, name, None)
                if callable(fn):
                    data = fn()
                    if isinstance(data, list):
                        catalog = data
                        break
        except Exception:
            pass

    # Chuẩn hoá về dict mỏng
    out = []
    for c in catalog or []:
        if isinstance(c, dict):
            out.append({
                "id": c.get("id"),
                "title": c.get("title") or c.get("name") or "",
                "category": c.get("category") or "",
                "tags": c.get("tags") or "",
                "level": (c.get("level") or "").lower(),
                "description": c.get("description") or "",
            })
        else:
            # object-like
            out.append({
                "id": getattr(c, "id", None),
                "title": getattr(c, "title", "") or getattr(c, "name", ""),
                "category": getattr(c, "category", ""),
                "tags": getattr(c, "tags", ""),
                "level": (getattr(c, "level", "") or "").lower(),
                "description": getattr(c, "description", ""),
            })
    return out
def _extract_error_topics(detailed: list[dict]) -> dict:
    """
    Đếm lỗi theo chủ đề từ text câu hỏi.
    """
    kw_map = {
        # nền tảng
        "biến": "Biến & Kiểu dữ liệu", "kiểu dữ liệu": "Biến & Kiểu dữ liệu",
        "variable": "Biến & Kiểu dữ liệu", "variables": "Biến & Kiểu dữ liệu",
        "string": "Chuỗi", "char": "Chuỗi",
        "array": "Mảng", "mảng": "Mảng", "list": "Mảng",
        # điều khiển
        "vòng lặp": "Vòng lặp", "for": "Vòng lặp", "while": "Vòng lặp",
        "điều kiện": "Câu lệnh điều kiện", "if": "Câu lệnh điều kiện", "switch": "Câu lệnh điều kiện",
        # hàm / OOP
        "hàm": "Hàm/Method", "method": "Hàm/Method", "function": "Hàm/Method",
        "class": "OOP cơ bản", "object": "OOP cơ bản",
        "kế thừa": "Kế thừa (OOP)", "đa hình": "Đa hình (OOP)", "encapsulation": "Đóng gói (OOP)"
    }
    topics = {}
    for d in detailed or []:
        q = (d.get("question") or d.get("question_text") or "").lower()
        wrong = int(d.get("user_answer_index", -1)) != int(d.get("correct_index", -1))
        for k, canon in kw_map.items():
            if k in q:
                t = topics.setdefault(canon, {"wrong": 0, "total": 0})
                t["total"] += 1
                if wrong:
                    t["wrong"] += 1
    return topics


def _heuristic_teacher_report(results: dict, catalog: list[dict]) -> dict:
    detailed = results.get("detailed_results") or results.get("details") or []
    total = int(results.get("total") or len(detailed) or 0)
    correct = int(results.get("correct") or sum(
        1 for d in detailed
        if int(d.get("user_answer_index", -1)) == int(d.get("correct_index", -1))
    ))
    score = float(results.get("score") or (correct * 100.0 / total if total else 0.0))

    # --- trích chủ đề lỗi
    topics = _extract_error_topics(detailed)
    topic_stat = []
    for name, st in topics.items():
        r = st["wrong"] / st["total"] if st["total"] else 0.0
        topic_stat.append((name, st["wrong"], st["total"], r))
    topic_stat.sort(key=lambda x: (-x[1], -x[3], -x[2]))
    weak_topics = [n for (n,w,t,r) in topic_stat if t >= 1][:3]

    # --- trình độ theo điểm
    level_hint = "advanced" if score >= 80 else ("intermediate" if score >= 50 else "beginner")

    # map chủ đề → keyword để so khớp catalog
    topic2kw = {
        "Biến & Kiểu dữ liệu": ["variable", "type", "kiểu dữ liệu", "biến"],
        "Chuỗi": ["string", "chuỗi"],
        "Mảng": ["array", "list", "mảng"],
        "Câu lệnh điều kiện": ["if", "else", "switch", "điều kiện"],
        "Vòng lặp": ["for", "while", "loop", "vòng lặp"],
        "Hàm/Method": ["function", "method", "hàm"],
        "OOP cơ bản": ["class", "object", "oop"],
        "Kế thừa (OOP)": ["inheritance", "kế thừa"],
        "Đa hình (OOP)": ["polymorphism", "đa hình"],
        "Đóng gói (OOP)": ["encapsulation", "đóng gói"],
    }
    kws = []
    for t in weak_topics:
        kws += topic2kw.get(t, [])
    kws = kws[:6]

    def _match_courses(topic_keywords: list[str], by_level: str, limit=4):
        picks = []
        for c in catalog or []:
            text = f"{(c.get('title') or '')} {(c.get('tags') or '')} {(c.get('category') or '')}".lower()
            lvl  = (c.get("level") or "").lower()
            hit_topic = any(k.lower() in text for k in topic_keywords)
            hit_level = (lvl == by_level.lower()) if by_level else False
            if hit_topic or hit_level:
                picks.append({
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "level": c.get("level"),
                    "thumbnail": c.get("thumbnail"),
                    "reason": ("Phù hợp chủ đề yếu" if hit_topic else f"Phù hợp trình độ {by_level}.")
                })
            if len(picks) >= limit:
                break
        return picks

    rec_courses = _match_courses(kws, level_hint, limit=4)

    strengths = f"Điểm: {score:.1f}/100 – đúng {correct}/{total} câu."
    weaknesses = ("Cần củng cố: " + ", ".join(weak_topics)) if weak_topics else "Cần luyện thêm các câu áp dụng."
    plan_text = (
        "Nên học lại từ nhập môn theo lộ trình ngắn, có bài tập minh họa mỗi chủ đề."
        if level_hint == "beginner" else
        ("Củng cố khái niệm và luyện áp dụng theo tình huống."
         if level_hint == "intermediate" else
         "Tiếp tục luyện đề phân hoá và mini-project.")
    )

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": {
            "level_hint": level_hint,
            "text": plan_text,
            "courses": rec_courses
        },
        "source": "heuristic"
    }


def build_teacher_report(results: dict, courses_catalog: list[dict]) -> dict:
    """
    Gọi Gemini (nếu có) để viết nhận xét chi tiết như giáo viên.
    Nếu lỗi (API / SDK / mạng / model), luôn fallback về _heuristic_teacher_report.
    """
    import os, json

    # Bước 0: luôn dựng sẵn bản heuristic để làm nền & fallback
    base = _heuristic_teacher_report(results, courses_catalog) or {}
    if "recommendations" not in base or not isinstance(base["recommendations"], dict):
        base["recommendations"] = {"text": "", "courses": []}
    base_recos = base["recommendations"]
    rec_courses = base_recos.get("courses") or []

    # Nếu không có API key → trả luôn bản heuristic
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        base["source"] = "heuristic_no_key"
        return base

    # Thử import SDK (thư viện mới google-generativeai)
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"[build_teacher_report] Gemini SDK init error: {e}")
        base["source"] = "heuristic_no_sdk"
        return base

    # Chuẩn bị dữ liệu tóm tắt cho prompt
    detailed = results.get("detailed_results") or results.get("details") or []
    wrong_qs = []
    for d in detailed:
        try:
            cidx = int(d.get("correct_index", 0) or 0)
            uidx = int(d.get("user_answer_index", -1) or -1)
        except Exception:
            cidx = int(d.get("correct_index") or 0)
            uidx = int(d.get("user_answer_index") or -1)

        if uidx == cidx:
            continue  # chỉ lấy câu sai để phân tích điểm yếu
        q_text = (d.get("question") or d.get("question_text") or "")[:220]
        opts = d.get("options") or []
        wrong_qs.append({
            "question": q_text,
            "correct": opts[cidx] if 0 <= cidx < len(opts) else "",
            "chosen": opts[uidx] if 0 <= uidx < len(opts) else "",
        })
        if len(wrong_qs) >= 10:
            break

    # Tóm tắt khóa học đã được hệ thống lọc sẵn (để AI chỉ giải thích chứ không tự bịa khoá mới)
    course_brief = [{
        "title": c.get("title"),
        "level": c.get("level"),
        "reason": c.get("reason")
    } for c in rec_courses]

    score = results.get("score")
    correct = results.get("correct")
    total = results.get("total")

    prompt = f"""
Bạn là giáo viên lập trình, đang viết phiếu nhận xét cho học viên sau bài kiểm tra trắc nghiệm.

Thông tin tổng quan:
- Điểm số: {score}/100
- Số câu đúng/số câu: {correct}/{total}

Một số câu làm sai (tối đa 10):
{json.dumps(wrong_qs, ensure_ascii=False, indent=2)}

Các khóa học hệ thống đang đề xuất sẵn:
{json.dumps(course_brief, ensure_ascii=False, indent=2)}

Nhiệm vụ:
1. Phân tích chi tiết ĐIỂM MẠNH: học viên đang làm tốt ở dạng câu nào, khái niệm nào, cách suy luận ra sao.
2. Phân tích chi tiết ĐIỂM YẾU: hay nhầm ở loại câu nào, khái niệm nào, sai vì thiếu kiến thức hay thiếu cẩn thận, ví dụ cụ thể.
3. Viết KẾ HOẠCH ÔN TẬP / LỘ TRÌNH học trong 1–2 tuần tới (3–5 gạch đầu dòng, có thể hành động ngay).
4. Dựa trên danh sách khóa học ở trên, giải thích ngắn gọn vì sao NHỮNG KHÓA HỌC ĐÓ phù hợp với trình độ hiện tại (không cần nghĩ thêm khoá mới).

TRẢ VỀ ĐÚNG ĐỊNH DẠNG SAU (không thêm ký hiệu khác, không dùng markdown, không có JSON):

[STRENGTHS]
(nội dung 3–6 câu, tiếng Việt, xưng hô "bạn")

[WEAKNESSES]
(nội dung 3–6 câu, tiếng Việt, nêu rõ lỗi điển hình)

[PLAN]
(nội dung 3–6 câu hoặc 3–5 gạch đầu dòng, tiếng Việt)
"""

    model_names = _gemini_model_candidates()

    def _extract_section(raw: str, tag: str) -> str:
        start = raw.find(f"[{tag}]")
        if start == -1:
            return ""
        start += len(tag) + 2  # qua dấu ]
        end = len(raw)
        for other in ["STRENGTHS", "WEAKNESSES", "PLAN"]:
            if other == tag:
                continue
            pos = raw.find(f"[{other}]", start)
            if pos != -1 and pos < end:
                end = pos
        return raw[start:end].strip()

    for name in model_names:
        try:
            model = genai.GenerativeModel(name)
            resp = model.generate_content(prompt)
            raw = (getattr(resp, "text", None) or "").strip()
            if not raw:
                continue

            s_txt = _extract_section(raw, "STRENGTHS")
            w_txt = _extract_section(raw, "WEAKNESSES")
            p_txt = _extract_section(raw, "PLAN")

            if not (s_txt or w_txt or p_txt):
                # không parse được → thử model khác
                continue

            merged = {
                "strengths": s_txt or base.get("strengths"),
                "weaknesses": w_txt or base.get("weaknesses"),
                "recommendations": {
                    "text": p_txt or base_recos.get("text"),
                    "courses": rec_courses,
                },
                "source": f"gemini_{name}",
            }
            return merged
        except Exception as e:
            print(f"[build_teacher_report] model {name} error: {e}")
            continue

    # Nếu tất cả model đều lỗi → quay lại heuristic
    base["source"] = "heuristic_error"
    return base

# --- AI-safe DETAILED explanation helper (returns HTML) ---
def detailed_explain_html(question_text: str, options: list, correct_index: int, user_index: int):
    """
    Trả về HTML giải thích chi tiết. Không ném lỗi dù AI hỏng.
    """
    def _fallback_html():
        correct = options[correct_index] if 0 <= correct_index < len(options) else "—"
        chosen  = options[user_index] if isinstance(user_index, int) and 0 <= user_index < len(options) else "—"
        bullets = []
        for i, opt in enumerate(options or []):
            tag = "ĐÚNG" if i == correct_index else ("BẠN CHỌN" if i == user_index else "SAI")
            reason = "Khớp định nghĩa/điều kiện nêu trong câu hỏi." if i == correct_index else \
                     ("Không thỏa điều kiện cốt lõi/mấu chốt sai." if i == user_index else "Chưa thỏa điều kiện hoặc chỉ đúng một phần.")
            bullets.append(f"<li><strong>{chr(65+i)}. {opt}</strong> — <em>{tag}</em>: {reason}</li>")
        return f"""
        <div>
          <p><strong>Tóm tắt:</strong> Bạn chọn <code>{chosen}</code>; đáp án đúng là <code>{correct}</code>.</p>
          <h6 class="mt-2">Vì sao đáp án đúng?</h6>
          <p>Đáp án đúng thỏa điều kiện của câu hỏi theo khái niệm chuẩn; các lựa chọn khác vi phạm ít nhất một tiêu chí.</p>
          <h6 class="mt-2">Đối chiếu từng phương án</h6>
          <ul>{''.join(bullets)}</ul>
          <h6 class="mt-2">Mẹo ghi nhớ</h6>
          <p>Đọc kỹ từ khóa chính (điều kiện, phạm vi áp dụng, ngoại lệ). Loại nhanh các lựa chọn trái định nghĩa.</p>
        </div>
        """

    # cố gắng dùng Gemini trước
    try:
        import google.generativeai as genai
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("No API key")
        genai.configure(api_key=api_key)

    # Danh sách model hợp lệ; lấy từ helper chung (có sửa alias cũ)
        model_names = _gemini_model_candidates()


        prompt = f"""
Bạn là trợ giảng lập trình. Hãy GIẢI THÍCH CHI TIẾT cho câu trắc nghiệm dưới dạng HTML (chỉ thẻ cơ bản: p, h6, ul, li, code, strong, em; không dùng script/css).
Yêu cầu cấu trúc:
1) <p><strong>Tóm tắt:</strong> ...</p>
2) <h6>Khái niệm chính</h6><p>...</p>
3) <h6>Vì sao đáp án đúng?</h6><p>...</p>
4) <h6>Đối chiếu từng phương án</h6><ul><li>...</li>...</ul> (nêu rõ A/B/C/D đúng-sai và vì sao)
5) <h6>Mẹo ghi nhớ</h6><p>...</p>

Câu hỏi: {question_text}
Các lựa chọn: {options}
Đáp án đúng: {options[correct_index] if 0 <= correct_index < len(options) else "—"}
Đáp án học viên: {(options[user_index] if isinstance(user_index,int) and 0<=user_index<len(options) else "—")}
Giải thích dựa trên kiến thức chuẩn; súc tích, không lan man, không thêm thẻ lạ.
"""

        for name in model_names:
            try:
                html = genai.GenerativeModel(name).generate_content(prompt).text or ""
                html = html.strip()
                if html:
                    return html
            except Exception:
                continue
        return _fallback_html()
    except Exception:
        return _fallback_html()


# ---- Template globals ----
@app.context_processor
def inject_user():
    username = session.get('username')
    role = session.get('role')
    user = None
    
    if username:
        from model.user_model import UserModel
        user_model = UserModel()
        user_row = user_model.find_user_by_username(username)
        if user_row:
            # Convert sqlite3.Row to dict
            user = dict(user_row)
            # Tạo avatar_url từ avatar_path
            avatar_path = user.get("avatar_path")
            if avatar_path:
                user["avatar_url"] = f"/static/{avatar_path}"
            else:
                user["avatar_url"] = None
    
    return {
        'username': username,
        'role': role,
        'user': user,
        'is_teacher': role == 'teacher'
    }

# ---- Guards ----
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            next_url = request.full_path or request.path
            if next_url.endswith('?'):
                next_url = next_url[:-1]
            return redirect(url_for("login", next=quote(next_url, safe=":/?&=")))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "teacher":
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ---- Home ----
@app.route("/")
def home():
    return auth_controller.home()

# ---- Auth ----
@app.route("/login", methods=["GET", "POST"])
def login():
    return auth_controller.login()

@app.route("/register", methods=["GET", "POST"])
def register():
    return auth_controller.register()

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        return 'Email reset đã được gửi!'
    return render_template('auth/forgot_password.html')

@app.route("/logout")
def logout():
    return auth_controller.logout()

# ---- Course (list/search/detail/CRUD) ----
@app.route("/course")
@login_required
def course():
    from flask import Response
    q = (request.args.get("q") or "").strip().lower()
    cat = (request.args.get("category") or "").strip().lower()
    try:
        resp = course_controller.list_courses()
        if isinstance(resp, (str, Response)):
            return resp
    except Exception as e:
        print(f"[course] list_courses passthrough failed: {e}")

    def _norm(s): return (s or "").lower()
    get_all_names = ["get_all_courses", "list_courses", "get_courses", "all", "fetch_all"]
    courses = []
    for name in get_all_names:
        fn = getattr(course_controller, name, None)
        if callable(fn):
            try:
                data = fn()
                if isinstance(data, list):
                    courses = data
                elif isinstance(data, dict) and "courses" in data:
                    courses = data["courses"]
                break
            except Exception as e:
                print(f"[course] try {name} failed: {e}")

    filtered = []
    for c in courses or []:
        title = _norm(c.get("title") if isinstance(c, dict) else getattr(c, "title", ""))
        ccat = _norm(c.get("category") if isinstance(c, dict) else getattr(c, "category", ""))
        if (not q or q in title) and (not cat or cat == ccat):
            filtered.append({
                "id": c.get("id") if isinstance(c, dict) else getattr(c, "id", None),
                "title": title and (c.get("title") if isinstance(c, dict) else getattr(c, "title", "")),
                "description": (c.get("description") if isinstance(c, dict) else getattr(c, "description", "")) or "",
                "category": (c.get("category") if isinstance(c, dict) else getattr(c, "category", "")) or "",
                "image_url": (c.get("image_url") if isinstance(c, dict) else getattr(c, "image_url", "")) or (c.get("image") if isinstance(c, dict) else getattr(c, "image", "")) or "",
                "tags": (c.get("tags") if isinstance(c, dict) else getattr(c, "tags", "")) or "",
            })

    return render_template("course_list_search.html", courses=filtered)

@app.route("/course/<int:course_id>")
def course_detail(course_id):
    return course_controller.course_detail(course_id)

@app.route("/manage-courses")
@admin_required
def manage_courses():
    return course_controller.manage_courses()

@app.route("/create-course", methods=["GET", "POST"])
@admin_required
def create_course():
    return course_controller.create_course()

@app.route("/edit-course/<int:course_id>", methods=["GET", "POST"])
@admin_required
def edit_course(course_id):
    return course_controller.edit_course(course_id)

@app.route("/update-course/<int:course_id>", methods=["POST"])
@admin_required
def update_course(course_id):
    return course_controller.edit_course(course_id)

@app.route("/delete-course/<int:course_id>")
@admin_required
def delete_course(course_id):
    return course_controller.delete_course(course_id)

# ---- Assignment / Exam ----
@app.route("/create_questions/<int:course_id>")
@admin_required
def create_questions(course_id):
    return assignment_controller.create_questions_for_course(course_id, "Bài học về AI cơ bản", "beginner")

@app.route("/submit_exam/<int:course_id>", methods=["POST"])
@login_required
def submit_exam(course_id):
    return assignment_controller.submit_exam(course_id)

@app.route("/history")
@login_required
def history():
    return assignment_controller.view_history()

@app.route("/generate_ai_questions/<int:course_id>")
@admin_required
def generate_ai_questions(course_id):
    return assignment_controller.generate_questions_from_video(course_id)

# ---- Users (admin) ----
@app.route("/users")
@admin_required
def list_users():
    return user_controller.list_users()

@app.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        return user_controller.store_user()
    return render_template('create_user.html')

@app.route("/users/store", methods=["POST"])
@admin_required
def store_user():
    return user_controller.store_user()

@app.route("/users/edit/<int:user_id>", methods=["GET"])
@admin_required
def edit_user_form(user_id):
    return user_controller.edit_user_form(user_id)

@app.route("/users/update/<int:user_id>", methods=["POST"])
@admin_required
def update_user(user_id):
    return user_controller.update_user(user_id)

@app.route("/users/delete/<int:user_id>")
@admin_required
def delete_user(user_id):
    return user_controller.delete_user(user_id)

@app.post("/admin/caption/<int:course_id>/generate")
def generate_caption(course_id):
    return course_controller.generate_caption(course_id, lang=request.args.get("lang","en"))

@app.get("/api/course/<int:course_id>/outline")
@login_required
def api_outline(course_id):
    return jsonify({
        "ok": True,
        "sections": progress_controller.get_outline(course_id),
        "progress": progress_controller.get_user_progress(
            course_id, session.get("user", {}).get("id"))
    })

@app.post("/api/progress/upsert")
@login_required
def api_progress_upsert():
    return progress_controller.upsert()

@app.route("/exam/<int:course_id>")
@login_required
def exam(course_id):
    return course_controller.exam(course_id)


# --- BEGIN: Gemini bulk questions from transcript ---
import json, os, re, random
from collections import defaultdict

def _read_vtt_as_text(vtt_path: str) -> str:
    """Chuyển .vtt/.srt đơn giản -> plain text."""
    if not vtt_path or not os.path.exists(vtt_path):
        return ""
    txt = []
    with open(vtt_path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            if re.search(r"\d{2}:\d{2}:\d{2}\.\d{3}", ln):  # bỏ timestamp
                continue
            if ln.strip().isdigit():  # bỏ số thứ tự
                continue
            ln = ln.strip()
            if ln:
                txt.append(ln)
    return re.sub(r"\s+", " ", " ".join(txt)).strip()

def _gemini_generate_mcqs(transcript_text: str, n: int = 20, language: str = "vi"):
    """
    Trả về list[dict]: 
      {level: beginner|intermediate|advanced, 
       question: str, options: [A,B,C,D], answer: 'A'..'D', explanation: str}
    """
    # Nếu chưa có API key -> fallback rules-based để không chặn luồng
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Fallback rất đơn giản để chạy được demo
        qs = []
        for i in range(n):
            opts = [f"Phương án {k}" for k in ["A","B","C","D"]]
            qs.append({
                "level": random.choice(["beginner","intermediate","advanced"]),
                "question": f"Câu hỏi #{i+1} theo nội dung transcript (demo).",
                "options": opts,
                "answer": "A",
                "explanation": "Giải thích (demo) dựa trên phần transcript tương ứng."
            })
        return qs

    import google.generativeai as genai
    genai.configure(api_key=api_key)

    # Ưu tiên model trong ENV, fallback an toàn
    model_name = os.getenv("GEMINI_MODEL_QA", "gemini-2.0-flash")
    try:
        model = genai.GenerativeModel(model_name)
    except Exception:
        for fb in ["gemini-2.5-flash","gemini-1.5-pro-latest","gemini-1.5-flash"]:
            try:
                model = genai.GenerativeModel(fb)
                break
            except Exception:
                model = None
        if model is None:
            raise RuntimeError("Không khởi tạo được Gemini model")

    sys_prompt = f"""
Bạn là trợ giảng AI. Hãy đọc kĩ TRANSCRIPT và tạo {n} câu hỏi trắc nghiệm 4 lựa chọn (A–D) 
bám SÁT nội dung, phân bố mức độ: 40% beginner, 40% intermediate, 20% advanced.
Mỗi mục JSON phải có:
- level: 'beginner' | 'intermediate' | 'advanced'
- question: string (ngắn gọn, rõ ý, đúng nội dung transcript)
- options: array 4 phần tử (mỗi phần tử là string)
- answer: 'A' | 'B' | 'C' | 'D' (chỉ 1 đáp án đúng)
- explanation: string (giải thích tại sao đúng, tham chiếu ý trong transcript)
TRẢ VỀ JSON DUY NHẤT: list các object như trên, KHÔNG văn bản rời.
NGÔN NGỮ: {language}.
TRANSCRIPT:
\"\"\"{transcript_text[:120000]}\"\"\"
"""

    resp = model.generate_content(sys_prompt)
    raw = resp.text if hasattr(resp, "text") else (resp.candidates[0].content.parts[0].text)
    # Chuẩn hoá JSON
    raw = raw.strip()
    raw = raw[raw.find("[") : raw.rfind("]")+1]  # cắt lấy đoạn list
    data = json.loads(raw)

    # Hậu kiểm, chuẩn hoá keys
    out = []
    for item in data:
        opts = item.get("options") or []
        if isinstance(opts, dict):  # A/B/C/D -> list
            opts = [opts.get(k,"") for k in ["A","B","C","D"]]
        if len(opts) != 4:
            continue
        ans = item.get("answer","A").strip().upper()[:1]
        if ans not in ("A","B","C","D"):
            ans = "A"
        lvl = (item.get("level","beginner") or "beginner").lower()
        if lvl.startswith("easy"): lvl = "beginner"
        if lvl.startswith("medium"): lvl = "intermediate"
        if lvl.startswith("hard"): lvl = "advanced"
        out.append({
            "level": lvl,
            "question": item.get("question","").strip(),
            "options": [str(o).strip() for o in opts],
            "answer": ans,
            "explanation": item.get("explanation","").strip()
        })
    return out

@app.post("/api/ai-quiz/bulk-from-transcript")
def api_ai_quiz_bulk_from_transcript():
    """
    Body JSON:
      {
        "course_id": 123,
        "transcript_text": "...",        # ưu tiên
        "caption_path": "static/uploads/xxx.vtt",  # hoặc
        "caption_url": "/static/uploads/xxx.vtt",
        "n": 20,
        "language": "vi"
      }
    """
    p = request.get_json(force=True) or {}
    course_id = int(p.get("course_id") or 0)
    if course_id <= 0:
        return jsonify({"ok": False, "error": "Thiếu course_id"}), 400

    transcript = (p.get("transcript_text") or "").strip()
    cap_path = p.get("caption_path") or ""
    cap_url  = p.get("caption_url") or ""
    if not transcript and cap_url and not cap_path:
        cap_path = cap_url.lstrip("/")
    if not transcript and cap_path:
        transcript = _read_vtt_as_text(cap_path)

    if not transcript or len(transcript) < 50:
        return jsonify({"ok": False, "error": "Transcript chưa đủ nội dung."}), 400

    n = int(p.get("n") or 20)
    language = p.get("language") or "vi"

    # 1) Gọi Gemini sinh câu hỏi
    try:
        qa_list = _gemini_generate_mcqs(transcript, n=n, language=language)
    except Exception as e:
        current_app.logger.exception("Gemini bulk failed: %s", e)
        return jsonify({"ok": False, "error": f"Lỗi Gemini: {e}"}), 500

    # 2) Gom theo level -> lưu DB qua AssignmentModel.insert_questions (giữ nguyên API cũ)
    level_map = defaultdict(list)
    for q in qa_list:
        level_map[q["level"]].append({
            "question": q["question"],
            "options": q["options"],
            "answer": q["answer"]  # A/B/C/D
        })

    am = assignment_controller.model
    total_inserted = 0
    for lvl, bucket in level_map.items():
        if not bucket: 
            continue
        am.insert_questions(course_id, lvl, bucket)
        total_inserted += len(bucket)

    return jsonify({"ok": True, "created": total_inserted, "levels": {k: len(v) for k,v in level_map.items()}})
# --- END: Gemini bulk questions from transcript ---

@app.post("/api/ai/video-chat")
@login_required
def api_ai_video_chat():
    """
    Chat trợ giảng AI dựa trên nội dung bài học.
    - Nếu câu hỏi thuộc phạm vi bài học -> AI trả lời (có thể dùng kiến thức ngoài transcript).
    - Nếu câu hỏi ngoài lề -> blocked = True.
    """
    try:
        payload = request.get_json(force=True) or {}
    except Exception:
        payload = {}

    course_id = int(payload.get("course_id") or 0)
    question = (payload.get("question") or "").strip()
    history  = payload.get("history") or []

    if course_id <= 0 or not question:
        return jsonify({"ok": False, "error": "Thiếu course_id hoặc question"}), 400

    # 1) Lấy đường dẫn transcript/caption cho khóa học
    try:
        cap_path = course_controller.course_model.get_caption_path(course_id)
    except Exception as e:
        current_app.logger.exception("get_caption_path failed: %s", e)
        cap_path = ""

    if not cap_path:
        return jsonify({"ok": False, "error": "Không tìm thấy transcript cho khóa học"}), 400

    # 2) Đọc transcript từ file .vtt/.srt
    transcript = _read_vtt_as_text(cap_path)
    if not transcript:
        return jsonify({"ok": False, "error": "Không đọc được transcript từ caption"}), 400

    # 3) Heuristic chặn sớm các câu hỏi rõ ràng ngoài lề
    q_norm = re.sub(r"\s+", " ", question.lower())
    obvious_off_topics = [
        "thời tiết", "thoi tiet",
        "trúng số", "trung so",
        "bóng đá", "bong da",
        "chứng khoán", "chung khoan",
        "crush", "tán gái", "tan gai",
        "ăn gì", "an gi",
        "chơi game", "choi game",
    ]
    if any(k in q_norm for k in obvious_off_topics):
        return jsonify({
            "ok": True,
            "blocked": True,
            "answer": None,
            "reason": "unrelated_or_out_of_scope"
        })

    # 4) Gọi Gemini để quyết định trong/ngoài phạm vi bài học
    result = chat_about_transcript(transcript, question, history)
    if not result:
        return jsonify({"ok": False, "error": "Gemini không phản hồi"}), 500

    related = bool(result.get("related"))
    answer = (result.get("answer") or "").strip()

    if not related or not answer:
        # Câu hỏi ngoài phạm vi bài học
        return jsonify({
            "ok": True,
            "blocked": True,
            "answer": None,
            "reason": "unrelated_or_out_of_scope"
        })

    return jsonify({
        "ok": True,
        "blocked": False,
        "answer": answer
    })


# --- thay toàn bộ route này ---
@app.post("/api/exam/start")
@login_required
def api_exam_start():
    import time
    # Ghi nhận mốc bắt đầu và reset bộ đếm server-side
    session["proctor_started_at"] = time.time()
    session["no_face_frames"] = 0
    session["server_armed_since"] = None
    session["server_susp_votes"] = 0
    session["last_proctor"] = None
    return course_controller.api_exam_start()

@app.post("/api/exam/next")
@login_required
def api_exam_next():
    return course_controller.api_exam_next()

@app.post("/api/exam/submit")
@login_required
def api_exam_submit():
    return course_controller.api_exam_submit()

@app.post("/api/exam/event")
@login_required
def api_exam_event():
    return course_controller.api_exam_event()

@app.post("/api/exam/status")
@login_required
def api_exam_status():
    return course_controller.api_exam_status()

@app.post("/api/exam/finish")
@login_required
def api_exam_finish():
    return course_controller.api_exam_finish()


@app.get("/api/proctor/status")
@login_required
def api_proctor_status():
    svc = face_recognition_service
    return jsonify({
        "ok": True,
        "available": svc.is_available(),
        "status": svc.debug_status()
    })

@app.get("/api/proctor/health")
@login_required
def api_proctor_health():
    import numpy as np
    svc = face_recognition_service
    fake = np.zeros((320,480,3), dtype=np.uint8)
    probe = svc.detect_faces_and_objects(fake)
    return jsonify({"ok": True, "available": svc.is_available(), "status": svc.debug_status(), "probe": probe.get("debug")})


@app.post("/api/proctor/analyze")
@login_required
def api_proctor_analyze():
    import os, base64, time, json
    from flask import current_app, session
    from services.face_recognition_service import get_face_recognition_service

    p = request.get_json(force=True) or {}
    image_payload = (
        p.get("image") or p.get("frame") or p.get("image_base64") or p.get("image_data")
    )
    if image_payload is None:
        return jsonify({"ok": False, "error": "Missing image payload"}), 400

    # --- coerce to raw bytes và lưu để dùng cho screenshot sau ---
    raw = None
    if isinstance(image_payload, (bytes, bytearray)):
        raw = bytes(image_payload)
    elif isinstance(image_payload, str):
        s = image_payload.split(",", 1)[-1].strip()
        try:
            raw = base64.b64decode(s, validate=False)
        except Exception:
            raw = image_payload.encode("utf-8", errors="ignore")
    elif isinstance(image_payload, list):
        try:
            raw = bytes(bytearray(image_payload))
        except Exception:
            return jsonify({"ok": False, "error": "Invalid image bytes list"}), 400
    else:
        return jsonify({"ok": False, "error": "Unsupported image payload type"}), 400

    # --- run service ---
    svc = get_face_recognition_service()
    if not svc.is_available():
        return jsonify({"ok": False, "error": "Face backends unavailable"}), 503

    result = svc.detect_faces_and_objects(raw) or {}
    if result.get("error"):
        return jsonify({"ok": False, "error": result.get("error"), "result": result}), 422
    
    # Lưu raw bytes vào result để dùng cho screenshot sau
    result["_raw_image_bytes"] = raw
    
    # --- ENRICH với model đã train (QUAN TRỌNG!) ---
    try:
        from services.attention_cheat_monitor import ProctorAugmentor
        augmentor = ProctorAugmentor()
        result = augmentor.enrich(result)  # Thêm cheat_proba, attention_proba từ model
    except Exception as e:
        if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
            current_app.logger.warning(f"[ENRICH] Failed to enrich result: {e}")
    
    IGNORE_AS_SUSPICIOUS = {
    c.strip().lower() for c in (os.getenv("IGNORE_SUSPICIOUS_CLASSES", "person,face,human") or "").split(",")
    }
    filtered_susp = []
    for o in (result.get("suspicious_objects") or []):
       name = (o.get("type") or o.get("label") or "").lower()
       if name in IGNORE_AS_SUSPICIOUS:
          continue
       filtered_susp.append(o)
    result["suspicious_objects"] = filtered_susp
    result["suspicious_count"] = len(filtered_susp)
    
    # --- Ensure attention percent fields for UI ---
    att = float(result.get("attention_score", 0.0) or 0.0)
    result["attention_pct"] = int(round(att * 100))
    val = result.get("attention_score_smooth")
    try:
        result["attention_pct_smooth"] = int(round(float(val) * 100))
    except Exception:
        result["attention_pct_smooth"] = result["attention_pct"]

    # --- Normalize counters (faces/objects/suspicious) ---
    try:
        if "suspicious_count" not in result or result.get("suspicious_count") is None:
            sc = 0
            objs = result.get("suspicious_objects")
            if isinstance(objs, list):
                sc = len(objs)
            result["suspicious_count"] = int(sc)

        objs_all = result.get("objects")
        result["object_count"] = int(
            result.get("object_count")
            or (len(objs_all) if isinstance(objs_all, list) else 0)
        )

        faces_all = result.get("faces") or result.get("faces_list")
        result["face_count"] = int(
            result.get("face_count")
            or (len(faces_all) if isinstance(faces_all, list) else int(result.get("faces") or 0))
        )
    except Exception:
        result.setdefault("suspicious_count", 0)
        result.setdefault("object_count", 0)
        result.setdefault("face_count", 0)

    # --- Policy / gating (NO-FACE => CHEAT after warm-up) ---
    warmup_sec = float(os.getenv("PROCTOR_WARMUP_SEC", "1.0"))
    t0 = session.get("proctor_started_at")
    try:
        started_ts = float(t0) if t0 is not None else None
    except Exception:
        started_ts = None
    elapsed = (time.time() - started_ts) if started_ts is not None else 999.0
    in_warmup = (elapsed < warmup_sec)

    armed_flag = bool(result.get("armed")) and not in_warmup
    state = "WARMUP" if in_warmup else "MONITORING"
    policy_level = (result.get("policy_level") or ("monitor" if armed_flag else "warmup")).lower()

    # --- THỨ TỰ ƯU TIÊN: Objects gian lận > Multiple faces > No face ---
    cheat_proba = float(result.get("cheat_proba") or 0.0)
    suspicious_count = int(result.get("suspicious_count") or 0)
    face_count = int(result.get("face_count") or 0)
    suspicious_objs = result.get("suspicious_objects") or []
    
    # Sử dụng model prediction để quyết định
    block_threshold = float(os.getenv("CHEAT_BLOCK_PROBA", "0.65"))
    warn_threshold = float(os.getenv("CHEAT_WARN_PROBA", "0.45"))
    
    # ƯU TIÊN 1: Objects gian lận (phone, book, tablet, etc.) - QUAN TRỌNG NHẤT
    has_suspicious_objects = suspicious_count > 0 and len(suspicious_objs) > 0
    suspicious_summary = result.get("suspicious_summary")
    
    # Lấy cheat_type trước để kiểm tra
    cheat_type = result.get("cheat_type", "unknown")
    
    # QUAN TRỌNG: Nếu cheat_type = "normal" thì KHÔNG được coi là gian lận
    # NHƯNG: looking_down và looking_away VẪN được coi là gian lận
    if cheat_type == "normal":
        # Reset các flag gian lận
        result["should_block"] = False
        result["should_warn"] = False
        result["cheating_detected"] = False
        result["cheating_reason"] = None
        # Không xử lý thêm, bỏ qua phần dưới
    elif cheat_type in ["looking_down", "looking_away"]:
        # Cúi xuống hoặc nhìn ra ngoài = gian lận
        # Đã được xử lý trong attention_cheat_monitor, chỉ cần đảm bảo flags đúng
        if not result.get("cheating_reason"):
            if cheat_type == "looking_down":
                result["cheating_reason"] = "Phát hiện cúi xuống - Có thể đang xem tài liệu gian lận"
            else:
                result["cheating_reason"] = "Phát hiện nhìn ra ngoài màn hình - Có thể đang gian lận"
    elif has_suspicious_objects or (cheat_proba > 0.0 and cheat_type != "normal"):
        # Ưu tiên sử dụng cheat_type từ multi-class model (đã được set trong enrich)
        cheat_type_conf = result.get("cheat_type_confidence", 0.0)
        
        # Lấy danh sách objects được phát hiện
        detected_types = [obj.get("type") or obj.get("label") for obj in suspicious_objs 
                         if obj.get("type") or obj.get("label")]
        detected_types = [t for t in detected_types if t.lower() != "person"]  # Bỏ qua person
        
        # Tạo thông báo cụ thể dựa trên objects
        if detected_types:
            # Loại bỏ duplicate và giới hạn số lượng
            unique_types = list(dict.fromkeys(detected_types))[:3]  # Giữ thứ tự, tối đa 3
            object_message = ", ".join(unique_types)
        else:
            object_message = None
        if suspicious_summary:
            object_message = suspicious_summary
        
        # Sử dụng cheat_type từ model nếu có và confidence cao
        # Ưu tiên sử dụng cheating_reason đã được set trong attention_cheat_monitor
        if result.get("cheating_reason"):
            # Đã có thông báo cụ thể từ attention_cheat_monitor - sử dụng luôn
            reason_message = result.get("cheating_reason")
        elif cheat_type != "unknown" and cheat_type != "normal" and cheat_type_conf > 0.5:
            # Model đã predict loại cụ thể - tạo thông báo phù hợp
            type_messages = {
                "phone": "⚠️ PHÁT HIỆN ĐIỆN THOẠI - Có thể đang tra cứu đáp án hoặc nhận hỗ trợ từ bên ngoài",
                "phone_call": "⚠️ PHÁT HIỆN ĐANG GỌI ĐIỆN - Có thể đang nhận hỗ trợ từ bên ngoài",
                "phone_selfie": "⚠️ PHÁT HIỆN SELFIE/CAMERA - Có thể đang chụp màn hình bài thi",
                "phone_screenshot": "⚠️ PHÁT HIỆN CHỤP MÀN HÌNH - Có thể đang lưu đề thi",
                "book": "⚠️ PHÁT HIỆN SÁCH/TÀI LIỆU - Có thể đang tra cứu đáp án",
                "tablet": "⚠️ PHÁT HIỆN TABLET/LAPTOP - Có thể đang tra cứu tài liệu",
                "glasses_suspicious": "⚠️ PHÁT HIỆN HÀNH VI ĐÁNG NGỜ VỚI KÍNH - Có thể đang sử dụng thiết bị hỗ trợ",
                "looking_away": "⚠️ PHÁT HIỆN NHÌN RA NGOÀI MÀN HÌNH - Có thể đang xem tài liệu hoặc nhận hỗ trợ",
                "looking_down": "⚠️ PHÁT HIỆN CÚI XUỐNG - Có thể đang xem tài liệu gian lận dưới bàn",
                "cheating_generic": "⚠️ PHÁT HIỆN HÀNH VI GIAN LẬN - Vui lòng tập trung vào bài thi"
            }
            reason_message = type_messages.get(cheat_type, f"Phát hiện hành vi gian lận: {cheat_type}")
        elif object_message:
            # Fallback: dựa trên objects được phát hiện
            reason_message = f"Phát hiện vật thể gian lận: {object_message}"
        else:
            # Fallback cuối cùng
            if suspicious_summary:
                reason_message = f"Phát hiện vật thể đáng ngờ: {suspicious_summary}"
            else:
                reason_message = (
                    f"Phát hiện hành vi gian lận (xác suất: {cheat_proba:.1%})"
                    if cheat_proba > 0
                    else "Phát hiện vật thể đáng ngờ"
                )
        
        # Quyết định block/warn dựa trên cheat_proba hoặc suspicious_count
        # CHỈ block/warn khi:
        # 1. Có suspicious objects (phone, book, tablet, etc.)
        # 2. Hoặc cheat_proba cao VÀ cheat_type KHÔNG phải "normal"
        # 3. Hoặc không có mặt (face_count = 0) - xử lý riêng ở dưới
        
        if has_suspicious_objects:
            # Có vật thể gian lận = chắc chắn gian lận
            result["should_block"] = True
            result["cheating_detected"] = True
            result["cheating_reason"] = reason_message
        elif cheat_proba >= block_threshold and cheat_type != "normal":
            # Cheat_proba cao VÀ không phải "normal"
            result["should_block"] = True
            result["cheating_detected"] = True
            result["cheating_reason"] = reason_message
        elif cheat_proba >= warn_threshold and cheat_type != "normal":
            # Cheat_proba trung bình VÀ không phải "normal"
            result["should_warn"] = True
            result["cheating_reason"] = reason_message
    
    # Không xoá nghi vấn trong warm-up; chỉ hạ UI action
    if in_warmup or policy_level == "warmup":
        ui_action = "none"
    else:
        ui_action = "block" if result.get("should_block") else ("warn" if result.get("should_warn") else "none")

    # ƯU TIÊN 2: Multiple faces - CHỈ khi KHÔNG có objects gian lận
    multi_face_warn  = int(os.getenv("MULTI_FACE_WARN_COUNT", "2"))  # >=2 mặt thì cảnh báo
    multi_face_block = os.getenv("MULTI_FACE_BLOCK", "0").lower() in ("1","true","yes","on")
    
    # CHỈ xử lý multiple faces nếu:
    # 1. Chưa có cảnh báo từ objects gian lận
    # 2. Thực sự có nhiều hơn 1 mặt
    # 3. Không trong warmup
    if (not result.get("should_block") and not result.get("should_warn") and 
        not in_warmup and face_count >= multi_face_warn and 
        not has_suspicious_objects):  # QUAN TRỌNG: Không có objects gian lận
        # Chỉ set "nhiều khuôn mặt" khi thực sự có nhiều hơn 1 mặt
        result["cheating_reason"] = f"Phát hiện {face_count} khuôn mặt trong khung hình - Có thể có người khác hỗ trợ"
        if multi_face_block:
            result["should_block"] = True
            result["cheating_detected"] = True
            ui_action = "block"
        else:
            result["should_warn"] = True
            if not result.get("should_block"):
                ui_action = "warn"
    
    # Luật NO-FACE => CẢNH BÁO/BLOCK
    no_face_warn_frames = int(os.getenv("NO_FACE_WARN_FRAMES", "2"))   # Cảnh báo sau 2 frames
    no_face_block_sec   = float(os.getenv("NO_FACE_BLOCK_SEC",  "1.5"))  # Block sau 1.5s (giảm từ 2.0)
    no_face_frames_req  = int(os.getenv("NO_FACE_REQ_FRAMES",   "4"))   # Block sau 4 frames (giảm từ 6)
    
    # ƯU TIÊN 3: No face - CHỈ khi KHÔNG có objects gian lận VÀ không có multiple faces
    if (not result.get("should_block") and not result.get("should_warn") and 
        not has_suspicious_objects):  # QUAN TRỌNG: Không có objects gian lận
        nf = session.get("no_face_frames", 0)
        nf = (nf + 1) if face_count == 0 else 0
        session["no_face_frames"] = nf
        
        if face_count == 0:
            # CẢNH BÁO ngay cả trong warmup (nhưng không block)
            if nf >= no_face_warn_frames:
                result["should_warn"] = True
                result["cheating_reason"] = "Không phát hiện khuôn mặt trong camera - Vui lòng điều chỉnh camera"
                if not in_warmup:
                    ui_action = "warn"
                else:
                    # Trong warmup: chỉ cảnh báo, không block
                    ui_action = "warn"
            
            # BLOCK sau warmup nếu không có mặt quá lâu
            if not in_warmup:
                if (elapsed >= (warmup_sec + no_face_block_sec)) or (nf >= no_face_frames_req):
                    result["cheating_detected"] = True
                    result["cheating_reason"] = "Không phát hiện khuôn mặt - Có thể đang gian lận"
                    result["should_block"] = True
                    ui_action = "block"
        else:
            # Reset counter khi có mặt lại
            if nf > 0:
                session["no_face_frames"] = 0

    # --- Finalize policy fields for FE ---
    result["state"] = state
    result["ui_action"] = ui_action
    result["policy_level"] = policy_level
    policy = result.get("policy") or {}
    policy.update({"level": policy_level, "armed": (not in_warmup)})
    result["policy"] = policy

    # --- debug log (optional) ---
    try:
        if os.getenv("AI_DEBUG","0").lower() in ("1","true","yes","on"):
            cheat_proba = result.get('cheat_proba', 0.0)
            suspicious_objs = result.get('suspicious_objects', [])
            detected_types = [obj.get('type') or obj.get('label') for obj in suspicious_objs[:3]]
            current_app.logger.info(
                "[ANALYZE] faces=%s objs=%s susp=%s cheat_proba=%.2f detected=%s state=%s armed=%s warmup=%s action=%s reason=%s",
                result.get('face_count'), result.get('object_count'), result.get('suspicious_count'),
                cheat_proba, detected_types, result.get('state'), bool(result.get('armed')), 
                in_warmup, ui_action, result.get('cheating_reason', '')[:50]
            )
    except Exception:
        pass

    # --- chuẩn bị thông tin người dùng & chụp screenshot (dù có attempt hay không) ---
    session_user = session.get("user") or {}
    user_id = session_user.get("id")
    username = (
        session.get("username")
        or session_user.get("username")
        or session_user.get("name")
        or str(user_id or "unknown_user")
    )

    should_capture = (
        result.get("cheating_detected")
        or result.get("should_block")
        or result.get("should_warn")
        or (int(result.get("suspicious_count") or 0) > 0)
        or (len(result.get("suspicious_objects") or []) > 0)
        or (result.get("cheat_type") not in [None, "normal", "unknown"])
    )

    screenshot_path = None
    screenshot_timestamp = None

    if should_capture:
        frame_bgr = None

        # Ưu tiên: raw bytes đã lưu trong result
        if result.get("_raw_image_bytes"):
            try:
                import numpy as np
                raw_bytes = result.get("_raw_image_bytes")
                nparr = np.frombuffer(raw_bytes, np.uint8)
                frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
                    current_app.logger.info(f"[AUTO-CAPTURE] Using raw bytes from result, size: {len(raw_bytes)}")
            except Exception as e:
                if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
                    current_app.logger.warning(f"[AUTO-CAPTURE] Failed to decode raw bytes from result: {e}")

        # Fallback: raw bytes trong scope local
        if (frame_bgr is None or (hasattr(frame_bgr, "size") and frame_bgr.size == 0)) and raw:
            try:
                import numpy as np
                nparr = np.frombuffer(raw, np.uint8)
                frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
                    current_app.logger.info(f"[AUTO-CAPTURE] Using raw bytes from local scope, size: {len(raw)}")
            except Exception as e:
                if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
                    current_app.logger.warning(f"[AUTO-CAPTURE] Failed to decode raw bytes from local: {e}")

        # Fallback cuối: payload base64
        if frame_bgr is None or (hasattr(frame_bgr, "size") and frame_bgr.size == 0):
            img_base64 = p.get("image") or p.get("frame") or p.get("image_base64") or p.get("snapshot")
            if img_base64:
                try:
                    if isinstance(img_base64, str):
                        if img_base64.startswith("data:image"):
                            img_base64 = img_base64.split(",", 1)[-1]
                        img_bytes = base64.b64decode(img_base64, validate=False)
                    else:
                        img_bytes = bytes(img_base64)

                    import numpy as np
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                except Exception as e:
                    if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
                        current_app.logger.warning(f"[AUTO-CAPTURE] Failed to decode image: {e}")

        if frame_bgr is not None and frame_bgr.size > 0:
            cheating_reason = result.get("cheating_reason") or result.get("cheat_type") or "cheating_detected"
            try:
                screenshot_path = save_cheat_frame(frame_bgr, username, cheating_reason)
                screenshot_timestamp = datetime.datetime.now().isoformat()
                result["screenshot_path"] = screenshot_path

                current_app.logger.info(
                    f"[AUTO-CAPTURE] ✅ Saved cheat screenshot: {screenshot_path} | "
                    f"Reason: {cheating_reason} | User: {username} | "
                    f"Flags: detected={result.get('cheating_detected')}, block={result.get('should_block')}, "
                    f"warn={result.get('should_warn')}, susp_count={result.get('suspicious_count')}, "
                    f"cheat_type={result.get('cheat_type')}"
                )
            except Exception as save_err:
                current_app.logger.error(f"[AUTO-CAPTURE] ❌ Failed to save screenshot: {save_err}")
                import traceback
                current_app.logger.error(traceback.format_exc())
        else:
            current_app.logger.warning(
                f"[AUTO-CAPTURE] ⚠️  Should capture but no image data available | "
                f"Flags: detected={result.get('cheating_detected')}, block={result.get('should_block')}, "
                f"warn={result.get('should_warn')}, susp_count={result.get('suspicious_count')}, "
                f"cheat_type={result.get('cheat_type')}"
            )

    # --- persist frame & events (best-effort) ---
    try:
        attempt_id = (p.get("attempt_id") or "").strip()
        course_id  = int(p.get("course_id") or 0)
        
        # QUAN TRỌNG: Luôn lưu event nếu có dấu hiệu gian lận, kể cả khi không có attempt_id/course_id
        # Điều này đảm bảo tất cả hành vi gian lận đều được ghi vào DB
        has_cheating = (
            result.get("should_block") or 
            result.get("should_warn") or 
            int(result.get("suspicious_count") or 0) > 0 or 
            result.get("cheating_detected") or
            (result.get("cheat_type") not in [None, "normal", "unknown"])
        )

        if attempt_id and user_id and course_id:
            # 1) lưu frame (chỉ khi có attempt_id)
            course_controller.course_model.log_proctor_frame(
                attempt_id=attempt_id,
                user_id=user_id,
                course_id=course_id,
                frame_no=int(p.get("frame_no") or 0),
                face_count=int(result.get("face_count") or 0),
                attention_score=float(result.get("attention_score") or 0.0),
                objects_json=json.dumps(result.get("objects") or [], ensure_ascii=False),
                snapshot_url=p.get("snapshot_url")
            )

            # 2) nếu có cảnh báo hoặc nghi vấn thì lưu event
            if has_cheating:
                evt = "block" if result.get("should_block") else ("warn" if result.get("should_warn") else ("cheating" if result.get("cheating_detected") else "suspicious_objects"))
                payload_meta = {
                    "source": "proctor.analyze",
                    "suspicious_count": int(result.get("suspicious_count") or 0),
                    "cheating_reason": result.get("cheating_reason"),
                    "ui_action": result.get("ui_action"),
                    "state": result.get("state"),
                }
                
                if screenshot_path:
                    payload_meta["screenshot_path"] = screenshot_path
                    payload_meta["screenshot_saved"] = True
                    payload_meta["screenshot_timestamp"] = screenshot_timestamp
                
                # 4) LƯU ĐẦY ĐỦ THÔNG TIN GIAN LẬN VÀO DATABASE
                # Bao gồm: hành vi gian lận, ngày, giờ, screenshot path, cheat_type, confidence
                cheating_reason = result.get("cheating_reason") or "Hành vi gian lận được phát hiện"
                cheat_type = result.get("cheat_type", "unknown")
                cheat_type_conf = result.get("cheat_type_confidence", 0.0)
                cheat_proba = result.get("cheat_proba", 0.0)
                
                # Tạo metadata đầy đủ (bao gồm screenshot_path nếu có)
                full_meta = {
                    **payload_meta,
                    "cheating_reason": cheating_reason,
                    "cheat_type": cheat_type,
                    "cheat_type_confidence": float(cheat_type_conf),
                    "cheat_proba": float(cheat_proba),
                    "suspicious_objects": result.get("suspicious_objects", []),
                    "suspicious_count": int(result.get("suspicious_count") or 0),
                    "face_count": int(result.get("face_count") or 0),
                    "attention_score": float(result.get("attention_score") or 0.0),
                    "should_block": bool(result.get("should_block")),
                    "should_warn": bool(result.get("should_warn")),
                    "cheating_detected": bool(result.get("cheating_detected")),
                    "detected_at": datetime.datetime.now().isoformat(),  # Thời gian phát hiện chính xác
                    "detected_date": datetime.datetime.now().strftime("%Y-%m-%d"),  # Ngày phát hiện
                    "detected_time": datetime.datetime.now().strftime("%H:%M:%S"),  # Giờ phát hiện
                }
                
                # Đảm bảo screenshot_path được thêm vào full_meta nếu có
                if screenshot_path:
                    full_meta["screenshot_path"] = screenshot_path
                    full_meta["screenshot_saved"] = True
                    full_meta["screenshot_timestamp"] = screenshot_timestamp
                
                # thử 2 chữ ký khác nhau tuỳ DB của bạn
                try:
                    course_controller.course_model.log_proctor_event(
                        attempt_id=attempt_id,
                        user_id=user_id,
                        course_id=course_id,
                        event=evt,
                        reason=cheating_reason,
                        meta=json.dumps(full_meta, ensure_ascii=False)
                    )
                except TypeError:
                    course_controller.course_model.log_proctor_event(
                        attempt_id=attempt_id,
                        user_id=user_id,
                        course_id=course_id,
                        event_type=evt,
                        confidence=float(cheat_proba) if cheat_proba > 0 else 1.0,
                        meta_json=json.dumps(full_meta, ensure_ascii=False)
                    )
        elif has_cheating and user_id:
            # QUAN TRỌNG: Lưu event ngay cả khi KHÔNG có attempt_id/course_id
            # Đảm bảo tất cả hành vi gian lận đều được ghi vào DB
            evt = "block" if result.get("should_block") else ("warn" if result.get("should_warn") else ("cheating" if result.get("cheating_detected") else "suspicious_objects"))
            cheating_reason = result.get("cheating_reason") or "Hành vi gian lận được phát hiện"
            cheat_type = result.get("cheat_type", "unknown")
            cheat_type_conf = result.get("cheat_type_confidence", 0.0)
            cheat_proba = result.get("cheat_proba", 0.0)
            
            full_meta = {
                "source": "proctor.analyze",
                "suspicious_count": int(result.get("suspicious_count") or 0),
                "cheating_reason": cheating_reason,
                "ui_action": result.get("ui_action"),
                "state": result.get("state"),
                "cheat_type": cheat_type,
                "cheat_type_confidence": float(cheat_type_conf),
                "cheat_proba": float(cheat_proba),
                "suspicious_objects": result.get("suspicious_objects", []),
                "face_count": int(result.get("face_count") or 0),
                "attention_score": float(result.get("attention_score") or 0.0),
                "should_block": bool(result.get("should_block")),
                "should_warn": bool(result.get("should_warn")),
                "cheating_detected": bool(result.get("cheating_detected")),
                "detected_at": datetime.datetime.now().isoformat(),
                "detected_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "detected_time": datetime.datetime.now().strftime("%H:%M:%S"),
            }
            
            # Thêm screenshot_path nếu có
            if screenshot_path:
                full_meta["screenshot_path"] = screenshot_path
                full_meta["screenshot_saved"] = True
                full_meta["screenshot_timestamp"] = screenshot_timestamp
            
            # Lưu event với attempt_id=None, course_id=0
            try:
                course_controller.course_model.log_proctor_event(
                    attempt_id=None,
                    user_id=user_id,
                    course_id=0,  # 0 = không xác định được course
                    event=evt,
                    reason=cheating_reason,
                    meta=json.dumps(full_meta, ensure_ascii=False)
                )
            except TypeError:
                course_controller.course_model.log_proctor_event(
                    attempt_id=None,
                    user_id=user_id,
                    course_id=0,
                    event_type=evt,
                    confidence=float(cheat_proba) if cheat_proba > 0 else 1.0,
                    meta_json=json.dumps(full_meta, ensure_ascii=False)
                )
            
            current_app.logger.info(
                f"[EVENT] ✅ Saved cheating event (no attempt_id) | "
                f"User: {username} | Reason: {cheating_reason} | "
                f"Screenshot: {screenshot_path or 'none'}"
            )
    except Exception as _e:
        try:
            current_app.logger.exception("persist proctor data failed: %s", _e)
        except Exception:
            pass

    # --- Xóa _raw_image_bytes khỏi result trước khi trả về JSON (bytes không thể serialize) ---
    if "_raw_image_bytes" in result:
        del result["_raw_image_bytes"]
    
    # --- always return JSON ---
    return jsonify({"ok": True, "result": result}), 200



# --- REPLACE the whole exam_result route with this version ---
@app.route("/exam/<int:course_id>/result")
@login_required
def exam_result(course_id):
    from flask import session

    attempt_id = request.args.get("attempt_id")
    if not attempt_id:
        return redirect(url_for("exam", course_id=course_id))

    results: dict | None = None
    rows: list | None = None

    # 1) Cache
    cache = getattr(course_controller, "EXAM_RESULTS_CACHE", {})
    if attempt_id in cache:
        results = cache[attempt_id]
        detailed = results.get("detailed_results") or results.get("details") or []
        for r in detailed:
            options = r.get("options") or []

            # correct_index
            if "correct_index" not in r or r.get("correct_index") is None:
                h_hmac, h_sha1 = _option_hashes_both(options)
                ch = (r.get("correct_hash") or "").strip()
                r["correct_index"] = h_hmac.index(ch) if ch in h_hmac else (
                    h_sha1.index(ch) if ch in h_sha1 else 0
                )

            # user_answer_index
            if "user_answer_index" not in r or r.get("user_answer_index") in (None, -1, ""):
                ua = (r.get("user_answer") or "").strip()
                uidx = -1
                try:
                    uidx = int(ua)
                except Exception:
                    h_hmac, h_sha1 = _option_hashes_both(options)
                    if ua in h_hmac: uidx = h_hmac.index(ua)
                    elif ua in h_sha1: uidx = h_sha1.index(ua)
                    else:
                        nopts = [_norm_text(o).lower() for o in options]
                        nua = _norm_text(ua).lower()
                        uidx = nopts.index(nua) if nua in nopts else -1
                r["user_answer_index"] = uidx

            # explanation_html
            if not r.get("explanation_html"):
                _explain = globals().get("detailed_explain_html")
                cidx = int(r.get("correct_index") or 0)
                uidx = int(r.get("user_answer_index") or -1)
                if callable(_explain):
                    html = _explain(r.get("question", ""), options, cidx, uidx)
                else:
                    letter = "ABCD"[cidx] if 0 <= cidx < 4 else "A"
                    html = (f"<p><strong>Tóm tắt:</strong> Đáp án đúng là <b>{letter}</b>.</p>"
                            "<p>Hãy đối chiếu định nghĩa/điều kiện của từng lựa chọn và chú ý các từ khóa.</p>")
                r["explanation_html"] = html
                r["explanation"] = html

        if not results.get("total"):
            correct_cnt = sum(1 for it in detailed
                              if int(it.get("user_answer_index", -1)) == int(it.get("correct_index", -1)))
            total = len(detailed)
            results["total"] = total
            results["correct"] = correct_cnt
            results["score"] = round((correct_cnt / total * 100.0), 2) if total else 0.0

    # 2) Không có cache → đọc DB và dựng lại
    else:
        rows = course_controller.course_model.get_exam_results(attempt_id) or []
        detailed, correct_cnt, total = [], 0, 0
        _explain = globals().get("detailed_explain_html")

        for idx, r in enumerate(rows):
            options = r.get("options") or []
            h_hmac, h_sha1 = _option_hashes_both(options)
            ch = (r.get("correct_hash") or "").strip()

            if ch in h_hmac: cidx = h_hmac.index(ch)
            elif ch in h_sha1: cidx = h_sha1.index(ch)
            else: cidx = int((r.get("rubric") or {}).get("correct_index", 0)) if isinstance(r.get("rubric"), dict) else 0

            ua = (r.get("user_answer") or "").strip()
            uidx = -1
            try:
                uidx = int(ua)
            except Exception:
                if ua in h_hmac: uidx = h_hmac.index(ua)
                elif ua in h_sha1: uidx = h_sha1.index(ua)
                else:
                    nopts = [_norm_text(o).lower() for o in options]
                    nua = _norm_text(ua).lower()
                    uidx = nopts.index(nua) if nua in nopts else -1

            ok = (uidx == cidx)
            if ok: correct_cnt += 1
            total += 1

            explain_html = (f"<p><strong>Đúng:</strong> Bạn đã chọn đáp án chính xác (<code>{options[cidx]}</code>).</p>"
                            if ok else
                            (_explain(r.get("question",""), options, cidx, uidx)
                             if callable(_explain) else
                             f"<p>Đáp án đúng là <b>{'ABCD'[cidx] if 0 <= cidx < 4 else 'A'}</b>.</p>"))

            detailed.append({
                "question_number": idx + 1,
                "question": r.get("question",""),
                "options": options,
                "correct_index": cidx,
                "user_answer_index": uidx,
                "user_answer_option": (options[uidx] if 0 <= uidx < len(options) else None),
                "is_correct": bool(ok),
                "explanation_html": explain_html,
                "explanation": explain_html,
                "time_spent_ms": int(r.get("time_spent_ms") or 0),
            })

        score = round((correct_cnt / total * 100.0), 2) if total else 0.0
        results = {
            "course_id": course_id,
            "score": score,
            "correct": correct_cnt,
            "total": total,
            "detailed_results": detailed,
        }

    # 2.5) --- Gọi giáo viên AI để sinh nhận xét & gợi ý khóa học ---
    try:
        catalog = _fetch_courses_catalog()
        teacher = build_teacher_report(results, catalog)
        results["strengths"] = teacher.get("strengths") or results.get("strengths")
        results["weaknesses"] = teacher.get("weaknesses") or results.get("weaknesses")
        results["recommendations"] = teacher.get("recommendations") or results.get("recommendations")
        results["teacher_source"] = teacher.get("source", "unknown")
    except Exception:
        # Nếu có lỗi vẫn cho hiển thị bình thường
        pass

    # 3) Lưu dấu attempt (idempotent)
    try:
        if session.get("history_saved_attempt_id") != attempt_id:
            session["history_saved_attempt_id"] = attempt_id
    except Exception:
        pass

    # 4) Render
    return render_template(
        "exam_result.html",
        course_id=course_id,
        attempt_id=attempt_id,
        results=results,
    )

    
    
@app.get("/api/exam/attempt/summary")
@login_required
def api_exam_attempt_summary():
    """
    Trả về tóm tắt cho một attempt:
    { ok, summary: {attempt_id, course_id, score, correct, total, strengths, weaknesses, recommendations} }
    """
    attempt_id = request.args.get("attempt_id")
    course_id = int(request.args.get("course_id") or 0)
    if not attempt_id:
        return jsonify({"ok": False, "error": "missing attempt_id"}), 400

    try:
        # 1) ưu tiên cache
        if hasattr(course_controller, 'EXAM_RESULTS_CACHE') and attempt_id in course_controller.EXAM_RESULTS_CACHE:
            res = course_controller.EXAM_RESULTS_CACHE[attempt_id] or {}
        else:
            # 2) ráp từ DB tương tự exam_result(...)
            rows = course_controller.course_model.get_exam_results(attempt_id) or []
            correct_cnt, total = 0, 0
            for r in rows:
                options = r.get("options") or []
                # xác định index đáp án đúng từ hash
                chashes = []
                try:
                    import hashlib
                    def _nh(s): return hashlib.sha1((s or "").strip().lower().encode("utf-8")).hexdigest()[:16]
                    chashes = [_nh(o) for o in options]
                except Exception:
                    pass
                try:
                    correct_index = chashes.index(r.get("correct_hash"))
                except Exception:
                    correct_index = 0
                # ánh xạ user_answer -> index
                ua = r.get("user_answer")
                try:
                    user_index = int(ua)
                except Exception:
                    try:    user_index = chashes.index(ua)
                    except Exception:
                        try:    user_index = options.index(ua)
                        except Exception: user_index = -1
                if user_index == correct_index:
                    correct_cnt += 1
                total += 1

            score = round((correct_cnt / total * 100.0), 2) if total else 0.0
            if score >= 80:
                rec = "Làm rất tốt! Bạn có thể thử khóa nâng cao để thách thức bản thân."
            elif score >= 50:
                rec = "Bạn nên ôn lại phần cơ bản và luyện thêm các câu vận dụng."
            else:
                rec = "Nên bắt đầu lại từ phần nhập môn để nắm chắc nền tảng trước."

            res = {
                "course_id": course_id,
                "score": score,
                "correct": correct_cnt,
                "total": total,
                "strengths": "Nắm tốt các khái niệm cơ bản.",
                "weaknesses": "Dễ nhầm ở câu vận dụng/so sánh.",
                "recommendations": rec,
            }

        summary = {
            "attempt_id": attempt_id,
            "course_id": res.get("course_id") or course_id,
            "score": float(res.get("score") or 0.0),
            "correct": int(res.get("correct") or 0),
            "total": int(res.get("total") or 0),
            "strengths": res.get("strengths") or "",
            "weaknesses": res.get("weaknesses") or "",
            "recommendations": res.get("recommendations") or "",
        }
        return jsonify({"ok": True, "summary": summary})
    except Exception as e:
        try: current_app.logger.exception("api_exam_attempt_summary failed: %s", e)
        except: pass
        return jsonify({"ok": False, "error": "internal_error"}), 500
   



@app.post('/api/courses/<int:cid>/generate_caption')
def gen_caption(cid):
    return course_controller.generate_caption(cid)

# Test route for quiz video feature
@app.route("/test-quiz-video")
def test_quiz_video():
    """Test route for the 50-second quiz video feature"""
    return render_template("test_quiz_video.html")

# Lesson view with quiz feature
@app.route("/lesson/<int:course_id>")
@login_required
def lesson_view(course_id):
    """View lesson with 50-second quiz feature"""
    # Get course data
    course = course_controller.course_model.get_course_by_id(course_id)
    if not course:
        return "Course not found", 404
    
    # Convert course to dict if it's an object
    try:
        course = {k: course[k] for k in course.keys()}
    except Exception:
        pass
    
    return render_template("lesson_view.html", 
                         course_title=course.get('title', 'Bài giảng'),
                         lesson_title=course.get('title', 'Bài giảng'),
                         video_url=course.get('video_url', ''),
                         caption_url=course.get('caption_url', ''),
                         video_id=str(course_id),
                         caption_path=course.get('caption_url', '').lstrip('/') if course.get('caption_url') else '')

# ---- Anti-cheat API ----
@app.post("/api/exam/cheating")
@login_required
def api_exam_cheating():
    p = request.get_json(force=True) or {}
    attempt_id = p.get("attempt_id")
    course_id = int(p.get("course_id") or 0)
    user_id = session.get("user",{}).get("id")

    if p.get("force") is True and attempt_id:
        # 1) log event
        course_controller.course_model.log_proctor_event(
            attempt_id=attempt_id,
            user_id=user_id,
            course_id=course_id,
            event_type="terminated",
            reason="force",
            confidence=1.0,
            meta_json=json.dumps({"source":"cheating.force"}, ensure_ascii=False)
        )
        # 2) đóng comprehensive
        course_controller.course_model.terminate_comprehensive_attempt(attempt_id)
        # 3) đóng exam_attempts (nếu có)
        try:
            course_controller.course_model.finish_attempt(attempt_id, score=0.0, cheated=True)
        except Exception:
            pass
        # 4) set cache
        att = course_controller.ATTEMPT_CACHE.get(attempt_id) or {}
        att["cheated"] = True
        course_controller.ATTEMPT_CACHE[attempt_id] = att
        return jsonify({"ok": True, "closed": True, "forced": True})

    return jsonify({"ok": False, "error": "missing attempt_id or force flag"}), 400





# (A) Phân tích một file ảnh trên server
@app.post("/api/proctor/analyze-file")
@login_required
def api_proctor_analyze_file():
    from services.face_recognition_service import get_face_recognition_service
    data = request.get_json(force=True) or {}
    path = (data.get("path") or "").strip()
    if not path:
        return jsonify({"ok": False, "error": "Missing 'path'"}), 400

    # Chỉ cho phép đọc trong các thư mục an toàn
    allowed_roots = {"attention_dataset", "static/uploads", "data_quiz"}
    import os
    ap = os.path.abspath(path)
    if not any(os.path.abspath(root) in ap for root in [os.path.abspath(r) for r in allowed_roots]):
        return jsonify({"ok": False, "error": "Path not allowed"}), 403
    if not os.path.exists(ap):
        return jsonify({"ok": False, "error": f"File not found: {ap}"}), 404

    svc = get_face_recognition_service()
    result = svc.detect_faces_and_objects(ap)   # path được hỗ trợ ở bước (1)
    att = float(result.get("attention_score") or 0.0)
    result["attention_pct"] = int(round(att * 100))
    result["ui_action"] = "block" if result.get("should_block") else ("warn" if result.get("should_warn") else "none")
    return jsonify({"ok": True, "result": result})


# (B) Đánh giá cả thư mục (tùy chọn, hữu ích để kiểm thử)
@app.post("/api/proctor/eval-dataset")
@login_required
def api_proctor_eval_dataset():
    """
    Body JSON: { "dir": "attention_dataset", "glob": "*.jpg", "labels_csv": "attention_dataset/annotations.csv" }
    """
    import os, glob, csv
    from services.face_recognition_service import get_face_recognition_service
    p = request.get_json(force=True) or {}
    root = (p.get("dir") or "attention_dataset").strip()
    pattern = p.get("glob") or "*.*"
    labels_csv = (p.get("labels_csv") or "").strip()

    base = os.path.abspath(root)
    if not os.path.isdir(base):
        return jsonify({"ok": False, "error": f"Not a directory: {base}"}), 404

    labels = {}
    if labels_csv and os.path.exists(labels_csv):
        with open(labels_csv, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                labels[r["filename"]] = r.get("attention_label") or ""

    svc = get_face_recognition_service()
    rows = []
    for fp in glob.glob(os.path.join(base, pattern)):
        res = svc.detect_faces_and_objects(fp)
        att = float(res.get("attention_score") or 0.0)
        pose = res.get("head_pose") or {}
        rows.append({
            "file": os.path.basename(fp),
            "faces": int(res.get("face_count") or 0),
            "att_score": round(att, 4),
            "att_pct": int(round(att*100)),
            "pose_yaw": float(pose.get("yaw") or 0.0),
            "pose_pitch": float(pose.get("pitch") or 0.0),
            "suspicious": int(res.get("suspicious_count") or 0),
            "should_warn": bool(res.get("should_warn")),
            "should_block": bool(res.get("should_block")),
            "label": labels.get(os.path.basename(fp))
        })
    return jsonify({"ok": True, "count": len(rows), "items": rows})



@app.post("/api/exam/terminate")
@login_required
def api_exam_terminate():
    """
    Hủy bài thi (luồng exam_attempts cũ): chấm 0 và ghi nhận lần thi + sự kiện gian lận.
    Body JSON: { attempt_id, reason? }
    """
    import datetime, json
    data = request.get_json(force=True) or {}
    attempt_id = data.get("attempt_id")
    reason = data.get("reason", "Phát hiện hành vi gian lận")

    if not attempt_id:
        return jsonify({"ok": False, "error": "Missing attempt_id"}), 400

    # 1) Cập nhật lần thi trong exam_attempts
    with course_controller.course_model._connect() as conn:
        cur = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        cur.execute("""
            UPDATE exam_attempts
               SET ended_at = ?, cheated = 1, score = 0
             WHERE id = ?
        """, (now, attempt_id))
        conn.commit()

        # Lấy user/course từ exam_attempts (fallback sang comprehensive_exams khi cần)
        cur.execute("SELECT course_id, user_id FROM exam_attempts WHERE id = ?", (attempt_id,))
        row = cur.fetchone()
        if row and row[0] is not None and row[1] is not None:
            course_id2, user_id2 = row
        else:
            course_id2, user_id2 = course_controller.course_model.get_course_id_by_attempt(attempt_id)

    # 2) Ghi sự kiện để bảng AI đếm cheat_events
    if course_id2 and user_id2:
        course_controller.course_model.log_proctor_event(
            attempt_id=attempt_id,
            user_id=user_id2,
            course_id=course_id2,
            event_type="terminated",
            confidence=1.0,
            meta_json=json.dumps({"reason": reason}, ensure_ascii=False)
        )

    return jsonify({"ok": True, "message": "Exam terminated and recorded"}), 200


@app.route("/api/ai/debug", methods=["GET"])
def ai_debug():
    frs = get_face_recognition_service()
    return jsonify(frs.debug_status())

@app.route("/api/proctor/debug_frs")
def debug_frs():
    from services.face_recognition_service import get_face_recognition_service
    svc = get_face_recognition_service()
    return jsonify(svc.debug_status())


@app.get("/api/proctor/model-status")
@login_required
def api_proctor_model_status():
    from services.attention_calibration import load_calibration
    data = load_calibration()
    
    return jsonify({
        "ok": True,
        "model_loaded": bool(data.get("logreg")),
        "cheat_model_loaded": bool(data.get("cheat_logreg")),
        "calibration_file": data.get("trained_at"),
        "n_samples": data.get("n_samples"),
        "attention_acc": data.get("logreg", {}).get("acc"),
        "cheat_acc": data.get("cheat_logreg", {}).get("acc")
    })


@app.post("/api/convert-doc-to-video")
@login_required
def api_convert_doc_to_video():
    return course_controller.api_doc_to_video()

@app.post("/api/captions/auto")
@login_required
def api_captions_auto():
    """Tự động tạo hoặc lấy caption cho video"""
    return course_controller.api_captions_auto()

@app.get("/api/captions/status")
@login_required
def api_captions_status():
    """Kiểm tra xem video đã có caption chưa"""
    return course_controller.api_captions_status()

@app.post("/api/segments/generate-questions")
@login_required
def api_segments_generate_questions():
    """Pre-generate questions cho tất cả các segment 50s dựa trên transcript"""
    return course_controller.api_generate_segment_questions()

@app.get("/api/segments/question")
@login_required
def api_segments_question():
    """Lấy câu hỏi đã pre-generate cho một segment"""
    return course_controller.api_get_segment_question()

@app.post("/api/comprehensive-exam/start")
@login_required
def api_comprehensive_exam_start():
    """Bắt đầu bài kiểm tra 20 câu trong 15 phút"""
    return course_controller.api_comprehensive_exam_start()

@app.get("/api/comprehensive-exam/question")
@login_required
def api_comprehensive_exam_get_question():
    """Lấy câu hỏi theo index"""
    return course_controller.api_comprehensive_exam_get_question()

@app.post("/api/comprehensive-exam/submit-answer")
@login_required
def api_comprehensive_exam_submit_answer():
    """Submit đáp án cho một câu hỏi"""
    return course_controller.api_comprehensive_exam_submit_answer()

@app.post("/api/comprehensive-exam/finish")
@login_required
def api_comprehensive_exam_finish():
    """Hoàn thành exam và nhận kết quả"""
    return course_controller.api_comprehensive_exam_finish()

@app.post("/api/comprehensive-exam/terminate")
@login_required
def api_comprehensive_exam_terminate():
    """Hủy bài kiểm tra do gian lận"""
    return course_controller.api_comprehensive_exam_terminate()

@app.get("/api/comprehensive-exam/results")
@login_required
def api_comprehensive_exam_results():
    """Lấy kết quả exam"""
    return course_controller.api_comprehensive_exam_results()

@app.route("/comprehensive-exam/<int:course_id>")
@login_required
def comprehensive_exam_page(course_id):
    """Trang làm bài kiểm tra comprehensive"""
    course = course_controller.course_model.get_course_by_id(course_id)
    if not course:
        return redirect(url_for("list_courses"))
    return render_template("comprehensive_exam.html", course=course, course_id=course_id)

# ---- Score Management for Teachers ----
@app.route("/manage-scores")
@login_required
def manage_scores():
    """Trang quản lý điểm cho giáo viên"""
    if session.get("role") != "teacher":
        abort(403)
    return course_controller.manage_scores()

@app.get("/api/scores")
@login_required
def api_get_scores():
    """API lấy danh sách điểm"""
    if session.get("role") != "teacher":
        abort(403)
    return course_controller.api_get_scores()

@app.get("/api/scores/user-details")
@login_required
def api_get_user_exam_details():
    """API lấy chi tiết các lần làm bài của user (luôn trả JSON, có fallback)."""
    if session.get("role") != "teacher":
        abort(403)

    # Lấy tham số để fallback khi cần
    uid = request.args.get("user_id", type=int)
    cid = request.args.get("course_id", type=int)

    # 1) Thử gọi controller như cũ
    try:
        out = course_controller.api_get_user_exam_details()
        # Nếu controller đã trả Response JSON -> trả nguyên
        if hasattr(out, "headers") and "application/json" in (out.headers.get("Content-Type", "")).lower():
            return out
        # Nếu controller trả dict/list -> chuẩn hóa thành JSON
        if isinstance(out, dict):
            return jsonify(out)
        if isinstance(out, list):
            return jsonify({"ok": True, "details": out})
        # Nếu là Response nhưng không phải JSON (có thể là HTML) -> rơi xuống fallback
    except Exception as e:
        current_app.logger.exception("api_get_user_exam_details controller failed: %s", e)

    # 2) Fallback: gọi model trực tiếp để bảo đảm có JSON
    try:
        details = course_controller.course_model.get_user_exam_details(uid, cid)
        return jsonify({"ok": True, "details": details})
    except Exception as e2:
        current_app.logger.exception("api_get_user_exam_details model fallback failed: %s", e2)
        return jsonify({"ok": False, "error": str(e2)}), 500


@app.post("/api/scores/update")
@login_required
def api_update_score():
    """API cập nhật điểm"""
    if session.get("role") != "teacher":
        abort(403)
    return course_controller.api_update_score()

@app.post("/api/scores/delete")
@login_required
def api_delete_score():
    """API xóa điểm"""
    if session.get("role") != "teacher":
        abort(403)
    return course_controller.api_delete_score()

@app.get("/api/check-login")
def api_check_login():
    """Simple endpoint to check if user is logged in"""
    if "username" in session:
        return jsonify({"ok": True, "username": session.get("username"), "role": session.get("role")})
    else:
        return jsonify({"ok": False}), 401

@app.post("/api/test-convert-doc-to-video")
def api_test_convert_doc_to_video():
    """Test endpoint without login requirement"""
    return course_controller.api_doc_to_video()


# ---- AI Monitoring for Teachers ----
@app.route("/ai-dashboard")
@login_required
def ai_dashboard():
    if session.get("role") != "teacher":
        abort(403)
    return course_controller.ai_dashboard()

@app.get("/api/ai/progress")
@login_required
def api_ai_progress():
    if session.get("role") != "teacher":
        abort(403)
    return course_controller.api_ai_progress()

@app.get("/api/ai/cheating-incidents")
@login_required
def api_ai_cheating_incidents():
    """API lấy danh sách chi tiết các sự kiện gian lận"""
    if session.get("role") != "teacher":
        abort(403)
    course_id = request.args.get("course_id", type=int)
    user_id = request.args.get("user_id", type=int)
    limit = request.args.get("limit", type=int, default=100)
    
    incidents = course_controller.course_model.get_cheating_incidents(
        course_id=course_id,
        user_id=user_id,
        limit=limit
    )
    return jsonify({"ok": True, "incidents": incidents, "count": len(incidents)})

@app.route("/cheat_screenshots/<path:filename>")
@login_required
def serve_cheat_screenshot(filename):
    """Serve screenshot files từ thư mục cheat_screenshots"""
    if session.get("role") != "teacher":
        abort(403)
    from flask import send_from_directory
    import os
    screenshot_dir = os.path.join(os.getcwd(), CHEAT_SCREENSHOT_ROOT)
    return send_from_directory(screenshot_dir, filename)

# --- Proctoring (camera/face) ---

@app.post("/api/exam/verify-face")
@login_required
def api_exam_verify_face():
    from flask import request, jsonify
    import base64
    from services.face_recognition_service import get_face_recognition_service

    p = request.get_json(force=True) or {}
    frame = p.get("image_base64") or p.get("image") or p.get("frame")
    if not frame:
        return jsonify({"ok": False, "error": "missing image"}), 400

    # Decode base64
    if isinstance(frame, str):
        s = frame.split(",", 1)[-1].strip()
        try:
            img_bytes = base64.b64decode(s, validate=False)
        except Exception as e:
            return jsonify({"ok": False, "error": f"bad base64: {e}"}), 400
    else:
        return jsonify({"ok": False, "error": "unsupported payload"}), 400

    svc = get_face_recognition_service()
    if not svc.is_available():
        return jsonify({"ok": False, "error": "face backend unavailable"}), 503

    # Chỉ lấy face_count (KHÔNG phán đoán vật thể ở bước verify)
    res = svc.detect_faces_and_objects(img_bytes) or {}
    faces = int(res.get("face_count") or 0)

    # Bước verify chỉ quyết định theo khuôn mặt:
    # - >1 mặt: fail
    # - =0 mặt: cảnh báo nhẹ
    # - =1 mặt: pass (chưa đối chiếu avatar ở đây)
    return jsonify({
        "ok": True,
        "face_count": faces,
        "verified": (faces == 1),
        "cheating_detected": False,     # ❗KHÔNG gắn cờ vật thể ở bước verify
        "cheating_reason": None,
        "suspicious_objects": []        # mask sạch để FE không dừng bài
    })


def _coerce_frame_to_bytes(frame):
    if frame is None:
        return None
    if isinstance(frame, (bytes, bytearray)):
        return bytes(frame)
    if isinstance(frame, str):
        s = frame.split(",", 1)[-1].strip()
        try:
            import base64
            return base64.b64decode(s, validate=False)
        except Exception:
            return None
    if isinstance(frame, list):
        try:
            return bytes(bytearray(frame))
        except Exception:
            return None
    return None

@app.post("/api/exam/capture-frame")
def api_capture_frame_unified():
    from services.face_recognition_service import get_face_recognition_service
    from flask import current_app
    data = request.get_json(silent=True) or {}
    frame = data.get("frame") or data.get("image") or data.get("image_base64")
    img_bytes = _coerce_frame_to_bytes(frame)
    if not img_bytes:
        return jsonify({"ok": False, "error": "Bad frame payload (expected bytes/base64/list[int])"}), 400

    FR = get_face_recognition_service()
    out = FR.detect_faces_and_objects(img_bytes)

    # ---- COPY lớp policy từ /api/proctor/analyze để có ui_action ----
    att = float(out.get("attention_score", 0.0) or 0.0)
    out["attention_pct"] = int(round(att * 100))

    val = out.get("attention_score_smooth", None)
    try:
        out["attention_pct_smooth"] = int(round(float(val) * 100))
    except (TypeError, ValueError):
        # fallback nếu None/không phải số
        out["attention_pct_smooth"] = out["attention_pct"]

    import os
    armed = bool(out.get("armed"))
    policy_level = (out.get("policy_level") or ("monitor" if armed else "warmup")).lower()
    mask_before_arm = (os.getenv("MASK_OBJECTS_BEFORE_ARM","1").lower() in ("1","true","yes","on"))

    if (not armed) or policy_level == "warmup":
        out["suspicious_objects"] = []
        out["suspicious_count"] = 0
        out["attention_alert"] = False
        out["should_warn"] = False
        out["should_block"] = False
        out["face_count"] = min(1, int(out.get("face_count") or 0))
        if mask_before_arm:
            cheat_alias = {
                "cell phone","phone","mobile phone","smartphone",
                "laptop","notebook","tablet","book","paper","sheet of paper",
                "keyboard","mouse","remote","monitor","tv","rectangular_device_or_paper"
            }
            filtered = []
            for o in (out.get("objects") or []):
                name = (o.get("type") or o.get("label") or "").lower()
                if name in cheat_alias: continue
                filtered.append(o)
            out["objects"] = filtered
            out["object_count"] = len(filtered)
        ui_action = "none"
    else:
        ui_action = "block" if out.get("should_block") else ("warn" if out.get("should_warn") else "none")

    out["ui_action"] = ui_action
    out.setdefault("policy", {}).update({"level": policy_level, "armed": armed})
    import time as _t
    session["last_proctor"] = {
        "t": _t.time(),
        "armed": bool(out.get("armed")),
        "policy_level": out.get("policy_level"),
        "ui_action": out.get("ui_action"),
        "should_warn": bool(out.get("should_warn")),
        "should_block": bool(out.get("should_block")),
        "suspicious_count": int(out.get("suspicious_count") or 0),
        "cheating_detected": bool(out.get("cheating_detected")),
    }
    if out.get("armed") and not session.get("server_armed_since"):
        session["server_armed_since"] = _t.time()
    
    # TỰ ĐỘNG CHỤP MÀN HÌNH cho TẤT CẢ các trường hợp có dấu hiệu gian lận
    should_capture_frame = (
        out.get("cheating_detected") or 
        out.get("should_block") or 
        out.get("should_warn") or 
        (int(out.get("suspicious_count") or 0) > 0)
    )
    
    if should_capture_frame:
        try:
            username = session.get("username") or str(session.get("user", {}).get("id", "unknown"))
            cheating_reason = out.get("cheating_reason") or "cheating_detected"
            
            # Sử dụng img_bytes đã có sẵn
            if img_bytes:
                import numpy as np
                nparr = np.frombuffer(img_bytes, np.uint8)
                frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame_bgr is not None and frame_bgr.size > 0:
                    screenshot_path = save_cheat_frame(frame_bgr, username, cheating_reason)
                    out["screenshot_path"] = screenshot_path
                    out["screenshot_saved"] = True
                    if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
                        current_app.logger.info(
                            f"[AUTO-CAPTURE] Saved cheat screenshot: {screenshot_path} | "
                            f"Reason: {cheating_reason} | User: {username}"
                        )
        except Exception as capture_err:
            if os.getenv("AI_DEBUG", "0").lower() in ("1", "true", "yes", "on"):
                current_app.logger.warning(f"[AUTO-CAPTURE] Error in capture-frame: {capture_err}")

    return jsonify({"ok": True, "result": out})



if __name__ == "__main__":
    app.run(debug=True)
