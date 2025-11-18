# controller/course_controller.py (patched)
from flask import request, render_template, redirect, url_for, current_app, session, jsonify, json, abort
from werkzeug.utils import secure_filename
import os, shutil
import uuid, time
import unicodedata
import re, random, hmac, hashlib
from collections.abc import Mapping
from model.course_model import CourseModel
from model.user_model import UserModel
from typing import Optional, Tuple, List
from ai_gemini import mcq_from_snippet, keywords_from_snippet, grade_free_text
from services.camera_capture_service import get_camera_capture_service

# Try to import video_script_quiz_service, fallback if not available
try:
    from video_script_quiz_service import video_script_quiz_service
except ImportError:
    video_script_quiz_service = None

# ---------- Aliases ----------
FIELD_ALIASES = {
    "id":          ["id", "course_id", "ID", "Id", "CourseId"],
    "title":       ["title", "name", "course_name", "Title", "Name", "CourseName"],
    "description": ["description", "short_description", "desc", "summary", "Description", "Summary"],
    "category":    ["category", "cate", "topic", "subject", "Category", "Topic", "Subject"],
    "tags":        ["tags", "tag", "keywords", "key_words", "Tags", "Keywords"],
}

FFMPEG_BIN = os.environ.get(
    "FFMPEG_BIN",
    r"C:\Users\FPTSHOP\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"
)

MAX_TIME_MS = 5000
TARGET_TOPICS_DEFAULT = 20  # 20 câu hỏi

# RAM caches
QA_CACHE = {}         # qid -> {..., cue_text, topic_hash}
ATTEMPT_CACHE = {}    # attempt_id -> {...}

SEVERE_EVENTS = {
    'terminated', 'cheat', 'window_blur', 'page_hide',
    'multiple_faces', 'multiple_faces_detected',
    'suspicious_objects', 'camera_denied',
    'face_mismatch', 'face_monitoring_failed'
}

SEVERE_REASONS = {
    'suspicious_objects','multiple_faces','page_hide','window_blur',
    'face_mismatch','face_monitoring_failed','camera_denied'
}

ATTEMPT_CACHE = {}  
EXAM_RESULTS_CACHE = {}

def ensure_ffmpeg_in_path():
    if shutil.which("ffmpeg"):
        return
    ff = FFMPEG_BIN
    if ff and os.path.isfile(ff):
        ff_dir = os.path.dirname(ff)
        os.environ["PATH"] = os.environ.get("PATH", "") + (os.pathsep + ff_dir)

def _fmt_ts(sec: float) -> str:
    if sec < 0:
        sec = 0
    ms = int(round((sec - int(sec)) * 1000))
    s  = int(sec)
    h  = s // 3600
    m  = (s % 3600) // 60
    s  = (s % 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def _write_vtt_from_segments(segments, outpath: str) -> None:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _fmt_ts(float(seg["start"]))
        end   = _fmt_ts(float(seg["end"]))
        text  = (seg.get("text") or "").strip()
        if text:
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def _hmac_secret():
    try:
        from flask import current_app
        sk = (current_app.config.get("SECRET_KEY") or "dev-secret").encode("utf-8")
    except Exception:
        sk = b"dev-secret"
    return sk

def _hash_option(text: str) -> str:
    # Sử dụng hash function dùng chung từ utils để đảm bảo consistency
    try:
        from utils.hash_utils import hash_option as shared_hash_option
        return shared_hash_option(text)
    except ImportError:
        # Fallback nếu utils module không có
        return hmac.new(_hmac_secret(), (text or "").encode("utf-8"), hashlib.sha256).hexdigest()[:16]

def _get_user_id():
    u = session.get("user") or {}
    return u.get("id") or u.get("user_id") or 0

def _parse_vtt(path: str):
    cues, buf, ts = [], [], None
    if not path or not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if "-->" in line and ":" in line:
                ts = line
            elif line.strip() == "":
                if ts and buf:
                    cues.append({"ts": ts, "text": " ".join(buf).strip()})
                buf, ts = [], None
            else:
                if not line.upper().startswith("WEBVTT"):
                    buf.append(line.strip())
        if ts and buf:
            cues.append({"ts": ts, "text": " ".join(buf).strip()})
    return [c for c in cues if len(c["text"].split()) >= 4]

def _parse_vtt_with_timestamps(path: str):
    """
    Parse VTT file và trả về cues với timestamp (start, end) dưới dạng số giây
    """
    cues = []
    buf, ts_line = [], None
    if not path or not os.path.exists(path):
        return []
    
    def _vtt_time_to_seconds(time_str: str) -> float:
        """Chuyển đổi VTT timestamp (HH:MM:SS.mmm) thành số giây"""
        try:
            # Format: 00:01:23.456 hoặc 01:23.456
            time_str = time_str.strip()
            if "." in time_str:
                time_part, ms_part = time_str.split(".", 1)
                ms = float("0." + ms_part)
            else:
                time_part = time_str
                ms = 0.0
            
            parts = time_part.split(":")
            if len(parts) == 3:
                h, m, s = map(int, parts)
                return h * 3600 + m * 60 + s + ms
            elif len(parts) == 2:
                m, s = map(int, parts)
                return m * 60 + s + ms
            else:
                return float(time_part)
        except Exception:
            return 0.0
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n")
            if "-->" in line and ":" in line:
                ts_line = line
            elif line.strip() == "":
                if ts_line and buf:
                    # Parse timestamp: "00:01:23.456 --> 00:01:25.789"
                    try:
                        times = ts_line.split("-->")
                        if len(times) == 2:
                            start_time = _vtt_time_to_seconds(times[0].strip())
                            end_time = _vtt_time_to_seconds(times[1].strip())
                            text = " ".join(buf).strip()
                            if text and len(text.split()) >= 3:
                                cues.append({
                                    "start": start_time,
                                    "end": end_time,
                                    "text": text,
                                    "ts": ts_line
                                })
                    except Exception as e:
                        print(f"[WARN] Error parsing timestamp '{ts_line}': {e}")
                buf, ts_line = [], None
            else:
                if not line.upper().startswith("WEBVTT"):
                    buf.append(line.strip())
        if ts_line and buf:
            try:
                times = ts_line.split("-->")
                if len(times) == 2:
                    start_time = _vtt_time_to_seconds(times[0].strip())
                    end_time = _vtt_time_to_seconds(times[1].strip())
                    text = " ".join(buf).strip()
                    if text and len(text.split()) >= 3:
                        cues.append({
                            "start": start_time,
                            "end": end_time,
                            "text": text,
                            "ts": ts_line
                        })
            except Exception as e:
                print(f"[WARN] Error parsing final timestamp '{ts_line}': {e}")
    
    return cues

def _get_text_for_segment(cues: list, segment_start: float, segment_end: float) -> str:
    """
    Lấy text từ VTT cues trong khoảng thời gian segment
    """
    texts = []
    for cue in cues:
        # Kiểm tra nếu cue overlap với segment
        if cue["end"] > segment_start and cue["start"] < segment_end:
            texts.append(cue["text"])
    return " ".join(texts).strip()

def _strip_diacritics(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")

def _norm_text(s: str) -> str:
    s = _strip_diacritics((s or "").lower())
    out = []
    for ch in s:
        out.append(ch if ch.isalnum() or ch.isspace() or ch in "+#" else " ")
    return " ".join("".join(out).split())

def _slugify_label(value: str, fallback: str) -> str:
    base = _norm_text(value)
    if not base:
        base = _norm_text(fallback)
    base = base.replace("#", " ").strip()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    base = re.sub(r"-{2,}", "-", base).strip("-")
    if not base:
        base = fallback.lower()
    return base[:60]

def _get_attr_any(obj, name):
    cand = {name, name.lower(), name.replace("-", "_"), name.replace(" ", "_"),
            name.lower().replace("-", "_").replace(" ", "_")}
    for n in cand:
        if hasattr(obj, n):
            return getattr(obj, n)
    return None

def _get_field(obj, key: str, join_lists: bool = True) -> str:
    if obj is None:
        return ""
    aliases = FIELD_ALIASES.get(key, [key])

    if isinstance(obj, Mapping):
        lower_keys = {str(k).lower(): k for k in obj.keys()}
        for a in aliases:
            lk = a.lower()
            if lk in lower_keys:
                v = obj.get(lower_keys[lk])
                if join_lists and isinstance(v, (list, tuple, set)):
                    return " ".join(str(x) for x in v if x is not None)
                return "" if v is None else str(v)

    for a in aliases:
        v = _get_attr_any(obj, a)
        if v is not None:
            if join_lists and isinstance(v, (list, tuple, set)):
                return " ".join(str(x) for x in v if x is not None)
            return "" if v is None else str(v)

    return ""

def _course_id(course):
    aliases = FIELD_ALIASES["id"]
    if isinstance(course, Mapping):
        lower_keys = {str(k).lower(): k for k in course.keys()}
        for a in aliases:
            if a.lower() in lower_keys:
                v = course[lower_keys[a.lower()]]
                if v not in (None, ""):
                    return v
    for a in aliases:
        v = _get_attr_any(course, a)
        if v not in (None, ""):
            return v
    return None

def _is_all_category(val: str) -> bool:
    t = _norm_text(val)
    return t in ("", "all", "tat ca the loai", "all categories", "all category")

def _haystack(course) -> str:
    return _norm_text(" ".join([
        _get_field(course, "title"),
        _get_field(course, "description"),
        _get_field(course, "category"),
        _get_field(course, "tags"),
    ]))

def _filter_courses(courses: list, q: str, category: str) -> list:
    q_norm   = _norm_text(q)
    terms    = [t for t in q_norm.split() if t] if q_norm else []

    cat_norm = None if _is_all_category(category) else _norm_text(category)

    out = []
    for c in courses:
        if cat_norm:
            c_cat = _norm_text(_get_field(c, "category"))
            if not c_cat or cat_norm not in c_cat:
                continue

        if terms:
            hay = _haystack(c)
            if not hay:
                continue
            pad = f" {hay} "
            if not all(f" {t} " in pad for t in terms):
                continue

        out.append(c)
    return out

def _url_to_local_path(url_path: str) -> Optional[str]:
    """
    Chuyển đổi URL (full hoặc relative) thành local file path
    - Full URL: http://127.0.0.1:5000/static/uploads/file.mp4 -> static/uploads/file.mp4
    - Relative URL: /static/uploads/file.mp4 -> static/uploads/file.mp4
    """
    if not url_path:
        return None
    
    # Loại bỏ query string
    url_path = url_path.split("?", 1)[0]
    
    # Nếu là full URL (có protocol), extract path
    if "://" in url_path:
        # Parse: http://host:port/path -> /path
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url_path)
            url_path = parsed.path
        except Exception:
            # Fallback: tìm sau domain
            if "/" in url_path:
                parts = url_path.split("/", 3)
                if len(parts) >= 4:
                    url_path = "/" + parts[3]
                elif len(parts) >= 3:
                    url_path = "/" + parts[2]
    
    # Loại bỏ leading slash để có relative path
    return url_path.lstrip("/")

def _guess_alias_stems(basename: str) -> List[str]:
    name, _ = os.path.splitext(basename)
    parts = name.split("_")
    out = [name]
    if len(parts) > 1 and (len(parts[0]) in (32, 36)):
        out.append("_".join(parts[1:]))
    out.append(parts[-1])
    seen, uniq = set(), []
    for s in out:
        if s not in seen:
            seen.add(s); uniq.append(s)
    return uniq

def _ensure_caption_files(video_url: str, course_id) -> Tuple[Optional[str], Optional[str]]:
    if not video_url:
        return (None, None)
    vpath = _url_to_local_path(video_url)
    if not vpath or not os.path.exists(vpath):
        return (None, None)

    # ƯU TIÊN: Tìm VTT file theo đúng tên video (không share transcript giữa các video)
    # Video: {uuid}_{filename}_video.mp4 -> VTT: {uuid}_{filename}.vtt
    stem, _ = os.path.splitext(vpath)
    # Loại bỏ "_video" suffix nếu có để match với VTT file
    if stem.endswith("_video"):
        stem = stem[:-6]
    
    # CHỈ TÌM VTT FILE THEO VIDEO URL - KHÔNG DÙNG COURSE_ID ĐỂ TRÁNH NHẦM TRANSCRIPT
    # Mỗi video phải có VTT file riêng theo naming: {uuid}_{filename}.vtt
    candidates: List[str] = [
        stem + ".vtt",  # {uuid}_{filename}.vtt
        stem + ".srt"   # {uuid}_{filename}.srt
    ]
    
    # LOẠI BỎ: Priority 2 (alias) và Priority 3 (course-specific) 
    # để đảm bảo mỗi video chỉ dùng transcript của chính nó

    for p in candidates:
        p = p.replace("\\", "/")
        if os.path.exists(p):
            if p.endswith(".srt"):
                vtt_out = p[:-4] + ".vtt"
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    s = f.read()
                s = re.sub(r"(?m)^\s*\d+\s*\n", "", s)
                s = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", s)
                if not s.lstrip().upper().startswith("WEBVTT"):
                    s = "WEBVTT\n\n" + s
                os.makedirs(os.path.dirname(vtt_out), exist_ok=True)
                with open(vtt_out, "w", encoding="utf-8") as f:
                    f.write(s)
                p = vtt_out
            return ("/" + p.replace(os.sep, "/"), p)

    return (None, None)

def _topic_hash(text: str) -> str:
    return hashlib.sha1((_norm_text(text) or "").encode("utf-8")).hexdigest()[:16]

def _create_alternative_question_course(text: str, qtype: str, difficulty: str, attempt: int = 0) -> dict:
    """Tạo câu hỏi thay thế khi phát hiện lặp trong course_controller"""
    if qtype == "mcq":
        # Tạo câu hỏi MCQ khác
        words = [w.strip(",.?!:;()[]\"'") for w in (text or "").split()]
        picks = [w for w in words if len(_strip_diacritics(w)) >= 4] or words or ["noi_dung"]
        key = random.choice(picks)
        q_sentence = (text or "").replace(key, "_____", 1)
        
        # Tạo câu hỏi với cách diễn đạt khác
        try:
            from question_diversity_manager import diversity_manager
            if diversity_manager:
                selected_question = diversity_manager.get_alternative_question_variation(q_sentence, "mcq", attempt)
            else:
                raise ImportError
        except:
            question_variations = [
                f"Điền từ còn thiếu trong câu sau (trích bài giảng): \"{q_sentence}\".",
                f"Chọn từ phù hợp để hoàn thành câu: \"{q_sentence}\".",
                f"Từ nào thích hợp nhất để điền vào chỗ trống: \"{q_sentence}\"?"
            ]
            selected_question = question_variations[(hash(text) + attempt) % len(question_variations)]
        
        # Tạo distractors khác
        pool = {w.strip(",.?!:;()[]\"'") for w in (text or "").split()
                if len(_strip_diacritics(w.strip(",.?!:;()[]\"'"))) >= 4 and
                   w.strip(",.?!:;()[]\"'").lower() != key.lower()}
        distractors = (random.sample(list(pool), k=min(3, len(pool))) if pool else ["không", "biết", "được"])
        options = [key] + distractors[:3]
        random.SystemRandom().shuffle(options)
        options_hashes = [_hash_option(o) for o in options]
        ci = options.index(key)
        return {
            "type": "mcq",
            "question": selected_question,
            "options": options, "options_hashes": options_hashes,
            "correct_index": ci, "correct_hash": options_hashes[ci],
            "rubric": None, "time_limit_ms": 5000
        }
    else:
        # Tạo câu hỏi tự luận/vấn đáp khác
        words = [w.strip(",.?!:;()[]\"'") for w in (text or "").split()]
        picks = [w for w in words if len(_strip_diacritics(w)) >= 4] or words
        random.shuffle(picks)
        uniq = []
        for w in picks:
            nw = _norm_text(w)
            if nw and nw not in uniq:
                uniq.append(nw)
            if len(uniq) >= 5:
                break
        if not uniq:
            uniq = [_norm_text(words[0])] if words else ["noi dung"]
        
        # Tạo câu hỏi với cách diễn đạt khác
        try:
            from question_diversity_manager import diversity_manager
            if diversity_manager:
                selected_question = diversity_manager.get_alternative_question_variation(', '.join(uniq), qtype, attempt)
            else:
                raise ImportError
        except:
            if qtype == "essay":
                question_variations = [
                    f"Tự luận ngắn: Trình bày nội dung trọng tâm, ưu tiên các ý: {', '.join(uniq)}.",
                    f"Viết đoạn văn ngắn về: {', '.join(uniq)}.",
                    f"Phân tích và trình bày các điểm chính: {', '.join(uniq)}."
                ]
            else:  # oral
                question_variations = [
                    f"Vấn đáp: Trả lời ngắn gọn theo các ý: {', '.join(uniq)}.",
                    f"Trả lời miệng về: {', '.join(uniq)}.",
                    f"Thuyết trình ngắn về: {', '.join(uniq)}."
                ]
            
            selected_question = question_variations[(hash(text) + attempt) % len(question_variations)]
        
        return {
            "type": qtype,
            "question": selected_question,
            "options": [], "options_hashes": [],
            "correct_index": None, "correct_hash": None,
            "rubric": {"keywords": uniq, "threshold": max(2, len(uniq)//2)},
            "time_limit_ms": 10000
        }

def generate_qa_from_vtt(*, caption_url: Optional[str], difficulty: str = "easy",
                         similar_to: Optional[str] = None, qtype: Optional[str] = None, session_id: str = None):
    """
    Tạo câu hỏi dựa trên phụ đề VTT. Hỗ trợ MCQ, tự luận, oral.
    Nếu thiếu phụ đề, tạo câu hỏi trạng thái.
    Trả về dict cấu trúc đề, đồng thời cache vào QA_CACHE[qid].
    Sử dụng diversity manager để tránh lặp câu hỏi.
    """
    # Import diversity manager
    try:
        from question_diversity_manager import diversity_manager
    except Exception:
        diversity_manager = None
    
    vtt_path = (caption_url or "").lstrip("/")
    cues = _parse_vtt(vtt_path)

    def _keywords_from_text(text: str, k: int = 5) -> list:
        words = [w.strip(",.?!:;()[]\"'") for w in (text or "").split()]
        picks = [w for w in words if len(_strip_diacritics(w)) >= 4] or words
        random.shuffle(picks)
        uniq = []
        for w in picks:
            nw = _norm_text(w)
            if nw and nw not in uniq:
                uniq.append(nw)
            if len(uniq) >= k:
                break
        if not uniq:
            uniq = [_norm_text(words[0])] if words else ["noi dung"]
        return uniq

    def _build_mcq_local(text: str) -> dict:
        words = [w.strip(",.?!:;()[]\"'") for w in (text or "").split()]
        picks = [w for w in words if len(_strip_diacritics(w)) >= 4] or words or ["noi_dung"]
        key = random.choice(picks)
        q_sentence = (text or "").replace(key, "_____", 1)
        pool = {w.strip(",.?!:;()[]\"'") for c in (cues or []) for w in (c["text"] or "").split()
                if len(_strip_diacritics(w.strip(",.?!:;()[]\"'"))) >= 4 and
                   w.strip(",.?!:;()[]\"'").lower() != key.lower()}
        distractors = (random.sample(list(pool), k=min(3, len(pool))) if pool else ["không", "biết", "được"])
        options = [key] + distractors[:3]
        random.SystemRandom().shuffle(options)
        options_hashes = [_hash_option(o) for o in options]
        ci = options.index(key)
        return {
            "type": "mcq",
            "question": f"Điền từ còn thiếu trong câu sau (trích bài giảng): “{q_sentence}”.",
            "options": options, "options_hashes": options_hashes,
            "correct_index": ci, "correct_hash": options_hashes[ci],
            "rubric": None, "time_limit_ms": 5000
        }

    if not cues:
        qid = str(uuid.uuid4())
        options = ["Video chưa có phụ đề", "Video có phụ đề", "Chưa chắc", "Bỏ qua"]
        random.SystemRandom().shuffle(options)
        options_hashes = [_hash_option(o) for o in options]
        ci = options.index("Video chưa có phụ đề")
        qa = {
            "qid": qid, "difficulty": difficulty, "type": "mcq",
            "question": "Chọn phát biểu đúng về phụ đề của video này.",
            "options": options, "options_hashes": options_hashes,
            "correct_index": ci, "correct_hash": options_hashes[ci],
            "rubric": None, "cue_text": "NO_CAPTION",
            "topic_hash": _topic_hash("NO_CAPTION"),
            "time_limit_ms": 5000
        }
        QA_CACHE[qid] = {k: qa[k] for k in ("correct_hash","options_hashes","difficulty","type","rubric","question","options","cue_text","topic_hash")}
        return qa

    if similar_to and similar_to in QA_CACHE and QA_CACHE[similar_to].get("cue_text"):
        text = QA_CACHE[similar_to]["cue_text"]
    else:
        # Sử dụng diversity manager để chọn text segment đa dạng
        if diversity_manager:
            text = diversity_manager.get_diverse_text_segment(cues, difficulty)
            if not text:
                # Fallback nếu không có text nào
                cues_sorted = sorted(cues, key=lambda c: len(c["text"]), reverse=(difficulty == "hard"))
                pick_pool = cues_sorted[:max(5, len(cues_sorted)//3)] or cues_sorted
                text = random.choice(pick_pool)["text"]
            else:
                # Đánh dấu text đã sử dụng
                diversity_manager.mark_text_segment_used(text)
        else:
            cues_sorted = sorted(cues, key=lambda c: len(c["text"]), reverse=(difficulty == "hard"))
            pick_pool = cues_sorted[:max(5, len(cues_sorted)//3)] or cues_sorted
            text = random.choice(pick_pool)["text"]

    qtype = (qtype or "").lower().strip() or random.choice(["mcq", "essay", "oral"])

    if qtype == "mcq":
        qa_core = None
        try:
            g = mcq_from_snippet(text)
            if g and isinstance(g.get("options"), list) and len(g["options"]) == 4:
                options = list(g["options"])
                correct_text = options[g["correct_index"]]
                random.SystemRandom().shuffle(options)
                if correct_text not in options:
                    options[0] = correct_text
                options_hashes = [_hash_option(o) for o in options]
                ci = options.index(correct_text)
                qa_core = {
                    "type": "mcq",
                    "question": g.get("question") or f"Câu hỏi dựa trên đoạn: “{text}”.",
                    "options": options, "options_hashes": options_hashes,
                    "correct_index": ci, "correct_hash": options_hashes[ci],
                    "rubric": None, "time_limit_ms": 5000
                }
        except Exception:
            qa_core = None
        if not qa_core:
            qa_core = _build_mcq_local(text)
    else:
        try:
            kws = keywords_from_snippet(text, k=5)
        except Exception:
            kws = None
        if not kws:
            kws = _keywords_from_text(text, k=5)
        qa_core = {
            "type": qtype,
            "question": (f"Tự luận ngắn: Trình bày nội dung trọng tâm, ưu tiên các ý: {', '.join(kws)}."
                         if qtype == "essay"
                         else f"Vấn đáp: Trả lời ngắn gọn theo các ý: {', '.join(kws)}."),
            "options": [], "options_hashes": [],
            "correct_index": None, "correct_hash": None,
            "rubric": {"keywords": kws, "threshold": max(2, len(kws)//2)},
            "time_limit_ms": 10000
        }

    # Kiểm tra hash câu hỏi để tránh lặp
    if diversity_manager and session_id:
        # Check if session should be reset
        if diversity_manager.should_reset_session(session_id):
            diversity_manager.reset_session(session_id)
        
        # Check for similar content
        if diversity_manager.is_question_content_similar(qa_core.get("question", ""), session_id):
            attempt = diversity_manager.get_next_alternative_count(session_id)
            qa_core = _create_alternative_question_course(text, qtype, difficulty, attempt)
        
        q_hash = diversity_manager.generate_question_hash(text, qa_core.get("question", ""), qtype, "general")
        if diversity_manager.is_question_recently_asked(q_hash, session_id):
            # Tạo câu hỏi thay thế
            attempt = diversity_manager.get_next_alternative_count(session_id)
            qa_core = _create_alternative_question_course(text, qtype, difficulty, attempt)
        diversity_manager.mark_question_asked(q_hash, session_id, qa_core.get("question", ""))

    qid = str(uuid.uuid4())
    qa = {
        "qid": qid, "difficulty": difficulty,
        "cue_text": text, "topic_hash": _topic_hash(text),
        **qa_core
    }
    QA_CACHE[qid] = {k: qa.get(k) for k in
                     ("correct_hash","options_hashes","difficulty","type","rubric","question","options","cue_text","topic_hash")}
    return qa

def grade_answer(qid: str, answer):
    meta = QA_CACHE.get(qid) or {}
    ans_hash = str(answer)
    correct = (ans_hash == meta.get("correct_hash"))
    return {"qid": qid, "correct": bool(correct)}

def escalate(verdict: dict) -> str:
    cur = (QA_CACHE.get(verdict.get("qid")) or {}).get("difficulty", "easy")
    order = ["easy", "medium", "hard"]
    if verdict.get("correct"):
        i = min(order.index(cur) + 1, len(order) - 1)
        return order[i]
    return cur


class CourseController:
    def __init__(self):
        ensure_ffmpeg_in_path()
        self.course_model = CourseModel()
        self.user_model = UserModel()

    def home(self):
        courses = self.course_model.get_all_courses()
        return render_template("home.html", courses=courses, username=session.get("username"))

    def list_courses(self):
        all_courses = self.course_model.get_all_courses()

        # Chuẩn hóa dữ liệu về dict để dùng chung các helper (.get, FIELD_ALIASES, ...)
        normalized_courses = []
        for course in all_courses or []:
            if isinstance(course, Mapping):
                try:
                    normalized_courses.append(dict(course))
                    continue
                except Exception:
                    pass
            try:
                normalized_courses.append(dict(course))
            except Exception:
                normalized_courses.append(course)
        all_courses = normalized_courses

        q = (request.args.get("q") or "").strip()
        category = (request.args.get("category") or "").strip()
        prefer_exact = (request.args.get("prefer", "").lower() == "exact")
        open_single = (request.args.get("openSingle", "").lower() in ("1", "true", "yes", "y", "on"))

        filtered = _filter_courses(all_courses, q=q, category=category)

        if prefer_exact and q:
            q_norm = _norm_text(q)
            def title_norm(c): return _norm_text(_get_field(c, "title"))
            exact = [c for c in filtered if title_norm(c) == q_norm]
            if len(exact) == 1:
                cid = _course_id(exact[0])
                if cid is not None:
                    return redirect(url_for("course_detail", course_id=cid), code=302)
            starts = [c for c in filtered if title_norm(c).startswith(q_norm)]
            if len(starts) == 1:
                cid = _course_id(starts[0])
                if cid is not None:
                    return redirect(url_for("course_detail", course_id=cid), code=302)

        if open_single and len(filtered) == 1:
            cid = _course_id(filtered[0])
            if cid is not None:
                return redirect(url_for("course_detail", course_id=cid), code=302)

        return render_template("course_list_search.html",
                               courses=filtered,
                               username=session.get("username"),
                               q=q, category=category, total=len(filtered))

    def course_detail(self, course_id):
        course = self.course_model.get_course_by_id(course_id)
        if not course:
            return redirect(url_for("course"))
        try:
            course = {k: course[k] for k in course.keys()}
        except Exception:
            pass

        video_url   = course.get("video_url")
        caption_url = (course.get("caption_url") or None)

        # QUAN TRỌNG: Chỉ tìm VTT file nếu chưa có caption_url trong DB
        # Và chỉ tìm theo video URL (không dùng course_id để tránh nhầm transcript)
        if not caption_url and video_url:
            # Tìm VTT file theo đúng tên video (không dùng course_id)
            vpath = _url_to_local_path(video_url)
            if vpath and os.path.exists(vpath):
                stem, _ = os.path.splitext(vpath)
                # Loại bỏ "_video" suffix nếu có
                if stem.endswith("_video"):
                    stem = stem[:-6]
                potential_vtt = stem + ".vtt"
                if os.path.exists(potential_vtt):
                    detected_url = "/" + potential_vtt.replace(os.sep, "/").lstrip("/")
                    caption_url = detected_url
                    self.course_model.update_course(
                        course_id,
                        course.get("title"),
                        course.get("description") or "",
                        course.get("image_url"),
                        video_url,
                        caption_url,
                        course.get("category"),
                        course.get("tags"),
                    )
                    course["caption_url"] = caption_url

        sections = self.course_model.get_outline(course_id)
        user     = session.get("user") or {}
        user_id  = user.get("id") or user.get("user_id")
        progress = self.course_model.get_user_progress(course_id, user_id) if user_id else {}
        related  = self.course_model.get_related_by_category(course.get("category"), course_id)

        return render_template(
            "course_detail.html",
            course=course,
            sections=sections,
            progress=progress,
            related_courses=related
        )

    def generate_caption(self, course_id: int, lang: str = "en"):
        course = self.course_model.get_course_by_id(course_id)
        if not course:
            return jsonify({"ok": False, "error": "Course not found"}), 404
        try:
            course = {k: course[k] for k in course.keys()}
        except Exception:
            pass

        video_url = course.get("video_url")
        if not video_url:
            return jsonify({"ok": False, "error": "Missing video_url"}), 400

        vpath = _url_to_local_path(video_url)
        print(f"[DEBUG] generate_caption: video_url={video_url}, vpath={vpath}, exists={os.path.exists(vpath) if vpath else False}")
        if not vpath:
            return jsonify({"ok": False, "error": f"Invalid video_url: {video_url}"}), 400
        if not os.path.exists(vpath):
            return jsonify({"ok": False, "error": f"Video file not found: {vpath} (from URL: {video_url})"}), 400

        try:
            import whisper
            model = whisper.load_model("small")
            result = model.transcribe(vpath, language=lang, task="transcribe", fp16=False)
        except ImportError:
            return jsonify({
                "ok": False, 
                "error": "Whisper module not installed. Please install: pip install openai-whisper"
            }), 500
        except Exception as e:
            return jsonify({"ok": False, "error": f"Whisper failed: {e}"}), 500

        outdir = os.path.join("static", "captions")
        outpath = os.path.join(outdir, f"{course_id}.vtt")
        try:
            _write_vtt_from_segments(result.get("segments", []), outpath)
        except Exception as e:
            return jsonify({"ok": False, "error": f"Write VTT failed: {e}"}), 500

        caption_url = "/" + outpath.replace(os.sep, "/")

        try:
            self.course_model.update_course(
                course_id,
                course.get("title"),
                course.get("description") or "",
                course.get("image_url"),
                video_url,
                caption_url,
                course.get("category"),
                course.get("tags"),
            )
        except Exception as e:
            return jsonify({"ok": False, "error": f"DB update failed: {e}"}), 500

        return jsonify({"ok": True, "caption_url": caption_url})

    def api_captions_auto(self):
        """
        POST /api/captions/auto
        Body JSON: { video_url, course_id, language?, force? }
        Tự động tạo hoặc lấy caption cho video.
        - Nếu video từ doc-to-video đã có VTT, sử dụng nó
        - Nếu không, tạo bằng Whisper
        """
        try:
            data = request.get_json(force=True) or {}
            video_url = data.get("video_url") or ""
            course_id = data.get("course_id")
            language = data.get("language") or "en"
            force = data.get("force", False)
            
            print(f"[DEBUG] api_captions_auto called: video_url={video_url}, course_id={course_id}, force={force}")
            
            if not video_url:
                return jsonify({"ok": False, "error": "Missing video_url"}), 400
            
            if not course_id:
                return jsonify({"ok": False, "error": "Missing course_id"}), 400
            
            # Lấy course hiện tại
            course = self.course_model.get_course_by_id(course_id)
            if not course:
                return jsonify({"ok": False, "error": "Course not found"}), 404

            try:
                course = {k: course[k] for k in course.keys()}
            except Exception:
                pass
            
            # Nếu đã có caption_url và không force, trả về ngay
            existing_caption = course.get("caption_url") or ""
            if existing_caption and not force:
                # Kiểm tra file có tồn tại không
                caption_path = _url_to_local_path(existing_caption)
                if caption_path and os.path.exists(caption_path):
                    return jsonify({"ok": True, "caption_url": existing_caption})
            
            # 1) Kiểm tra xem video có VTT file cùng tên không (từ doc-to-video)
            vpath = _url_to_local_path(video_url)
            print(f"[DEBUG] api_captions_auto: video_url={video_url}, vpath={vpath}, exists={os.path.exists(vpath) if vpath else False}")
            if not vpath:
                return jsonify({"ok": False, "error": f"Invalid video_url: {video_url}"}), 400
            if not os.path.exists(vpath):
                return jsonify({"ok": False, "error": f"Video file not found: {vpath} (from URL: {video_url})"}), 400
            
            # Tìm VTT file cùng thư mục và cùng tên
            # Video có thể là: {uuid}_{filename}_video.mp4 -> VTT là: {uuid}_{filename}.vtt
            video_dir = os.path.dirname(vpath)
            video_base = os.path.splitext(os.path.basename(vpath))[0]
            # Loại bỏ "_video" suffix nếu có (để match với VTT file)
            if video_base.endswith("_video"):
                video_base = video_base[:-6]  # Remove "_video"
            potential_vtt = os.path.join(video_dir, f"{video_base}.vtt")
            
            if os.path.exists(potential_vtt):
                # Video đã có VTT từ doc-to-video
                caption_url = "/" + potential_vtt.replace(os.sep, "/").lstrip("/")
                try:
                    self.course_model.update_course(
                        course_id,
                        course.get("title"),
                        course.get("description") or "",
                        course.get("image_url"),
                        video_url,
                        caption_url,
                        course.get("category"),
                        course.get("tags"),
                    )
                    return jsonify({"ok": True, "caption_url": caption_url})
                except Exception as e:
                    print(f"[ERROR] DB update failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return jsonify({"ok": False, "error": f"DB update failed: {e}"}), 500
            
            # 2) Nếu không có VTT sẵn, tạo bằng Whisper (giống generate_caption)
            try:
                import whisper
                print(f"[WHISPER] Loading model 'small' for transcription...")
                model = whisper.load_model("small")
                print(f"[WHISPER] Transcribing video: {vpath}")
                result = model.transcribe(vpath, language=language, task="transcribe", fp16=False)
                print(f"[WHISPER] Transcription completed: {len(result.get('segments', []))} segments")
            except ImportError:
                return jsonify({
                    "ok": False, 
                    "error": "Whisper module not installed. Please install: pip install openai-whisper"
                }), 500
            except Exception as e:
                print(f"[ERROR] Whisper failed: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"ok": False, "error": f"Whisper failed: {e}"}), 500

            outdir = os.path.join("static", "captions")
            os.makedirs(outdir, exist_ok=True)
            outpath = os.path.join(outdir, f"{course_id}.vtt")
            try:
                _write_vtt_from_segments(result.get("segments", []), outpath)
                print(f"[VTT] Wrote VTT file: {outpath}")
            except Exception as e:
                print(f"[ERROR] Write VTT failed: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"ok": False, "error": f"Write VTT failed: {e}"}), 500

            caption_url = "/" + outpath.replace(os.sep, "/")

            try:
                self.course_model.update_course(
                    course_id,
                    course.get("title"),
                    course.get("description") or "",
                    course.get("image_url"),
                    video_url,
                    caption_url,
                    course.get("category"),
                    course.get("tags"),
                )
                print(f"[SUCCESS] Caption created and saved: {caption_url}")
            except Exception as e:
                print(f"[ERROR] DB update failed: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"ok": False, "error": f"DB update failed: {e}"}), 500

            return jsonify({"ok": True, "caption_url": caption_url})
        except Exception as e:
            # Catch tất cả exception để tránh 500 Internal Server Error không rõ ràng
            print(f"[ERROR] api_captions_auto exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_captions_status(self):
        """
        GET /api/captions/status?video_url=...
        Kiểm tra xem video đã có caption chưa
        """
        video_url = request.args.get("video_url") or ""
        if not video_url:
            return jsonify({"ok": False, "error": "Missing video_url"}), 400
        
        # 1) Kiểm tra xem video có VTT file cùng tên không (từ doc-to-video)
        # Video có thể là: {uuid}_{filename}_video.mp4 -> VTT là: {uuid}_{filename}.vtt
        vpath = _url_to_local_path(video_url)
        print(f"[DEBUG] api_captions_status: video_url={video_url}, vpath={vpath}, exists={os.path.exists(vpath) if vpath else False}")
        if vpath and os.path.exists(vpath):
            video_dir = os.path.dirname(vpath)
            video_base = os.path.splitext(os.path.basename(vpath))[0]
            # Loại bỏ "_video" suffix nếu có (để match với VTT file)
            if video_base.endswith("_video"):
                video_base = video_base[:-6]  # Remove "_video"
            potential_vtt = os.path.join(video_dir, f"{video_base}.vtt")
            
            if os.path.exists(potential_vtt):
                caption_url = "/" + potential_vtt.replace(os.sep, "/").lstrip("/")
                return jsonify({"ok": True, "exists": True, "caption_url": caption_url})
        
        # 2) Kiểm tra trong DB có course nào có video_url này và đã có caption_url không
        # (Cần query DB - nhưng đơn giản hóa: chỉ trả về exists=False nếu không tìm thấy VTT)
        return jsonify({"ok": True, "exists": False, "caption_url": None})

    def api_generate_segment_questions(self):
        """
        POST /api/segments/generate-questions
        Body JSON: { course_id, force? }
        Pre-generate questions cho tất cả các segment 50s dựa trên transcript
        """
        try:
            data = request.get_json(force=True) or {}
            course_id = data.get("course_id")
            force = data.get("force", False)
            
            if not course_id:
                return jsonify({"ok": False, "error": "Missing course_id"}), 400
            
            course = self.course_model.get_course_by_id(course_id)
            if not course:
                return jsonify({"ok": False, "error": "Course not found"}), 404
            
            try:
                course = {k: course[k] for k in course.keys()}
            except Exception:
                pass
            
            caption_url = course.get("caption_url") or ""
            if not caption_url:
                return jsonify({"ok": False, "error": "Course chưa có transcript. Vui lòng tạo transcript trước."}), 400
            
            # Parse VTT file
            vtt_path = _url_to_local_path(caption_url)
            if not vtt_path or not os.path.exists(vtt_path):
                return jsonify({"ok": False, "error": f"VTT file not found: {vtt_path}"}), 400
            
            print(f"[SEGMENT] Parsing VTT: {vtt_path}")
            cues = _parse_vtt_with_timestamps(vtt_path)
            if not cues:
                return jsonify({"ok": False, "error": "Không thể parse VTT file hoặc VTT file rỗng"}), 400
            
            # Tính tổng thời gian video (từ cue cuối cùng)
            max_time = max(cue["end"] for cue in cues) if cues else 0
            print(f"[SEGMENT] Video duration: {max_time:.2f}s, Total cues: {len(cues)}")
            
            # Xóa câu hỏi cũ nếu force regenerate
            if force:
                self.course_model.delete_segment_questions(course_id)
                print(f"[SEGMENT] Deleted existing questions for course {course_id}")
            
            # Chia thành các segment 50 giây (0-50, 50-100, 100-150, ...)
            segment_size = 50.0
            segments = []
            current_start = 0
            generated_count = 0
            skipped_count = 0
            
            while current_start < max_time:
                segment_end = min(current_start + segment_size, max_time)
                segment_start = int(current_start)
                segment_end_int = int(segment_end)
                
                # Lấy text từ segment này
                segment_text = _get_text_for_segment(cues, current_start, segment_end)
                
                if not segment_text or len(segment_text.strip()) < 20:
                    print(f"[SEGMENT] Segment {segment_start}-{segment_end_int}s: Không đủ nội dung, bỏ qua")
                    skipped_count += 1
                    current_start += segment_size
                    continue
                
                # Kiểm tra xem đã có câu hỏi cho segment này chưa
                existing = self.course_model.get_segment_question(course_id, segment_start)
                if existing and not force:
                    print(f"[SEGMENT] Segment {segment_start}-{segment_end_int}s: Đã có câu hỏi, bỏ qua")
                    skipped_count += 1
                    current_start += segment_size
                    continue
                
                # Generate question cho segment này
                try:
                    from app import generate_question_from_subtitles
                    time_range = f"{segment_start}-{segment_end_int} seconds"
                    print(f"[SEGMENT] Generating question for segment {segment_start}-{segment_end_int}s...")
                    question_data = generate_question_from_subtitles(segment_text, time_range, "vi")
                    
                    if question_data and "question" in question_data and "options" in question_data:
                        # Lưu vào database
                        self.course_model.insert_segment_question(
                            course_id=course_id,
                            segment_start=segment_start,
                            segment_end=segment_end_int,
                            question=question_data["question"],
                            options=question_data["options"],
                            correct_index=question_data.get("correct_index", 0),
                            explanation=question_data.get("explanation", "")
                        )
                        generated_count += 1
                        print(f"[SEGMENT] [OK] Generated and saved question for segment {segment_start}-{segment_end_int}s")
                    else:
                        print(f"[SEGMENT] [FAIL] Failed to generate valid question for segment {segment_start}-{segment_end_int}s")
                        skipped_count += 1
                except Exception as e:
                    print(f"[ERROR] Failed to generate question for segment {segment_start}-{segment_end_int}s: {e}")
                    import traceback
                    traceback.print_exc()
                    skipped_count += 1
                
                current_start += segment_size
            
            return jsonify({
                "ok": True,
                "generated": generated_count,
                "skipped": skipped_count,
                "total_segments": int(max_time / segment_size) + 1,
                "message": f"Đã tạo {generated_count} câu hỏi cho {generated_count + skipped_count} segment(s)"
            })
            
        except Exception as e:
            print(f"[ERROR] api_generate_segment_questions exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_get_segment_question(self):
        """
        GET /api/segments/question?course_id=X&segment_start=Y
        Lấy câu hỏi đã pre-generate cho một segment
        """
        try:
            course_id = request.args.get("course_id")
            segment_start_str = request.args.get("segment_start")
            
            if not course_id:
                return jsonify({"ok": False, "error": "Missing course_id"}), 400
            
            if not segment_start_str:
                return jsonify({"ok": False, "error": "Missing segment_start"}), 400
            
            try:
                course_id = int(course_id)
                segment_start = int(float(segment_start_str))  # Có thể là 50.0 hoặc 50
            except ValueError:
                return jsonify({"ok": False, "error": "Invalid course_id or segment_start"}), 400
            
            # Tính segment_start chính xác (làm tròn xuống bội số của 50)
            segment_start = (segment_start // 50) * 50
            
            question = self.course_model.get_segment_question(course_id, segment_start)
            
            if question:
                return jsonify({
                    "ok": True,
                    "question": question["question"],
                    "options": question["options"],
                    "correct_index": question["correct_index"],
                    "explanation": question["explanation"],
                    "segment_start": question["segment_start"],
                    "segment_end": question["segment_end"]
                })
            else:
                # Trả về 200 với ok=False thay vì 404 để frontend có thể handle fallback
                return jsonify({
                    "ok": False,
                    "error": f"Không tìm thấy câu hỏi cho segment {segment_start}s",
                    "hint": "Có thể cần pre-generate questions trước"
                }), 200
            
        except Exception as e:
            print(f"[ERROR] api_get_segment_question exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_comprehensive_exam_start(self):
        """
        POST /api/comprehensive-exam/start
        Body: { course_id }
        Tạo bài kiểm tra 20 câu trong 15 phút từ transcript (không cần pre-generate)
        """
        try:
            data = request.get_json(force=True) or {}
            course_id = data.get("course_id")
            
            if not course_id:
                return jsonify({"ok": False, "error": "Missing course_id"}), 400
            
            user = session.get("user") or {}
            user_id = user.get("id") or user.get("user_id") or _get_user_id()
            
            if not user_id:
                return jsonify({"ok": False, "error": "User not logged in"}), 401
            
            # Lấy course và caption_url
            course = self.course_model.get_course_by_id(course_id)
            if not course:
                return jsonify({"ok": False, "error": "Course not found"}), 404
            
            try:
                course = {k: course[k] for k in course.keys()}
            except Exception:
                pass
            
            caption_url = course.get("caption_url") or ""
            if not caption_url:
                return jsonify({"ok": False, "error": "Course chưa có transcript. Vui lòng tạo transcript trước."}), 400
            
            # Parse VTT để lấy toàn bộ transcript text
            vtt_path = _url_to_local_path(caption_url)
            if not vtt_path or not os.path.exists(vtt_path):
                return jsonify({"ok": False, "error": f"VTT file not found: {vtt_path}"}), 400
            
            print(f"[COMPREHENSIVE EXAM] Parsing VTT: {vtt_path}")
            cues = _parse_vtt_with_timestamps(vtt_path)
            if not cues:
                return jsonify({"ok": False, "error": "Không thể parse VTT file hoặc VTT file rỗng"}), 400
            
            # Lấy toàn bộ transcript text
            full_transcript = " ".join([cue["text"] for cue in cues if cue.get("text")]).strip()
            
            if len(full_transcript) < 100:
                return jsonify({"ok": False, "error": "Transcript quá ngắn, không đủ để tạo câu hỏi"}), 400
            
            print(f"[COMPREHENSIVE EXAM] Generating 20 questions from transcript (length: {len(full_transcript)} chars)")
            
            # TẠO EXAM ATTEMPT TRƯỚC để có attempt_id ngay
            attempt_id = self.course_model.create_comprehensive_exam(course_id, user_id, time_limit=900)
            print(f"[COMPREHENSIVE EXAM] Created exam attempt: {attempt_id}")
            
            # Trả về attempt_id ngay để frontend có thể bắt đầu
            # Tạo câu hỏi sẽ chạy trong background
            import threading
            
            def generate_questions_background():
                """Tạo câu hỏi trong background"""
                try:
                    # Tạo 20 câu hỏi từ transcript sử dụng AI Gemini
                    import random
                    questions = []
                    transcript_parts = []
                    
                    # Chia transcript thành 20 phần ngẫu nhiên
                    words = full_transcript.split()
                    chunk_size = max(20, len(words) // 20)
                    for i in range(20):
                        start_idx = i * chunk_size
                        end_idx = min(start_idx + chunk_size, len(words))
                        if start_idx < len(words):
                            chunk = " ".join(words[start_idx:end_idx])
                            transcript_parts.append(chunk)
                    
                    # Tạo câu hỏi cho mỗi phần với độ khó tăng dần
                    from app import generate_question_from_subtitles
                    import time
                    
                    for idx, part in enumerate(transcript_parts):
                        if len(part.strip()) < 50:
                            continue
                        
                        # Độ khó: dễ (0-5), trung bình (6-13), khó (14-19)
                        difficulty = "easy" if idx < 6 else ("medium" if idx < 14 else "hard")
                        time_range = f"Phần {idx + 1} của transcript"
                        
                        print(f"[COMPREHENSIVE EXAM] Generating question {idx + 1}/20 (difficulty: {difficulty})...")
                        
                        # Thêm delay giữa các requests để tránh rate limiting
                        if idx > 0:
                            delay = 1.5  # Delay 1.5 giây giữa các requests
                            time.sleep(delay)
                        
                        question_data = generate_question_from_subtitles(part, time_range, "vi")
                        
                        if question_data and "question" in question_data and "options" in question_data:
                            questions.append({
                                "question": question_data["question"],
                                "options": question_data["options"],
                                "correct_index": question_data.get("correct_index", 0),
                                "explanation": question_data.get("explanation", ""),
                                "difficulty": difficulty
                            })
                        
                        # Giới hạn để không quá lâu
                        if len(questions) >= 20:
                            break
                    
                    # Nếu chưa đủ 20, lặp lại với các phần còn lại
                    if len(questions) < 20:
                        remaining = 20 - len(questions)
                        for attempt in range(remaining):
                            # Delay để tránh rate limiting
                            if attempt > 0:
                                time.sleep(1.5)
                            
                            part = random.choice(transcript_parts)
                            if len(part.strip()) >= 50:
                                question_data = generate_question_from_subtitles(part, "Random part", "vi")
                                if question_data and "question" in question_data:
                                    questions.append({
                                        "question": question_data["question"],
                                        "options": question_data["options"],
                                        "correct_index": question_data.get("correct_index", 0),
                                        "explanation": question_data.get("explanation", ""),
                                        "difficulty": "mixed"
                                    })
                            
                            # Giới hạn số lần thử
                            if len(questions) >= 20:
                                break
                    
                    # Shuffle questions nhưng giữ thứ tự độ khó tăng dần (dễ -> khó)
                    questions.sort(key=lambda x: {"easy": 0, "medium": 1, "hard": 2, "mixed": 1}.get(x.get("difficulty", "mixed"), 1))
                    
                    # Đảm bảo đủ 20 câu với fallback
                    while len(questions) < 20:
                        # Fallback: tạo câu hỏi đơn giản từ keywords
                        words_sample = random.sample(words, min(10, len(words)))
                        simple_q = {
                            "question": f"Dựa trên nội dung: '{' '.join(words_sample[:5])}...', câu nào sau đây đúng nhất?",
                            "options": [
                                "Nội dung liên quan đến chủ đề được đề cập",
                                "Nội dung không liên quan",
                                "Chưa rõ nội dung",
                                "Cần thêm thông tin"
                            ],
                            "correct_index": 0,
                            "explanation": "Câu hỏi dựa trên nội dung transcript",
                            "difficulty": "easy"
                        }
                        questions.append(simple_q)
                        if len(questions) >= 20:
                            break
                    
                    questions = questions[:20]  # Đảm bảo chỉ 20 câu
                    
                    # Lưu các câu hỏi vào database
                    for idx, q in enumerate(questions):
                        self.course_model.save_comprehensive_exam_question(
                            attempt_id=attempt_id,
                            question_index=idx + 1,
                            question_text=q.get("question", ""),
                            options=q.get("options", []),
                            correct_index=q.get("correct_index", 0),
                            segment_start=None,
                            segment_end=None
                        )
                    
                    print(f"[COMPREHENSIVE EXAM] Background: Created {len(questions)} questions for attempt {attempt_id}")
                    
                except Exception as e:
                    print(f"[ERROR] Background question generation failed: {e}")
                    import traceback
                    traceback.print_exc()
                    # Fallback: thử lấy từ segment questions
                    try:
                        all_segment_questions = self.course_model.get_all_segment_questions(course_id)
                        if len(all_segment_questions) >= 20:
                            import random
                            questions = random.sample(all_segment_questions, 20)
                            for idx, q in enumerate(questions):
                                self.course_model.save_comprehensive_exam_question(
                                    attempt_id=attempt_id,
                                    question_index=idx + 1,
                                    question_text=q.get("question", ""),
                                    options=q.get("options", []),
                                    correct_index=q.get("correct_index", 0),
                                    segment_start=q.get("segment_start"),
                                    segment_end=q.get("segment_end")
                                )
                            print(f"[COMPREHENSIVE EXAM] Background: Used {len(questions)} segment questions as fallback")
                    except Exception as e2:
                        print(f"[ERROR] Fallback also failed: {e2}")
            
            # Bắt đầu thread tạo câu hỏi trong background
            thread = threading.Thread(target=generate_questions_background, daemon=True)
            thread.start()
            
            # Trả về attempt_id ngay (câu hỏi sẽ được tạo trong background)
            return jsonify({
                "ok": True,
                "attempt_id": attempt_id,
                "total_questions": 20,
                "time_limit_seconds": 900,
                "message": "Đang tạo câu hỏi, vui lòng đợi..."
            })
            
        except Exception as e:
            print(f"[ERROR] api_comprehensive_exam_start: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_comprehensive_exam_get_question(self):
        """
        GET /api/comprehensive-exam/question?attempt_id=X&question_index=Y
        Lấy câu hỏi theo index (1-20)
        """
        try:
            attempt_id = request.args.get("attempt_id")
            question_index_str = request.args.get("question_index")
            
            if not attempt_id or not question_index_str:
                return jsonify({"ok": False, "error": "Missing attempt_id or question_index"}), 400
            
            try:
                question_index = int(question_index_str)
            except ValueError:
                return jsonify({"ok": False, "error": "Invalid question_index"}), 400
            
            import json
            with self.course_model._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT question_text, options_json, correct_index, selected_index, segment_start, segment_end
                    FROM comprehensive_exam_questions
                    WHERE attempt_id = ? AND question_index = ?
                """, (attempt_id, question_index))
                row = cursor.fetchone()
                
                if row:
                    return jsonify({
                        "ok": True,
                        "question_index": question_index,
                        "question": row[0],
                        "options": json.loads(row[1]),
                        "correct_index": row[2],
                        "selected_index": row[3],  # Đã trả lời chưa
                        "segment_start": row[4],
                        "segment_end": row[5]
                    })
                else:
                    # Câu hỏi chưa được tạo (đang tạo trong background)
                    # Trả về 200 với message thay vì 404 để frontend có thể polling
                    return jsonify({
                        "ok": False,
                        "error": "Question not ready yet",
                        "message": "Câu hỏi đang được tạo, vui lòng đợi..."
                    }), 200
                    
        except Exception as e:
            print(f"[ERROR] api_comprehensive_exam_get_question: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_comprehensive_exam_submit_answer(self):
        """
        POST /api/comprehensive-exam/submit-answer
        Body: { attempt_id, question_index, selected_index, time_spent }
        """
        try:
            data = request.get_json(force=True) or {}
            attempt_id = data.get("attempt_id")
            question_index = data.get("question_index")
            selected_index = data.get("selected_index")
            time_spent = data.get("time_spent", 0)
            
            if not all([attempt_id, question_index is not None, selected_index is not None]):
                return jsonify({"ok": False, "error": "Missing required fields"}), 400
            
            self.course_model.submit_comprehensive_exam_answer(
                attempt_id=attempt_id,
                question_index=int(question_index),
                selected_index=int(selected_index),
                time_spent=float(time_spent)
            )
            
            return jsonify({"ok": True})
            
        except Exception as e:
            print(f"[ERROR] api_comprehensive_exam_submit_answer: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_comprehensive_exam_finish(self):
        """
        POST /api/comprehensive-exam/finish
        Body: { attempt_id }
        Hoàn thành exam, tính điểm và phân tích
        """
        try:
            data = request.get_json(force=True) or {}
            attempt_id = data.get("attempt_id")
            
            if not attempt_id:
                return jsonify({"ok": False, "error": "Missing attempt_id"}), 400
            
            # Lấy thông tin exam và questions để phân tích
            results = self.course_model.get_comprehensive_exam_results(attempt_id)
            if not results:
                return jsonify({"ok": False, "error": "Exam not found"}), 404
            
            # Phân tích điểm mạnh/yếu và đề xuất khóa học bằng AI
            try:
                from app import generate_question_from_subtitles
                from ai_gemini import _ensure
                
                # Tạo prompt phân tích
                correct_topics = []
                wrong_topics = []
                
                for q in results["questions"]:
                    if q.get("is_correct"):
                        if q.get("segment_start") is not None:
                            correct_topics.append(f"Segment {q['segment_start']}-{q['segment_end']}s")
                    else:
                        if q.get("segment_start") is not None:
                            wrong_topics.append(f"Segment {q['segment_start']}-{q['segment_end']}s")
                
                analysis_text = f"""
Điểm số: {results['score']}/100
Số câu đúng: {results['correct']}/{results['total']}
Điểm mạnh (topics làm đúng): {', '.join(correct_topics[:5]) if correct_topics else 'Không có'}
Điểm yếu (topics làm sai): {', '.join(wrong_topics[:5]) if wrong_topics else 'Không có'}
                """
                
                # Sử dụng AI để phân tích và đề xuất (có thể dùng Gemini)
                strengths = f"Bạn đã làm tốt ở các phần: {', '.join(correct_topics[:5]) if correct_topics else 'Chưa có điểm mạnh rõ ràng'}"
                weaknesses = f"Bạn cần cải thiện ở các phần: {', '.join(wrong_topics[:5]) if wrong_topics else 'Không có điểm yếu'}"
                
                # Đề xuất khóa học dựa trên điểm số và weaknesses
                course = self.course_model.get_course_by_id(results['course_id'])
                # Fix sqlite3.Row - convert to dict
                course_dict = {}
                if course:
                    try:
                        if hasattr(course, 'keys'):
                            course_dict = dict(course)
                        elif isinstance(course, dict):
                            course_dict = course
                        else:
                            # sqlite3.Row - convert manually
                            course_dict = {key: course[key] for key in course.keys()}
                    except Exception as e:
                        print(f"[WARNING] Could not convert course to dict: {e}")
                        course_dict = {}
                
                course_category = course_dict.get('category', '')
                course_tags = course_dict.get('tags', '')
                course_title = course_dict.get('title', '')
                
                recommendations = f"""
Dựa trên kết quả kiểm tra (điểm: {results['score']}/100):
- Nếu điểm < 50: Nên xem lại toàn bộ khóa học '{course_title}' và làm bài tập thêm
- Nếu điểm 50-70: Nên tập trung vào các phần yếu và thực hành thêm
- Nếu điểm > 70: Có thể chuyển sang khóa học nâng cao về {course_category}
                """
                
                # Check nếu exam đã bị terminate do gian lận
                with self.course_model._connect() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT status FROM comprehensive_exams WHERE attempt_id = ?
                    """, (attempt_id,))
                    row = cursor.fetchone()
                    if row and row[0] == 'terminated':
                        return jsonify({
                            "ok": True,
                            "results": {
                                "attempt_id": attempt_id,
                                "score": 0.0,
                                "completed": 0,
                                "correct": 0,
                                "total": 20,
                                "strengths": None,
                                "weaknesses": "Bài kiểm tra đã bị hủy do phát hiện hành vi gian lận",
                                "recommendations": None
                            }
                        })
                
                # Hoàn thành exam
                self.course_model.finish_comprehensive_exam(
                    attempt_id=attempt_id,
                    strengths=strengths,
                    weaknesses=weaknesses,
                    recommendations=recommendations
                )
                
                # Lấy kết quả cuối cùng
                final_results = self.course_model.get_comprehensive_exam_results(attempt_id)
                
                return jsonify({
                    "ok": True,
                    "results": final_results
                })
                
            except Exception as e:
                print(f"[ERROR] Analysis failed: {e}")
                # Vẫn finish exam nhưng không có phân tích
                self.course_model.finish_comprehensive_exam(attempt_id=attempt_id)
                final_results = self.course_model.get_comprehensive_exam_results(attempt_id)
                return jsonify({
                    "ok": True,
                    "results": final_results,
                    "warning": "Phân tích không khả dụng"
                })
                
        except Exception as e:
            print(f"[ERROR] api_comprehensive_exam_finish: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_comprehensive_exam_terminate(self):
        """
        POST /api/comprehensive-exam/terminate
        Body: { attempt_id, reason, score? }
        Hủy bài kiểm tra do gian lận và set score = 0
        """
        try:
            data = request.get_json(force=True) or {}
            attempt_id = data.get("attempt_id")
            reason = data.get("reason", "Phát hiện hành vi gian lận")
            score = data.get("score", 0.0)
            
            if not attempt_id:
                return jsonify({"ok": False, "error": "Missing attempt_id"}), 400
            
            # Update exam với status = 'terminated' và score = 0
            with self.course_model._connect() as conn:
                cursor = conn.cursor()
                import datetime
                cursor.execute("""
                    UPDATE comprehensive_exams
                    SET ended_at = ?, score = ?, status = ?, weaknesses_analysis = ?
                    WHERE attempt_id = ?
                """, (datetime.datetime.utcnow().isoformat(), float(score), 'terminated', 
                      f"Bài kiểm tra bị hủy: {reason}", attempt_id))
                conn.commit()
            
            return jsonify({"ok": True, "message": "Exam terminated"})
            
        except Exception as e:
            print(f"[ERROR] api_comprehensive_exam_terminate: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def manage_scores(self):
        """
        Trang quản lý điểm dành cho giáo viên
        GET /manage-scores
        """        
        # Kiểm tra quyền giáo viên
        user = session.get("user") or {}
        role = session.get("role")
        if role != "teacher":
            return redirect(url_for("home"))
        
        # Lấy danh sách điểm
        scores = self.course_model.get_all_exam_scores_for_teacher()
        
        # Lấy danh sách courses để filter
        courses_raw = self.course_model.get_all_courses()
        courses = []
        for course in courses_raw:
            try:
                courses.append(dict(course))
            except:
                courses.append({
                    'id': course[0],
                    'title': course[1] if len(course) > 1 else 'N/A'
                })
        
        return render_template("manage_scores.html", scores=scores, courses=courses)
    
    def api_get_scores(self):
        """
        API lấy danh sách điểm (có thể filter theo course_id)
        GET /api/scores?course_id=X
        """
        course_id = request.args.get("course_id", type=int)
        scores = self.course_model.get_all_exam_scores_for_teacher(course_id=course_id)
        return jsonify({"ok": True, "scores": scores})
    
    def api_get_user_exam_details(self):
        """
        API lấy chi tiết các lần làm bài của một user
        GET /api/scores/user-details?user_id=X&course_id=Y
        """
        user_id = request.args.get("user_id", type=int)
        course_id = request.args.get("course_id", type=int)
        
        if not user_id:
            return jsonify({"ok": False, "error": "Missing user_id"}), 400
        
        details = self.course_model.get_user_exam_details(user_id, course_id)
        return jsonify({"ok": True, "details": details})
    
    def api_update_score(self):
        """
        API cập nhật điểm
        POST /api/scores/update
        Body: { attempt_id, new_score }
        """
        data = request.get_json(force=True) or {}
        attempt_id = data.get("attempt_id")
        new_score = data.get("new_score")
        
        if not attempt_id or new_score is None:
            return jsonify({"ok": False, "error": "Missing attempt_id or new_score"}), 400
        
        try:
            new_score = float(new_score)
            if new_score < 0 or new_score > 100:
                return jsonify({"ok": False, "error": "Score must be between 0 and 100"}), 400
            
            success = self.course_model.update_exam_score(attempt_id, new_score)
            if success:
                return jsonify({"ok": True, "message": "Score updated successfully"})
            else:
                return jsonify({"ok": False, "error": "Attempt not found"}), 404
        except Exception as e:
            print(f"[ERROR] api_update_score: {e}")
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500
    
    def api_delete_score(self):
        """
        API xóa một lần làm bài
        POST /api/scores/delete
        Body: { attempt_id }
        """
        data = request.get_json(force=True) or {}
        attempt_id = data.get("attempt_id")
        
        if not attempt_id:
            return jsonify({"ok": False, "error": "Missing attempt_id"}), 400
        
        try:
            success = self.course_model.delete_exam_attempt(attempt_id)
            if success:
                return jsonify({"ok": True, "message": "Exam attempt deleted successfully"})
            else:
                return jsonify({"ok": False, "error": "Attempt not found"}), 404
        except Exception as e:
            print(f"[ERROR] api_delete_score: {e}")
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_comprehensive_exam_results(self):
        """
        GET /api/comprehensive-exam/results?attempt_id=X
        Lấy kết quả exam đã hoàn thành
        """
        try:
            attempt_id = request.args.get("attempt_id")
            
            if not attempt_id:
                return jsonify({"ok": False, "error": "Missing attempt_id"}), 400
            
            results = self.course_model.get_comprehensive_exam_results(attempt_id)
            
            if results:
                return jsonify({"ok": True, "results": results})
            else:
                return jsonify({"ok": False, "error": "Results not found"}), 404
                
        except Exception as e:
            print(f"[ERROR] api_comprehensive_exam_results: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"ok": False, "error": f"Server error: {str(e)}"}), 500

    def api_outline(self, course_id: int):
        sections = self.course_model.get_outline(course_id)
        user = session.get("user") or {}
        user_id = user.get("id") or user.get("user_id")
        progress = self.course_model.get_user_progress(course_id, user_id) if user_id else {}
        return jsonify({"ok": True, "sections": sections, "progress": progress})

    def api_progress_upsert(self):
        p = request.get_json(force=True)
        user = session.get("user") or {}
        user_id = p.get("user_id") or user.get("id") or user.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Bạn chưa đăng nhập"}), 401
        try:
            self.course_model.upsert_progress(
                user_id=int(user_id),
                course_id=int(p["course_id"]),
                item_id=int(p["item_id"]),
                status=p.get("status", "in_progress"),
                seconds_watched=int(p.get("seconds_watched") or 0),
                score=p.get("score"),
            )
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 400

    def manage_courses(self):
        courses = self.course_model.get_all_courses()
        return render_template("manage_courses.html", username=session.get("username"), courses=courses)

    def create_course(self):
        if request.method == "GET":
            return render_template("create_course.html")

        upload_dir = current_app.config.get("UPLOAD_FOLDER") or os.path.join("static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        title = request.form.get("title") or request.form.get("name")
        description = request.form.get("description") or ""
        category = request.form.get("category")
        tags_raw = request.form.get("tags")
        tags = ",".join([t.strip() for t in tags_raw.split(",") if t.strip()]) if tags_raw else None

        image_file = request.files.get("image")
        if not image_file or image_file.filename == "":
            return "Vui lòng chọn ảnh khóa học."
        image_filename = secure_filename(image_file.filename)
        image_name = f"{uuid.uuid4()}_{image_filename}"
        image_path = os.path.join(upload_dir, image_name)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image_file.save(image_path)
        image_url = "/" + image_path.replace(os.sep, "/")

        video_file = request.files.get("video")
        if not video_file or video_file.filename == "":
            return "Vui lòng chọn video bài giảng."
        video_filename = secure_filename(video_file.filename)
        video_name = f"{uuid.uuid4()}_{video_filename}"
        video_path = os.path.join(upload_dir, video_name)
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        video_file.save(video_path)
        video_url = "/" + video_path.replace(os.sep, "/")

        caption_file = request.files.get("caption")
        caption_url = (request.form.get("caption_url") or "").strip() or None
        if caption_file and caption_file.filename:
            cap_name = f"{uuid.uuid4()}_{secure_filename(caption_file.filename)}"
            cap_path = os.path.join(upload_dir, cap_name)
            os.makedirs(os.path.dirname(cap_path), exist_ok=True)
            caption_file.save(cap_path)
            caption_url = "/" + cap_path.replace(os.sep, "/")
        if not caption_url:
            # QUAN TRỌNG: Loại bỏ "_video" suffix trước khi thêm .vtt
            # Video: {uuid}_{filename}_video.mp4 -> VTT: {uuid}_{filename}.vtt
            guess_url = video_url.rsplit(".", 1)[0]
            if guess_url.endswith("_video"):
                guess_url = guess_url[:-6]  # Remove "_video"
            guess_url = guess_url + ".vtt"
            guess_path = guess_url.lstrip("/")
            if os.path.exists(guess_path):
                caption_url = guess_url

        course_id = self.course_model.add_course(
            title, description, image_url, video_url, caption_url, category, tags
        )

        outline_raw = request.form.get("outline_json") or ""
        try:
            payload = json.loads(outline_raw) if outline_raw.strip() else {"sections": []}
        except Exception:
            payload = {"sections": []}
        sections = payload.get("sections", [])

        for s in sections:
            for it in (s.get("items") or []):
                uf = (it.get("upload_field") or "").strip()
                if not uf:
                    continue
                f = request.files.get(uf)
                if f and f.filename:
                    fname = f"{uuid.uuid4()}_{secure_filename(f.filename)}"
                    fpath = os.path.join(upload_dir, fname)
                    os.makedirs(os.path.dirname(fpath), exist_ok=True)
                    f.save(fpath)
                    it["resource_url"] = "/" + fpath.replace(os.sep, "/")

        self.course_model.replace_outline(course_id, sections)

        return redirect(url_for("manage_courses"))

    def edit_course(self, course_id):
        course = self.course_model.get_course_by_id(course_id)
        if not course:
            return "Khóa học không tồn tại", 404

        if request.method == "GET":
            sections = self.course_model.get_outline(course_id)
            return render_template("edit_course.html", course=course, sections=sections)

        title = request.form.get("title") or getattr(course, "title", None)
        description = request.form.get("description") or getattr(course, "description", "")

        category = request.form.get("category")
        if category is None:
            category = getattr(course, "category", None)

        tags_raw = request.form.get("tags")
        if tags_raw is None:
            tags = getattr(course, "tags", None)
        else:
            tags = ",".join([t.strip() for t in tags_raw.split(",") if t.strip()])

        image_file = request.files.get("image")
        if image_file and image_file.filename:
            image_name = f"{uuid.uuid4()}_{secure_filename(image_file.filename)}"
            image_path = os.path.join(current_app.config["UPLOAD_FOLDER"], image_name)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image_file.save(image_path)
            image_url = f"/{image_path.replace(os.sep, '/')}"
        else:
            image_url = getattr(course, "image_url", None) or (course.get("image_url") if isinstance(course, Mapping) else None)

        video_file = request.files.get("video")
        if video_file and video_file.filename:
            video_name = f"{uuid.uuid4()}_{secure_filename(video_file.filename)}"
            video_path = os.path.join(current_app.config["UPLOAD_FOLDER"], video_name)
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            video_file.save(video_path)
            video_url = f"/{video_path.replace(os.sep, '/')}"
        else:
            video_url = getattr(course, "video_url", None) or (course.get("video_url") if isinstance(course, Mapping) else None)

        existing_caption = getattr(course, "caption_url", None) or (course.get("caption_url") if isinstance(course, Mapping) else None)

        caption_file = request.files.get("caption")
        caption_url = (request.form.get("caption_url") or "").strip() or existing_caption

        if caption_file and caption_file.filename:
            cap_name = f"{uuid.uuid4()}_{secure_filename(caption_file.filename)}"
            cap_path = os.path.join(current_app.config["UPLOAD_FOLDER"], cap_name)
            os.makedirs(os.path.dirname(cap_path), exist_ok=True)
            caption_file.save(cap_path)
            caption_url = f"/{cap_path.replace(os.sep, '/')}"

        if not caption_url and video_url:
            # QUAN TRỌNG: Loại bỏ "_video" suffix trước khi thêm .vtt
            # Video: {uuid}_{filename}_video.mp4 -> VTT: {uuid}_{filename}.vtt
            guess_url = video_url.rsplit(".", 1)[0]
            if guess_url.endswith("_video"):
                guess_url = guess_url[:-6]  # Remove "_video"
            guess_url = guess_url + ".vtt"
            guess_path = guess_url.lstrip("/")
            if os.path.exists(guess_path):
                caption_url = guess_url

        self.course_model.update_course(course_id, title, description, image_url, video_url, caption_url, category, tags)

        outline_raw = request.form.get("outline_json") or ""
        try:
            payload = json.loads(outline_raw) if outline_raw.strip() else {"sections": []}
        except Exception:
            payload = {"sections": []}
        sections = payload.get("sections", [])

        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"])
        os.makedirs(upload_dir, exist_ok=True)

        for s in sections:
            for it in (s.get("items") or []):
                uf = (it.get("upload_field") or "").strip()
                if uf:
                    f = request.files.get(uf)
                    if f and f.filename:
                        fname = f"{uuid.uuid4()}_{secure_filename(f.filename)}"
                        fpath = os.path.join(upload_dir, fname)
                        os.makedirs(os.path.dirname(fpath), exist_ok=True)
                        f.save(fpath)
                        it["resource_url"] = "/" + fpath.replace(os.sep, "/")

        self.course_model.replace_outline(course_id, sections)

        return redirect(url_for("manage_courses"))

    def delete_course(self, course_id):
        self.course_model.delete_course(course_id)
        return redirect(url_for("manage_courses"))

    def _pick_caption_for_course(self, course_id):
        if not course_id:
            return None
        c = self.course_model.get_course_by_id(int(course_id))
        if not c:
            return None
        try:
            c = {k: c[k] for k in c.keys()}
        except Exception:
            pass
        cap = c.get("caption_url")
        if cap:
            return cap
        detected, _ = _ensure_caption_files(c.get("video_url"), course_id)
        return detected

    def exam(self, course_id):
        course = self.course_model.get_course_by_id(course_id)
        return render_template('exam.html', course=course)
    
    def ensure_question_bank_from_transcript(self, course_id: int, n_required: int = 20, language: str = "vi") -> int:
      """
      Nếu ngân hàng câu hỏi cho course_id chưa đủ n_required câu thì đọc transcript/caption,
      gọi Gemini sinh 20 câu và lưu vào bảng questions (theo level).
      Trả về số câu đã tạo thêm.
      """
      try:
        # 1) đủ rồi thì thôi
        if self.assignment_model.count_questions(course_id) >= n_required:
            return 0

        # 2) lấy đường dẫn caption/transcript
        cap_path = self.course_model.get_caption_path(course_id)  # bạn thêm hàm này ở bước 3
        if not cap_path:
            raise RuntimeError("Không tìm thấy caption/transcript cho khóa học")

        # 3) gọi helper có sẵn trong app.py (import *lười* bên trong để tránh circular import)
        from app import _read_vtt_as_text, _gemini_generate_mcqs
        transcript = _read_vtt_as_text(cap_path)
        if not transcript or len(transcript) < 50:
            raise RuntimeError("Transcript rỗng hoặc quá ngắn")

        qa_list = _gemini_generate_mcqs(transcript, n=n_required, language=language)

        # 4) gom theo level và lưu
        buckets = {"beginner": [], "intermediate": [], "advanced": []}
        for q in qa_list:
            lvl = (q.get("level") or "beginner").lower()
            if lvl not in buckets: lvl = "beginner"
            buckets[lvl].append({
                "question": q["question"],
                "options": q["options"],
                "answer": q["answer"]  # 'A'..'D'
            })

        inserted = 0
        for lvl, qs in buckets.items():
            if qs:
                self.assignment_model.insert_questions(course_id, lvl, qs)
                inserted += len(qs)
        return inserted
      except Exception as e:
        current_app.logger.warning("ensure_question_bank_from_transcript failed: %s", e)
        return 0
    
    # đặt ở đầu file (hoặc trong class CourseController dưới dạng @staticmethod)
    # --- safe helpers (place near the top of file, outside the class) ---
    @staticmethod
    def _get_int_param(req, key, default=None):
      """Read int from args -> form -> json, without raising on None/invalid."""
      v = req.args.get(key, type=int)
      if v is not None:
        return v
      v = req.form.get(key, type=int)
      if v is not None:
        return v
      data = req.get_json(silent=True) or {}
      try:
        vv = data.get(key)
        if vv is None or (isinstance(vv, str) and vv.strip() == ""):
            return default
        return int(vv)
      except Exception:
        return default
    def _prefill_questions_from_caption_if_needed(self, course_id: int, n_required: int = 20):
        # Đếm câu hỏi hiện có cho khoá
        try:
            have = self.assignment_model.count_questions(course_id)
        except Exception:
            # Tương thích: nếu thuộc tính khác tên, fallback sang model trong app
            from model.assignment_model import AssignmentModel
            self.assignment_model = getattr(self, "assignment_model", AssignmentModel())
            have = self.assignment_model.count_questions(course_id)

        if have >= n_required:
            return

        # Lấy caption path/url từ DB
        c = self.course_model.get_course_by_id(course_id)
        cap_url = (c["caption_url"] if isinstance(c, dict) else getattr(c, "caption_url", "")) or ""
        cap_path = _url_to_local_path(cap_url) if cap_url else ""

        # Đọc transcript từ .vtt; nếu không có thì bỏ qua (không crash)
        from app import _read_vtt_as_text, _gemini_generate_mcqs
        transcript = _read_vtt_as_text(cap_path) if cap_path else ""

        if not transcript or len(transcript) < 50:
            # Không đủ nội dung để sinh câu hỏi
            return

        # Gọi Gemini sinh 20 câu và nhét vào DB, chia theo level
        qa_list = _gemini_generate_mcqs(transcript, n=n_required, language="vi")

        buckets = {"beginner": [], "intermediate": [], "advanced": []}
        for q in qa_list:
            buckets[q.get("level", "beginner")].append({
                "question": q["question"],
                "options": q["options"],
                "answer": q["answer"]  # 'A'..'D'
            })

        for lvl, qs in buckets.items():
            if qs:
                self.assignment_model.insert_questions(course_id, lvl, qs)

    def api_exam_start(self):  
      try:
          self._prefill_questions_from_caption_if_needed(int(request.json.get("course_id")))
      except Exception:
          pass  # không chặn luồng nếu sinh lỗi
        
    # ĐỌC course_id AN TOÀN: tránh int(None) gây 500
      course_id = self._get_int_param(request, "course_id")
      if not course_id:
        return jsonify(ok=False, error="missing course_id"), 400

      attempt_id = str(uuid.uuid4())
    # Thiết lập 15 phút và mục tiêu 20 câu
      ATTEMPT_CACHE[attempt_id] = {
        "course_id": course_id,
        "user_id": _get_user_id(),
        "started_at": time.time(),
        "ends_at": time.time() + 15 * 60,  # 900s
        "level": "easy",
        "cheated": False,
        "cancelled": False,
        "completed_topics": 0,
        "first_try_correct": 0,
        "current_topic": None,
        "pending_repeat_qid": None,
        "repeat_mode": False,
        "last_qid": None,
        "target_total": 20,
    }

    # Ghi attempt vào DB (nếu có hàm)
      try:
        if hasattr(self.course_model, "create_attempt"):
            self.course_model.create_attempt(course_id, user_id=_get_user_id())
      except Exception:
        pass

    # (Tuỳ chọn) hâm nóng ngân hàng câu hỏi từ transcript nếu bạn đã cài
      try:
        if hasattr(self, "ensure_question_bank_from_transcript"):
            self.ensure_question_bank_from_transcript(course_id, n_required=20, language="vi")
      except Exception as e:
        current_app.logger.warning("pre-warm question bank failed: %s", e)

      return jsonify(
        ok=True,
        attempt_id=attempt_id,
        difficulty="easy",
        ends_at=ATTEMPT_CACHE[attempt_id]["ends_at"],
        total_questions=20,
        time_limit_seconds=900,
      )

    def api_exam_next(self):
        p = request.get_json(force=True)
        attempt_id = p.get('attempt_id')
        att = ATTEMPT_CACHE.get(attempt_id) or {}
        if not att:
            return jsonify(ok=False, error="Attempt not found"), 404
        if att.get("cancelled") or att.get("cheated"):
            return jsonify(ok=False, error="Attempt killed")
        if time.time() > att.get("ends_at", 0):
            att["cancelled"] = True
            ATTEMPT_CACHE[attempt_id] = att
            return jsonify(ok=False, error="Time is up")

        # Kiểm tra đã làm đủ 20 câu hỏi
        if att.get("completed_topics", 0) >= 20:
            return jsonify(ok=True, done=True)

        course_id = p.get('course_id') or att.get('course_id')
        diff = p.get('difficulty', att.get("level", "easy"))
        caption_url = self._pick_caption_for_course(course_id)
        similar_to = p.get('similar_to') or att.get("pending_repeat_qid")
        session_id = session.get("user", {}).get("id", "anonymous")
        
        # Lấy script content thực tế từ caption/transcript - QUAN TRỌNG: Phải có transcript thực tế
        script_content = ""
        transcript_source = None
        
        # Ưu tiên 1: Đọc từ file caption/transcript (.vtt/.srt)
        try:
            from app import _read_vtt_as_text
            # Lấy đường dẫn caption thực tế
            cap_path = self.course_model.get_caption_path(course_id)
            if not cap_path and caption_url:
                # Fallback: chuyển caption_url sang local path
                cap_path = _url_to_local_path(caption_url)
            
            if cap_path:
                import os
                if os.path.exists(cap_path):
                    script_content = _read_vtt_as_text(cap_path)
                    if script_content and len(script_content.strip()) >= 100:  # Ít nhất 100 ký tự
                        transcript_source = f"caption_file:{cap_path}"
                        current_app.logger.info(f"[EXAM_NEXT] ✅ Loaded transcript from {cap_path}, length: {len(script_content)} chars")
                    else:
                        current_app.logger.warning(f"[EXAM_NEXT] ⚠️ Caption file {cap_path} exists but content too short: {len(script_content) if script_content else 0} chars")
                else:
                    current_app.logger.warning(f"[EXAM_NEXT] ⚠️ Caption file not found: {cap_path}")
        except Exception as e:
            current_app.logger.warning(f"[EXAM_NEXT] Failed to read caption: {e}")
        
        # Ưu tiên 2: Nếu không có từ file, thử lấy từ course model (script_text)
        if not script_content or len(script_content.strip()) < 100:
            try:
                course = self.course_model.get_course_by_id(course_id)
                if course:
                    # Thử lấy script_text từ course nếu có
                    if isinstance(course, dict):
                        script_content = course.get("script_text", "") or course.get("description", "")
                    else:
                        script_content = getattr(course, "script_text", "") or getattr(course, "description", "")
                    
                    if script_content and len(script_content.strip()) >= 100:
                        transcript_source = "course_script_text"
                        current_app.logger.info(f"[EXAM_NEXT] ✅ Loaded transcript from course script_text, length: {len(script_content)} chars")
            except Exception as e:
                current_app.logger.warning(f"[EXAM_NEXT] Failed to get script from course: {e}")
        
        # Kiểm tra: Nếu không có transcript đủ dài, báo lỗi rõ ràng
        if not script_content or len(script_content.strip()) < 100:
            current_app.logger.error(f"[EXAM_NEXT] ❌ No valid transcript found for course_id={course_id}")
            current_app.logger.error(f"   Caption URL: {caption_url}")
            current_app.logger.error(f"   Script content length: {len(script_content) if script_content else 0} chars")
            current_app.logger.error(f"   Required minimum: 100 chars")
            # Thử tìm file caption thủ công
            import os
            possible_paths = [
                f"static/captions/course_{course_id}.vtt",
                f"static/captions/{course_id}.vtt",
                f"static/uploads/course_{course_id}.vtt",
                f"static/uploads/{course_id}.vtt",
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    current_app.logger.warning(f"   Found possible caption file: {path}")
                    try:
                        from app import _read_vtt_as_text
                        test_content = _read_vtt_as_text(path)
                        if test_content and len(test_content.strip()) >= 100:
                            current_app.logger.info(f"   ✅ Successfully read from {path}, length: {len(test_content)} chars")
                            script_content = test_content
                            transcript_source = f"manual_found:{path}"
                            break
                    except Exception as e:
                        current_app.logger.warning(f"   Failed to read {path}: {e}")
            # Vẫn tiếp tục nhưng sẽ dùng fallback - nhưng log rõ ràng
        
        # Sử dụng script-based system với transcript thực tế
        if video_script_quiz_service:
            try:
                # QUAN TRỌNG: Chỉ tạo câu hỏi từ transcript nếu có đủ nội dung
                if script_content and len(script_content.strip()) >= 100:
                    current_app.logger.info(f"[EXAM_NEXT] 🎯 Creating question from transcript (source: {transcript_source}, length: {len(script_content)} chars)")
                    # Tạo câu hỏi từ script content thực tế
                    script_qa = video_script_quiz_service.get_next_question_from_video_script(
                        course_id=str(course_id),
                        script_content=script_content,  # Dùng transcript thực tế
                        session_id=str(session_id),
                        question_type="mcq",
                        language="vi"
                    )
                else:
                    # Nếu không có transcript, báo lỗi và dùng fallback
                    current_app.logger.error(f"[EXAM_NEXT] ❌ Cannot create question: No valid transcript (length: {len(script_content) if script_content else 0} chars, required: >= 100)")
                    raise ValueError("No valid transcript available for course")
                
                # Validate và đảm bảo có đầy đủ dữ liệu
                question_text = script_qa.get("question", "").strip()
                if not question_text:
                    question_text = "Câu hỏi về nội dung video bài giảng"
                
                options = script_qa.get("options", [])
                if not options or len(options) < 2:
                    # Đảm bảo có ít nhất 4 options
                    options = ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"]
                
                # SỬ DỤNG HASH CÓ SẴN TỪ SERVICE THAY VÌ TẠO LẠI
                # để tránh mismatch do different secret keys
                options_hashes = [_hash_option(opt) for opt in options]
                correct_idx = int(script_qa.get("correct_index", 0) or 0)
                if not (0 <= correct_idx < len(options_hashes)):
                   correct_idx = 0
                correct_hash = options_hashes[correct_idx]
                
                # Log để debug
                current_app.logger.info(f"[EXAM_NEXT] Generated question: qid={script_qa.get('qid')}, question_len={len(question_text)}, options_count={len(options)}")
                
                qa = {
                    "qid": script_qa.get("qid") or f"script_q_{hash(question_text)}",
                    "question": question_text,
                    "options": options,
                    "options_hashes": options_hashes,
                    "answer_index": correct_idx,
                    "correct_index": correct_idx,
                    "correct_hash": correct_hash,
                    "explanation": script_qa.get("explanation", "Giải thích dựa trên nội dung video"),
                    "topic_hash": script_qa.get("qid", "script_topic"),
                    "type": "mcq",
                    "time_limit_ms": 10000
                }
            except Exception as e:
                # Fallback nếu script system không hoạt động
                current_app.logger.warning(f"[EXAM_NEXT] Script service failed: {e}, using fallback")
                options = ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"]
                options_hashes = [_hash_option(opt) for opt in options]
                correct_hash = options_hashes[0]
                
                qa = {
                    "qid": "fallback_q_" + str(hash(str(course_id))),
                    "question": "Câu hỏi về nội dung video bài giảng",
                    "options": options,
                    "options_hashes": options_hashes,
                    "answer_index": 0,
                    "correct_index": 0,
                    "correct_hash": correct_hash,
                    "explanation": "Giải thích dựa trên nội dung video",
                    "topic_hash": "fallback_topic",
                    "type": "mcq",
                    "time_limit_ms": 10000
                }
        else:
            # Fallback nếu script system không hoạt động
            options = ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"]
            options_hashes = [_hash_option(opt) for opt in options]
            correct_hash = options_hashes[0]
            
            qa = {
                "qid": "fallback_q_" + str(hash(str(course_id))),
                "question": "Câu hỏi về nội dung video bài giảng",
                "options": options,
                "options_hashes": options_hashes,
                "answer_index": 0,
                "correct_index": 0,
                "correct_hash": correct_hash,
                "explanation": "Giải thích dựa trên nội dung video",
                "topic_hash": "fallback_topic",
                "type": "mcq",
                "time_limit_ms": 10000
            }

        try:
            if hasattr(self.course_model, "log_question"):
                self.course_model.log_question(attempt_id, qa)
        except Exception:
            pass

        # LƯU VÀO QA_CACHE để submit có thể lấy đáp án đúng
        qid = qa.get("qid")
        if qid:
            QA_CACHE[qid] = {
                "correct_hash": qa.get("correct_hash"),
                "options_hashes": qa.get("options_hashes", []),
                "difficulty": qa.get("difficulty", "easy"),
                "type": qa.get("type", "mcq"),
                "rubric": qa.get("rubric"),
                "question": qa.get("question"),
                "options": qa.get("options", []),
                "cue_text": qa.get("cue_text", "NO_CAPTION"),
                "topic_hash": qa.get("topic_hash"),
                "correct_index": qa.get("correct_index"),
                "answer_index": qa.get("answer_index") or qa.get("correct_index")
            }
            print(f"[OK] QA_CACHE updated for qid: {qid}")
            print(f"  options_hashes: {qa.get('options_hashes')}")
            print(f"  correct_hash: {qa.get('correct_hash')}")
            print(f"  correct_index: {qa.get('correct_index')}")

        # Validate qa trước khi trả về
        if not qa.get("question") or not qa.get("options") or len(qa.get("options", [])) < 2:
            current_app.logger.error(f"[EXAM_NEXT] Invalid qa structure: {qa}")
            # Tạo qa mặc định nếu không hợp lệ
            qa = {
                "qid": "error_q_" + str(hash(str(course_id))),
                "question": "Câu hỏi về nội dung video bài giảng",
                "options": ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"],
                "options_hashes": [_hash_option(opt) for opt in ["Đáp án A", "Đáp án B", "Đáp án C", "Đáp án D"]],
                "answer_index": 0,
                "correct_index": 0,
                "correct_hash": _hash_option("Đáp án A"),
                "explanation": "Giải thích dựa trên nội dung video",
                "topic_hash": "error_topic",
                "type": "mcq",
                "time_limit_ms": 10000
            }
        
        att["current_topic"] = qa.get("topic_hash")
        att["pending_repeat_qid"] = None
        att["repeat_mode"] = bool(similar_to)
        att["last_qid"] = qa.get("qid")
        ATTEMPT_CACHE[attempt_id] = att
        
        # Log response để debug
        current_app.logger.info(f"[EXAM_NEXT] Returning question: qid={qa.get('qid')}, question={qa.get('question')[:50]}..., options_count={len(qa.get('options', []))}")
        
        return jsonify(ok=True, **qa)

    def api_exam_submit(self):
        p = request.get_json(force=True)
        attempt_id = p.get('attempt_id')
        att = ATTEMPT_CACHE.get(attempt_id) or {}
        if not att:
            return jsonify(ok=False, error="Attempt not found"), 404

        if att.get("cancelled") or att.get("cheated"):
            return jsonify(ok=True, correct=False, killed=True,
                           next_difficulty=att.get("level", "easy"))

        if time.time() > att.get("ends_at", 0):
            att["cancelled"] = True
            ATTEMPT_CACHE[attempt_id] = att
            return jsonify(ok=False, error="Time is up")

        qid = p.get('qid')
        answer = p.get('answer')
        spent = int(p.get("time_spent_ms") or 0)

        # Chỉ lưu câu trả lời, không kiểm tra đúng/sai ngay
        # AI sẽ chấm chi tiết sau khi nộp bài
        try:
            if hasattr(self.course_model, "log_answer"):
                # Lưu với correct=False tạm thời, AI sẽ chấm lại sau
                self.course_model.log_answer(attempt_id, qid, answer, False, spent)
        except Exception:
            pass

        # Tăng số câu đã làm
        att["completed_topics"] = att.get("completed_topics", 0) + 1
        ATTEMPT_CACHE[attempt_id] = att
        
        # Trả về thành công, không trả về đúng/sai
        return jsonify(ok=True, saved=True)

    def api_exam_event(self):
      import json

      p = request.get_json(silent=True) or {}
      attempt_id = str(p.get("attempt_id") or "").strip()
      if not attempt_id:
        return jsonify(ok=False, error="missing attempt_id"), 400

    # Chuẩn hóa payload
      event = (p.get("event") or p.get("event_type") or p.get("kind") or "").strip().lower()
      reason = (p.get("reason") or "").strip().lower()
      confidence = float(p.get("confidence") or 1.0)
      cheat_count = int(p.get("cheat_count") or 0)

    # Lấy course_id từ payload hoặc suy ra từ DB
      course_id = p.get("course_id")
      try:
        if course_id is not None and str(course_id).strip() != "":
            course_id = int(course_id)
        else:
            if hasattr(self.course_model, "get_course_id_by_attempt"):
                derived = self.course_model.get_course_id_by_attempt(attempt_id)
                if isinstance(derived, (list, tuple)) and len(derived) >= 1:
                    course_id = derived[0]
            else:
                course_id = None
      except Exception:
        course_id = None

    # user_id từ session (nếu có)
      try:
        user_id = session.get("user", {}).get("id")
      except Exception:
        user_id = None

    # 1) Log sự kiện cho AI dashboard / phân tích hành vi
      try:
        meta = {
            "reason": reason or None,
            "confidence": confidence,
            "cheat_count": cheat_count,
            "timestamp": p.get("timestamp")
        }
        self.course_model.log_proctor_event(
            attempt_id=attempt_id,
            user_id=user_id,
            course_id=course_id,
            event_type=event or "event",
            reason=reason or None,
            confidence=confidence,
            meta_json=json.dumps(meta, ensure_ascii=False)
        )
      except Exception as e:
        logger = getattr(self, "logger", None)
        if logger:
            logger.exception("log_proctor_event failed: %s", e)

    # 2) Nếu là sự kiện nghiêm trọng → đóng attempt (idempotent)
      SEVERE = {
        "terminated", "cheat",
        "multiple_faces", "multiple_faces_detected",
        "suspicious_objects", "camera_denied",
        "face_mismatch", "face_monitoring_failed",
        "page_hide", "window_blur"
      }
      cheated_now = False

      if event in SEVERE or reason in SEVERE:
        # 2.1) Ghim cờ cache cho /api/exam/finish (nếu được gọi sau)
        if not hasattr(self, "ATTEMPT_CACHE"):
            self.ATTEMPT_CACHE = {}
        att = self.ATTEMPT_CACHE.get(attempt_id) or {}
        att["cheated"] = True
        att["reason"]  = reason or event or "cheat"
        self.ATTEMPT_CACHE[attempt_id] = att

        # 2.2) Chốt attempt về 0 điểm (idempotent; có fallback)
        
        
        try:
            if hasattr(self.course_model, "mark_attempt_cheated"):
                self.course_model.mark_attempt_cheated(attempt_id=attempt_id, reason=att["reason"])
                cheated_now = True
            else:
                raise AttributeError("mark_attempt_cheated not available")
        except Exception:
            try:
                if hasattr(self.course_model, "force_close_attempt_zero"):
                    self.course_model.force_close_attempt_zero(attempt_id)
                    cheated_now = True
            except Exception as e2:
                logger = getattr(self, "logger", None)
                if logger:
                    logger.exception("force_close_attempt_zero failed for attempt %s: %s", attempt_id, e2)

        # 2.3) (Tuỳ) Đóng comprehensive_exams nếu dự án bạn có bảng này
        try:
            if hasattr(self.course_model, "terminate_comprehensive_attempt"):
                self.course_model.terminate_comprehensive_attempt(attempt_id)
        except Exception as e:
            logger = getattr(self, "logger", None)
            if logger:
                logger.warning("terminate_comprehensive_attempt failed for attempt %s: %s", attempt_id, e)

      return jsonify(ok=True, attempt_id=attempt_id, event=event, reason=reason, cheated=cheated_now)

   
   


    def api_exam_finish(self):
        import json
        p = request.get_json(force=True)
        attempt_id = p.get("attempt_id")
        att = ATTEMPT_CACHE.get(attempt_id) or {}
        if not att:
            return jsonify(ok=False, error="Attempt not found"), 404
        
        course_id = att.get("course_id")
        if att.get("cheated") or att.get("cancelled"):
            score = 0.0
            detailed_results = []
            strengths = "Không có điểm mạnh do vi phạm quy định"
            weaknesses = "Bạn đã vi phạm quy định làm bài kiểm tra"
            recommendations = "Vui lòng làm lại bài kiểm tra một cách trung thực"
        else:
            # Lấy tất cả câu hỏi và câu trả lời
            results = self.course_model.get_exam_results(attempt_id)
            
            # AI chấm chi tiết từng câu
            detailed_results = []
            correct_count = 0
            
            try:
                import google.generativeai as genai
                from ai_gemini import _ensure
                
                if _ensure():
                    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
                    model = genai.GenerativeModel('gemini-flash')
                    
                    for i, result in enumerate(results, 1):
                        question = result.get("question", "")
                        options = result.get("options", [])
                        user_answer = result.get("user_answer", "")
                        correct_hash = result.get("correct_hash", "")
                        qtype = result.get("type", "mcq")
                        
                        # Tìm đáp án đúng từ hash
                        correct_index = None
                        correct_option = ""
                        for idx, opt in enumerate(options):
                            opt_hash = _hash_option(opt)
                            if opt_hash == correct_hash:
                                correct_index = idx
                                correct_option = opt
                                break
                        
                        # Tìm đáp án của học viên từ hash
                        user_answer_index = None
                        user_answer_option = ""
                        if user_answer:
                            for idx, opt in enumerate(options):
                                opt_hash = _hash_option(opt)
                                if opt_hash == user_answer:
                                    user_answer_index = idx
                                    user_answer_option = opt
                                    break
                        
                        # Kiểm tra đúng/sai
                        user_answer_hash = user_answer
                        is_correct = (user_answer_hash == correct_hash)
                        if is_correct:
                            correct_count += 1
                        
                        # Tạo lời giải thích bằng AI
                        explanation = ""
                        try:
                            user_answer_text = user_answer_option if user_answer_option else "Không chọn"
                            prompt = f"""
Bạn là giáo viên AI chuyên giải thích đáp án bài kiểm tra.

CÂU HỎI {i}:
{question}

CÁC LỰA CHỌN:
{chr(10).join([f"{chr(65+j)}. {opt}" for j, opt in enumerate(options)])}

ĐÁP ÁN ĐÚNG: {chr(65 + correct_index)}. {correct_option}

ĐÁP ÁN HỌC VIÊN CHỌN: {user_answer_text if user_answer_text != "Không chọn" else "Không chọn câu trả lời"}

Hãy giải thích:
1. Tại sao đáp án đúng là đúng?
2. Nếu học viên làm sai, giải thích tại sao sai và cách đúng là gì?
3. Cung cấp kiến thức bổ sung liên quan đến câu hỏi này.

Trả về lời giải thích ngắn gọn, rõ ràng, dễ hiểu (khoảng 2-3 câu).
"""
                            response = model.generate_content(prompt, generation_config={"temperature": 0.3, "max_output_tokens": 300})
                            explanation = response.text.strip()
                        except Exception as e:
                            print(f"Error generating explanation: {e}")
                            explanation = f"Đáp án đúng là {chr(65 + correct_index)}. {correct_option}"
                        
                        detailed_results.append({
                            "question_number": i,
                            "question": question,
                            "options": options,
                            "user_answer": user_answer_hash,
                            "user_answer_index": user_answer_index,
                            "user_answer_option": user_answer_option,
                            "correct_answer": correct_hash,
                            "correct_index": correct_index,
                            "correct_option": correct_option,
                            "is_correct": is_correct,
                            "explanation": explanation,
                            "time_spent_ms": result.get("time_spent_ms", 0)
                        })
                else:
                    # Fallback nếu không có Gemini
                    for i, result in enumerate(results, 1):
                        correct_hash = result.get("correct_hash", "")
                        user_answer = result.get("user_answer", "")
                        is_correct = (user_answer == correct_hash)
                        if is_correct:
                            correct_count += 1
                        
                        options = result.get("options", [])
                        correct_index = None
                        for idx, opt in enumerate(options):
                            if _hash_option(opt) == correct_hash:
                                correct_index = idx
                                break
                        
                        # Tìm đáp án của học viên
                        user_answer_index = None
                        user_answer_option = ""
                        if user_answer:
                            for idx, opt in enumerate(options):
                                if _hash_option(opt) == user_answer:
                                    user_answer_index = idx
                                    user_answer_option = opt
                                    break
                        
                        detailed_results.append({
                            "question_number": i,
                            "question": result.get("question", ""),
                            "options": options,
                            "user_answer": user_answer,
                            "user_answer_index": user_answer_index,
                            "user_answer_option": user_answer_option,
                            "correct_answer": correct_hash,
                            "correct_index": correct_index,
                            "correct_option": options[correct_index] if correct_index is not None else "",
                            "is_correct": is_correct,
                            "explanation": f"Đáp án đúng là {chr(65 + correct_index)}" if correct_index is not None else "",
                            "time_spent_ms": result.get("time_spent_ms", 0)
                        })
            except Exception as e:
                print(f"Error in AI grading: {e}")
                # Fallback nếu lỗi
                for i, result in enumerate(results, 1):
                    correct_hash = result.get("correct_hash", "")
                    user_answer = result.get("user_answer", "")
                    is_correct = (user_answer == correct_hash)
                    if is_correct:
                        correct_count += 1
                    
                    detailed_results.append({
                        "question_number": i,
                        "question": result.get("question", ""),
                        "options": result.get("options", []),
                        "user_answer": user_answer,
                        "correct_answer": correct_hash,
                        "is_correct": is_correct,
                        "explanation": "",
                        "time_spent_ms": result.get("time_spent_ms", 0)
                    })
            
            # Tính điểm
            ttl = len(results) or 20
            score = round((correct_count / ttl * 100), 2) if ttl > 0 else 0
            
            # Phân tích điểm mạnh/yếu và đề xuất khóa học bằng AI
            strengths = ""
            weaknesses = ""
            recommendations = ""
            
            try:
                if _ensure():
                    # Tạo prompt phân tích
                    correct_topics = [r["question"] for r in detailed_results if r.get("is_correct")]
                    wrong_topics = [r["question"] for r in detailed_results if not r.get("is_correct")]
                    
                    analysis_prompt = f"""
Bạn là chuyên gia giáo dục AI phân tích kết quả bài kiểm tra.

KẾT QUẢ BÀI KIỂM TRA:
- Tổng số câu: {ttl}
- Số câu đúng: {correct_count}
- Điểm số: {score}/100

CÁC CÂU ĐÚNG ({len(correct_topics)} câu):
{chr(10).join([f"- {q[:100]}..." for q in correct_topics[:5]])}

CÁC CÂU SAI ({len(wrong_topics)} câu):
{chr(10).join([f"- {q[:100]}..." for q in wrong_topics[:5]])}

NHIỆM VỤ:
1. Phân tích ĐIỂM MẠNH của học viên (những phần họ làm tốt)
2. Phân tích ĐIỂM YẾU của học viên (những phần cần cải thiện)
3. Đề xuất các KHÓA HỌC phù hợp để cải thiện điểm yếu

Trả về JSON:
{{
  "strengths": "Điểm mạnh của học viên (2-3 câu)",
  "weaknesses": "Điểm yếu và cần cải thiện (2-3 câu)",
  "recommendations": "Đề xuất khóa học cụ thể (2-3 khóa học)"
}}
"""
                    response = model.generate_content(analysis_prompt, generation_config={"temperature": 0.5, "max_output_tokens": 500})
                    text = response.text.strip()
                    s = text.find("{")
                    e = text.rfind("}")
                    if s != -1 and e != -1:
                        data = json.loads(text[s:e+1])
                        strengths = data.get("strengths", "Bạn đã làm tốt một số phần trong bài kiểm tra.")
                        weaknesses = data.get("weaknesses", "Bạn cần cải thiện một số phần.")
                        recommendations = data.get("recommendations", "Hãy xem lại video bài giảng và làm lại bài kiểm tra.")
            except Exception as e:
                print(f"Error in AI analysis: {e}")
                strengths = "Điểm mạnh: Bạn đã làm đúng một số câu hỏi."
                weaknesses = "Điểm yếu: Bạn cần cải thiện kiến thức ở các phần làm sai."
                recommendations = "Đề xuất: Xem lại video bài giảng và làm bài kiểm tra lại."
            
            # Lưu kết quả vào database
            try:
                self.course_model.finish_attempt(attempt_id, score, att.get("cheated", False))
            except Exception:
                pass
        
        # Lưu kết quả chi tiết vào cache để trang kết quả lấy
        if not hasattr(self, 'EXAM_RESULTS_CACHE'):
            self.EXAM_RESULTS_CACHE = {}
        self.EXAM_RESULTS_CACHE[attempt_id] = {
            "score": score,
            "total": len(detailed_results) or 20,
            "correct": correct_count,
            "detailed_results": detailed_results,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "course_id": course_id
        }
        
        return jsonify(ok=True, 
                      score=score,
                      total=len(detailed_results) or 20,
                      correct=correct_count,
                      attempt_id=attempt_id)

    # --- STRICT: GEMINI chỉ dùng SCRIPT, không đọc transcript/VTT ---
    def api_script_quiz_next(self):
        """
        POST /api/script-quiz/next
        Body: { course_id, attempt_id, type: "mcq"|"essay"|"oral", script_text, lang? }
        Bắt buộc có script_text; nếu thiếu -> 400. Không động tới VTT.
        """
        p = request.get_json(force=True)
        course_id  = str(p.get("course_id"))
        attempt_id = str(p.get("attempt_id") or uuid.uuid4())
        qtype      = (p.get("type") or "mcq").strip().lower()
        lang       = (p.get("lang") or "vi").strip().lower()
        script_text = (p.get("script_text") or "").strip()

        if not script_text:
            return jsonify(ok=False, error="STRICT: thiếu script_text (nội dung kịch bản video)."), 400

        # Gọi engine STRICT SCRIPT
        if not video_script_quiz_service:
            return jsonify(ok=False, error="Video script quiz service is not available"), 503
        
        item = video_script_quiz_service.get_next_question_from_video_script(
            course_id=course_id,
            script_content=script_text,
            session_id=attempt_id,
            question_type=qtype,
            language=lang
        )

        # Chuẩn hoá cho UI (giữ cùng format MCQ/Essay/Oral của hệ thống)
        if item.get("type") == "mcq":
            time_ms = item.get("time_limit_ms") or 5000
            payload = {
                "ok": True,
                "qid": item.get("qid"),
                "type": "mcq",
                "question": item.get("question"),
                "options": item.get("options", []),
                "options_hashes": item.get("options_hashes", []),
                "correct_index": item.get("correct_index"),
                "correct_hash": item.get("correct_hash"),
                "rubric": None,
                "time_limit_ms": time_ms
            }
        else:
            # essay/oral — tạo rubric đơn giản từ keywords
            kws = item.get("keywords", [])
            time_ms = item.get("time_limit_ms") or 10000
            payload = {
                "ok": True,
                "qid": item.get("qid"),
                "type": item.get("type"),
                "question": item.get("question"),
                "options": [],
                "options_hashes": [],
                "correct_index": None,
                "correct_hash": None,
                "rubric": {"keywords": kws, "threshold": max(2, len(kws)//2 or 1)},
                "time_limit_ms": time_ms
            }

        return jsonify(payload)

    def api_script_quiz_reset(self):
        """
        POST /api/script-quiz/reset
        Body: { attempt_id }
        Dọn cache theo phiên (nếu cần).
        """
        p = request.get_json(force=True)
        attempt_id = str(p.get("attempt_id") or "")
        if attempt_id and video_script_quiz_service:
            try:
                video_script_quiz_service.reset_session(attempt_id)
            except Exception:
                pass
        return jsonify(ok=True)
    
    
    
    # --- Proctoring handlers ---
    def api_exam_verify_face(self):
      try:
        data = request.get_json(force=True, silent=True) or {}
        attempt_id = (data.get("attempt_id") or "").strip()
        image_b64  = data.get("image_base64") or data.get("image") or ""
        frame_no   = int(data.get("frame_no") or 0)
        if not attempt_id or not image_b64:
            return jsonify(ok=False, error="missing attempt_id or image_base64"), 400

        # AI nhận diện khung hình như trước (đếm mặt, attention, objects…)
        svc = get_camera_capture_service()
        capture = svc.capture_frame_from_base64(image_b64, attempt_id, frame_no)
        if not capture.get("success"):
            return jsonify(ok=False, error=capture.get("error","decode_error")), 400

        ai = capture.get("ai", {})  # cùng định dạng với /api/exam/capture-frame
        face_count = int(ai.get("face_count", 0))
        attention_score = float(ai.get("attention_score", 0.0))
        cheating_detected = bool(ai.get("cheating_detected", False))
        cheating_reason = ai.get("cheating_reason")
        capture_path = capture.get("filepath")
        capture_rel = capture.get("relative_filepath")
        capture_web = capture.get("web_url")
        capture_time = capture.get("captured_at")

        # --- NEW: so khớp với avatar nếu có ---
        # FE nên gửi avatar ở key 'avatar_image_base64'
        avatar_b64 = (data.get("avatar_image_base64") or data.get("avatar") or "").strip()

        # Đọc ngưỡng & chế độ từ .env
        thr = float(os.getenv("FACE_VERIFY_THRESHOLD", "0.50"))
        strict = os.getenv("FACE_VERIFY_STRICT", "0") == "1"
        verify_enabled = os.getenv("FACE_VERIFY_ENABLED", "1") == "1"

        face_similarity = None
        verified = (face_count == 1)  # mặc định (backward compatible)

        if verify_enabled and avatar_b64:
            try:
                import base64
                from services.face_recognition_service import get_face_recognition_service
                face_service = get_face_recognition_service()

                cur_bytes = base64.b64decode(image_b64.split(",")[-1])
                ava_bytes = base64.b64decode(avatar_b64.split(",")[-1])
                face_similarity = face_service.compare_face_with_avatar_bytes(cur_bytes, ava_bytes)

                # Quy tắc nới lỏng: phải có ≥1 mặt và similarity ≥ thr (mặc định 0.50)
                if face_count >= 1:
                    verified = (face_similarity >= thr)

                # Nếu không tính được similarity thì:
                #   strict=0 → vẫn cho qua nếu có ≥1 mặt
                #   strict=1 → fail
                if face_similarity is None or face_similarity == 0.0:
                    verified = (face_count >= 1) if not strict else False
            except Exception:
                verified = (face_count >= 1) if not strict else False

        objects_json = json.dumps(ai.get("suspicious_objects") or [])

        # Ghi log proctor với metadata ảnh
        user_id, course_id = self.get_attempt_context(attempt_id)
        evidence_info = None
        if user_id and course_id:
            labels = self._build_proctor_labels(user_id, course_id)
            snapshot_for_db = capture_rel
            if cheating_detected and capture_path:
                evidence_info = svc.promote_evidence(
                    capture_path,
                    user_slug=labels["user_slug"],
                    course_slug=labels["course_slug"],
                    attempt_id=attempt_id,
                    frame_no=frame_no,
                    event_type="cheating_detected",
                    reason=cheating_reason if isinstance(cheating_reason, str) else str(cheating_reason),
                    captured_at=capture_time,
                )
                if evidence_info:
                    snapshot_for_db = evidence_info.get("relative_path") or snapshot_for_db

            self.course_model.log_proctor_frame(
                attempt_id=attempt_id,
                user_id=user_id,
                course_id=course_id,
                frame_no=frame_no,
                face_count=face_count,
                attention_score=attention_score,
                objects_json=objects_json,
                snapshot_url=snapshot_for_db,
            )

            if cheating_detected:
                meta_payload = {
                    "reason": cheating_reason,
                    "captured_at": capture_time,
                    "frame_no": frame_no,
                    "username": labels.get("username"),
                    "course_title": labels.get("course_title"),
                    "capture_url": capture_web,
                }
                if evidence_info:
                    meta_payload["evidence_url"] = evidence_info.get("web_url")
                    meta_payload["evidence_path"] = evidence_info.get("relative_path")
                self.course_model.log_proctor_event(
                    attempt_id=attempt_id,
                    user_id=user_id,
                    course_id=course_id,
                    event_type="cheating_detected",
                    confidence=1.0,
                    meta_json=json.dumps(meta_payload, ensure_ascii=False),
                )

        return jsonify(ok=True,
                       verified=bool(verified),
                       face_count=face_count,
                       attention_score=round(attention_score, 3),
                       cheating_detected=cheating_detected,
                       cheating_reason=cheating_reason,
                       entities=ai.get("entities", []),
                       face_similarity=None if face_similarity is None else round(float(face_similarity), 3),
                       threshold_used=thr)
      except Exception as e:
        return jsonify(ok=False, error=str(e)), 500
    
    
    def api_exam_cheating(self):
      data = request.get_json(silent=True) or {}
      attempt_id = data.get('attempt_id')
      if not attempt_id:
        return jsonify(ok=False, error='missing attempt_id'), 400

    # Log “terminated” + đóng attempt về 0
      try:
        self.course_model.log_proctor_event(
            attempt_id=attempt_id,
            user_id=None, course_id=None,
            event_type='terminated',
            meta_json=json.dumps({
                "reason": "cheating_confirmed",
                "cheat_count": data.get("cheat_count"),
                "final_score": 0
            }, ensure_ascii=False)
        )
      except Exception:
        pass

      try:
        self.course_model.mark_attempt_cheated(attempt_id=attempt_id, user_id=None, course_id=None, reason='cheating_confirmed')
      except Exception:
        try:
            self.course_model.force_close_attempt_zero(attempt_id)
        except Exception:
            self.logger.exception("force_close_attempt_zero fallback failed")

      return jsonify(ok=True)

    
    
    



    def api_exam_capture_frame(self):
      """
      Body: { attempt_id, frame_number/frame_no, image_base64, ... }
      - Nếu có image_base64: gọi AI detection (YOLO/MediaPipe)
      - Nếu không: dùng dữ liệu từ frontend (backward compatible)
      """
      try:
        data = request.get_json(force=True, silent=True) or {}
        attempt_id = (data.get("attempt_id") or "").strip()
        if not attempt_id:
            return jsonify(ok=False, error="missing attempt_id"), 400

        frame_no = int(data.get("frame_number") or data.get("frame_no") or 0)
        image_base64 = data.get("image_base64")
        
        # Debug logging
        debug_mode = os.getenv("AI_DEBUG", "0") == "1"
        if debug_mode:
            print(f"[CAPTURE-FRAME] Request received - attempt_id={attempt_id}, frame_no={frame_no}")
            print(f"[CAPTURE-FRAME] Has image_base64: {bool(image_base64)}")
            if image_base64:
                print(f"[CAPTURE-FRAME] image_base64 length: {len(image_base64) if isinstance(image_base64, str) else 'N/A'}")
                print(f"[CAPTURE-FRAME] image_base64 starts with: {image_base64[:50] if isinstance(image_base64, str) else 'N/A'}...")
        
        # AI Detection nếu có image
        ai_result = None
        face_count = 0
        att_score = 0.0
        suspicious_objects = []
        cheating_detected = False
        cheating_reason = None
        
        svc = None
        capture_result = None
        capture_path = None
        capture_rel = None
        capture_web = None
        capture_time = None

        if image_base64:
            try:
                if debug_mode:
                    print(f"[CAPTURE-FRAME] Calling camera_capture_service.capture_frame_from_base64()...")
                svc = get_camera_capture_service()
                capture_result = svc.capture_frame_from_base64(image_base64, attempt_id, frame_no)

                if debug_mode:
                    print(f"[CAPTURE-FRAME] Capture result success: {capture_result.get('success')}")
                    print(f"[CAPTURE-FRAME] Capture latency: {capture_result.get('latency_ms', 0)}ms")
                
                if capture_result.get("success"):
                    ai_result = capture_result.get("ai", {})
                    face_count = int(ai_result.get("face_count", 0))
                    att_score = float(ai_result.get("attention_score", 0.0))
                    suspicious_objects = ai_result.get("suspicious_objects", [])
                    cheating_detected = bool(ai_result.get("cheating_detected", False))
                    cheating_reason = ai_result.get("cheating_reason")
                    capture_path = capture_result.get("filepath")
                    capture_rel = capture_result.get("relative_filepath")
                    capture_web = capture_result.get("web_url")
                    capture_time = capture_result.get("captured_at")
                    
                    if debug_mode:
                        print(f"[CAPTURE-FRAME] AI Results:")
                        print(f"  - Face count: {face_count}")
                        print(f"  - Object count: {len(suspicious_objects)}")
                        print(f"  - Attention score: {att_score:.2f}")
                        print(f"  - Cheating detected: {cheating_detected}")
                        if suspicious_objects:
                            print(f"  - Suspicious objects: {[obj.get('type') for obj in suspicious_objects]}")
                else:
                    error_msg = capture_result.get("error", "Unknown error")
                    if debug_mode:
                        print(f"[CAPTURE-FRAME] Capture failed: {error_msg}")
                    # Fallback to frontend data if decode fails
                    face_count = int(data.get("face_count") or 0)
                    att_score = float(data.get("attention_score") or 0.0)
                    suspects = data.get("suspicious_objects") or ""
                    suspicious_objects = suspects if isinstance(suspects, list) else []
            except Exception as e:
                print(f"[CAPTURE-FRAME] AI detection error: {e}")
                if debug_mode:
                    import traceback
                    print(traceback.format_exc())
                # Fallback to frontend data
                face_count = int(data.get("face_count") or 0)
                att_score = float(data.get("attention_score") or 0.0)
                suspects = data.get("suspicious_objects") or ""
                suspicious_objects = suspects if isinstance(suspects, list) else []
        else:
            if debug_mode:
                print(f"[CAPTURE-FRAME] No image_base64 provided, using frontend data")
            # Backward compatible: use frontend-provided data
            face_count = int(data.get("face_count") or 0)
            att_score = float(data.get("attention_score") or 0.0)
            suspects = data.get("suspicious_objects") or ""
            suspicious_objects = suspects if isinstance(suspects, list) else []

        user_id, course_id = self.get_attempt_context(attempt_id)
        if not user_id or not course_id:
            # Return AI result even if DB context missing
            if ai_result:
                return jsonify(ok=True, ai=ai_result, skipped=True)
            return jsonify(ok=True, skipped=True)

        # Convert suspicious_objects to JSON string for DB
        objects_json = json.dumps(suspicious_objects) if suspicious_objects else ""

        labels = self._build_proctor_labels(user_id, course_id)
        snapshot_for_db = capture_rel
        evidence_info = None
        if (suspicious_objects or cheating_detected) and capture_path and svc:
            event_type = "cheating_detected" if cheating_detected else "suspicious_objects"
            evidence_info = svc.promote_evidence(
                capture_path,
                user_slug=labels["user_slug"],
                course_slug=labels["course_slug"],
                attempt_id=attempt_id,
                frame_no=frame_no,
                event_type=event_type,
                reason=cheating_reason if cheating_detected else json.dumps(suspicious_objects, ensure_ascii=False),
                captured_at=capture_time,
            )
            if evidence_info:
                snapshot_for_db = evidence_info.get("relative_path") or snapshot_for_db

        self.course_model.log_proctor_frame(
            attempt_id=attempt_id,
            user_id=user_id,
            course_id=course_id,
            frame_no=frame_no,
            face_count=face_count,
            attention_score=att_score,
            objects_json=objects_json,
            snapshot_url=snapshot_for_db,
        )

        if suspicious_objects or cheating_detected:
            event_type = "suspicious_objects" if suspicious_objects and not cheating_detected else "cheating_detected"
            meta_payload = {
                "objects": suspicious_objects,
                "reason": cheating_reason,
                "captured_at": capture_time,
                "frame_no": frame_no,
                "username": labels.get("username"),
                "course_title": labels.get("course_title"),
                "capture_url": capture_web,
            }
            if evidence_info:
                meta_payload["evidence_url"] = evidence_info.get("web_url")
                meta_payload["evidence_path"] = evidence_info.get("relative_path")

            self.course_model.log_proctor_event(
                attempt_id=attempt_id,
                user_id=user_id,
                course_id=course_id,
                event_type=event_type,
                confidence=1.0,
                meta_json=json.dumps(meta_payload, ensure_ascii=False),
            )

        # Return result với AI data
        result = {"ok": True, "frame_no": frame_no}
        if ai_result:
            result["ai"] = ai_result
            # Also include top-level fields for backward compatibility
            result["face_count"] = face_count
            result["attention_score"] = att_score
            result["suspicious_objects"] = suspicious_objects
            result["cheating_detected"] = cheating_detected
            if cheating_reason:
                result["cheating_reason"] = cheating_reason
        else:
            # Return basic info if no AI result
            result["face_count"] = face_count
            result["attention_score"] = att_score
            result["suspicious_objects"] = suspicious_objects
        
        if debug_mode:
            print(f"[CAPTURE-FRAME] Returning result: ok={result.get('ok')}, face_count={result.get('face_count')}, object_count={len(result.get('suspicious_objects', []))}")
        
        return jsonify(result)
      except Exception as e:
          import traceback
          print(f"[CAPTURE-FRAME] Error: {e}")
          print(traceback.format_exc())
          return jsonify(ok=False, error=str(e)), 500

    
    def api_doc_to_video(self):
        """
        POST /api/convert-doc-to-video
        form-data:
          - file: (pdf|docx|pptx)
          - title:   (optional) tiêu đề hiển thị
          - wpm:     (optional) tốc độ đọc
        return: { ok, video_url, caption_url, script_text }
        """
        try:
            print("Starting video creation process...")
            
            f = request.files.get("file")
            if not f or not f.filename:
                print("No file provided")
                return jsonify(ok=False, error="Thiếu file tài liệu"), 400

            print(f"File received: {f.filename}")
            
            title = (request.form.get("title") or "").strip()
            try:
                wpm = int(request.form.get("wpm") or 140)
            except Exception:
                wpm = 140

            print(f"Title: {title}, WPM: {wpm}")

            upload_dir = current_app.config.get("UPLOAD_FOLDER") or os.path.join("static", "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            src_name = f"{uuid.uuid4()}_{secure_filename(f.filename)}"
            src_path = os.path.join(upload_dir, src_name)
            f.save(src_path)
            
            print(f"File saved to: {src_path}")

            # thư mục xuất video
            out_dir = os.path.join("static", "uploads", "generated")
            os.makedirs(out_dir, exist_ok=True)
            
            print(f"Output directory: {out_dir}")

            # Sử dụng hệ thống hình ảnh thông minh mới - TUYỆT ĐỐI KHÔNG CÓ CON NGƯỜI
            try:
                print("[IMPORT] Importing doc_video_service...")
                from services.doc_video_service import make_video_from_file
                print("[OK] Import successful")
                
                print("[VIDEO] Creating video with Smart Image System...")
                video_title = title or os.path.splitext(f.filename)[0]
                print(f"  Title: {video_title}")
                print(f"  File: {src_path}")
                print(f"  Output: {out_dir}")
                
                result = make_video_from_file(src_path, out_dir, title=video_title)
                
                # Verify result
                if not result or "video_path" not in result:
                    print("[ERROR] No video_path in result")
                    return jsonify(ok=False, error="Video creation did not return valid path"), 500
                
                video_path = result["video_path"]
                if not os.path.exists(video_path):
                    print(f"[ERROR] Video file does not exist: {video_path}")
                    return jsonify(ok=False, error="Video file was not created"), 500
                
                print(f"[OK] Video created successfully: {video_path}")
                print("  Smart Image System - NO PEOPLE, CONTENT-MATCHED IMAGES")
                
            except ImportError as e:
                print(f"[ERROR] Import error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify(ok=False, error=f"Import error: {str(e)}"), 500
            except Exception as e:
                print(f"[ERROR] Video creation error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify(ok=False, error=f"Video creation failed: {str(e)}"), 500

            # Convert paths to URLs - Đảm bảo đúng format URL
            video_path = result["video_path"]
            video_url = "/" + video_path.replace(os.sep, "/").lstrip("/")
            caption_url = "/" + result["caption_path"].replace(os.sep, "/").lstrip("/") if "caption_path" in result else ""
            
            print(f"[URL] Video path: {video_path}")
            print(f"[URL] Video URL: {video_url}")
            print(f"[URL] Video exists: {os.path.exists(video_path)}")
            
            # Calculate approximate video statistics
            script_text = result.get("script_text", "")
            chunks = script_text.split("\n\n") if script_text else []
            approximate_duration = len(chunks) * 3  # Assume ~3 seconds per slide
            
            # Create lecture structure info for frontend
            lecture_structure = {
                "title": title or os.path.splitext(f.filename)[0],
                "slide_count": len(chunks),
                "total_duration": approximate_duration / 60,  # Convert to minutes
                "description": f"AI-generated lecture from {f.filename}"
            }
            
            print(f"\n{'='*60}")
            print(f"[SUCCESS] VIDEO CREATION COMPLETE!")
            print(f"{'='*60}")
            print(f"  Video URL: {video_url}")
            print(f"  Caption URL: {caption_url}")
            print(f"  Slides: {len(chunks)}")
            print(f"  Duration: ~{approximate_duration/60:.1f} minutes")
            print(f"  File exists: {os.path.exists(result['video_path'])}")
            print(f"{'='*60}\n")

            return jsonify(ok=True, 
                         video_url=video_url, 
                         caption_url=caption_url, 
                         script_text=script_text,
                         lecture_structure=lecture_structure)
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            current_app.logger.exception("convert-doc-to-video failed: %s", e)
            return jsonify(ok=False, error=f"Unexpected error: {str(e)}"), 500
        
        
        # --- ADD inside CourseController ---

    def get_attempt_context(self, attempt_id):
      """
      Trả về (user_id, course_id) từ cache hoặc DB
      """
      try:
        # dùng cache nếu bạn đang lưu attempt trong bộ nhớ
        ctx = self.ATTEMPT_CACHE.get(attempt_id) if hasattr(self, "ATTEMPT_CACHE") else None
      except Exception:
        ctx = None

      user_id = None
      course_id = None
      if ctx:
        user_id = ctx.get("user_id") or user_id
        course_id = ctx.get("course_id") or course_id

      if not (user_id and course_id):
        c_id, u_id = self.course_model.get_course_id_by_attempt(attempt_id)
        course_id = course_id or c_id
        user_id = user_id or u_id

    # fallback cuối cùng: lấy user từ session
      try:
        if not user_id:
            from flask import session
            user = session.get("user") or {}
            user_id = user.get("id")
      except Exception:
        pass

      return user_id, course_id

    def _build_proctor_labels(self, user_id, course_id):
      username = None
      course_title = None
      if user_id:
        try:
          user = self.user_model.get_user_by_id(int(user_id))
          if user:
            username = user.get("username") or user.get("email")
        except Exception:
          username = None
      if course_id:
        try:
          course = self.course_model.get_course_by_id(int(course_id))
          if course:
            try:
              course_dict = dict(course)
            except Exception:
              course_dict = course
            course_title = course_dict.get("title") or course_dict.get("name")
        except Exception:
          course_title = None

      user_slug = _slugify_label(username or f"user-{user_id or 'unknown'}", f"user-{user_id or 'unknown'}")
      course_slug = _slugify_label(course_title or f"course-{course_id or 'unknown'}", f"course-{course_id or 'unknown'}")
      return {
        "username": username,
        "course_title": course_title,
        "user_slug": user_slug,
        "course_slug": course_slug,
      }

    def ai_dashboard(self):
      """
      Trang bảng theo dõi AI (giáo viên)
      """
      from flask import render_template, redirect, url_for, session
      if session.get("role") != "teacher":
        return redirect(url_for("home"))

      # danh sách khóa học để filter
      courses_raw = self.course_model.get_all_courses()
      courses = []
      for course in courses_raw:
        try:
            courses.append(dict(course))
        except:
            courses.append({'id': course[0], 'title': course[1] if len(course)>1 else 'N/A'})
      return render_template("ai_dashboard.html", courses=courses)

    def api_ai_progress(self):
      if session.get("role") != "teacher":
        abort(403)
      course_id = request.args.get("course_id")
      items = self.course_model.get_ai_progress_overview(course_id=course_id, include_teachers=False)
      return jsonify({"ok": True, "items": items})


  
  
    def api_ai_status(self):
      from services.face_recognition_service import get_face_recognition_service
      s = get_face_recognition_service().debug_status()
      info = {
        "YOLO_FACE_ONNX": os.getenv("YOLO_FACE_ONNX"),
        "OBJECT_BACKEND": os.getenv("OBJECT_BACKEND"),
        "COCO_CLASSES": os.getenv("COCO_CLASSES"),
        "ALWAYS_ALERT_ON_OBJECTS": os.getenv("ALWAYS_ALERT_ON_OBJECTS"),
      }
      return jsonify(ok=True, status=s, env=info)



