import sqlite3
from typing import List, Dict, Any, Optional
import datetime
import uuid
import json

class CourseModel:
    """
    CourseModel manages:
    - courses (adds migration-safe columns)
    - course_sections (weeks/chapters)
    - course_items (items: video/reading/quiz/lesson)
    - user_progress (per-user/item progress)
    - exam-related tables (attempts, questions, answers)
    """
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._migrate_all()
        self._create_proctoring_tables()


    # ---------- Low-level database connection ----------
    def _connect(self):
      conn = sqlite3.connect(self.db_path, check_same_thread=False)
      conn.row_factory = sqlite3.Row
      conn.execute("PRAGMA foreign_keys = ON")
      # ĐẢM BẢO schema proctor tồn tại
      try:
        self._ensure_proctor_events_schema(conn)
      except Exception as e:
        print("[WARN] ensure_proctor_events_schema:", e)
      return conn

    # ---------- Database migrations ----------
    def _migrate_all(self):
        self._create_course_table()
        self.add_image_url_column_if_not_exists()
        self.add_video_url_column_if_not_exists()
        self.add_category_column_if_not_exists()
        self.add_tags_column_if_not_exists()
        self.add_caption_url_column_if_not_exists()
        self._create_sections_table()
        self._create_items_table()
        self._create_progress_table()
        self._create_exam_tables()
        self._create_segment_questions_table()
        self._create_comprehensive_exam_tables()

    def _create_course_table(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    image_url TEXT,
                    video_url TEXT,
                    caption_url TEXT,
                    category TEXT,
                    tags TEXT
                )
            """)
            conn.commit()

    def _create_sections_table(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS course_sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS ix_sections_course ON course_sections(course_id)")
            conn.commit()

    def _create_items_table(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS course_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER NOT NULL REFERENCES course_sections(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    item_type TEXT NOT NULL,   -- 'video' | 'reading' | 'quiz' | 'lesson'
                    resource_url TEXT,
                    duration_sec INTEGER,
                    content TEXT,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
            """)
            # Ensure 'content' column exists for old DBs
            cols = [r[1] for r in conn.execute("PRAGMA table_info(course_items)").fetchall()]
            if "content" not in cols:
                conn.execute("ALTER TABLE course_items ADD COLUMN content TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_items_section ON course_items(section_id)")
            conn.commit()

    def _create_progress_table(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                    item_id INTEGER NOT NULL REFERENCES course_items(id) ON DELETE CASCADE,
                    status TEXT NOT NULL DEFAULT 'not_started',   -- 'not_started'|'in_progress'|'done'
                    seconds_watched INTEGER DEFAULT 0,
                    score REAL,
                    completed_at TEXT,
                    UNIQUE(user_id, item_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS ix_prog_course_user ON user_progress(course_id, user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_prog_item ON user_progress(item_id)")
            conn.commit()

    # ---------- Courses API ----------
    def get_all_courses(self):
        with self._connect() as conn:
            return conn.execute("SELECT * FROM courses").fetchall()

    def get_course_by_id(self, course_id: int):
        with self._connect() as conn:
            return conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()

    def add_course(self, title: str, description: str, image_url: str, video_url: str,
                   caption_url: Optional[str], category: Optional[str], tags: Optional[str]) -> int:
        with self._connect() as conn:
            cur = conn.execute("""
                INSERT INTO courses (title, description, image_url, video_url, caption_url, category, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, description, image_url, video_url, caption_url, category, tags))
            conn.commit()
            return cur.lastrowid

    def update_course(self, course_id: int, title: str, description: str, image_url: str, video_url: str,
                      caption_url: Optional[str], category: Optional[str], tags: Optional[str]):
        with self._connect() as conn:
            conn.execute("""
                UPDATE courses
                   SET title=?, description=?, image_url=?, video_url=?, caption_url=?, category=?, tags=?
                 WHERE id=?
            """, (title, description, image_url, video_url, caption_url, category, tags, course_id))
            conn.commit()

    def delete_course(self, course_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
            conn.commit()

    def _get_existing_columns(self, conn):
        cur = conn.execute("PRAGMA table_info(courses)")
        return [col[1] for col in cur.fetchall()]

    def add_image_url_column_if_not_exists(self):
        with self._connect() as conn:
            cols = self._get_existing_columns(conn)
            if "image_url" not in cols:
                conn.execute("ALTER TABLE courses ADD COLUMN image_url TEXT")
                conn.commit()

    def add_video_url_column_if_not_exists(self):
        with self._connect() as conn:
            cols = self._get_existing_columns(conn)
            if "video_url" not in cols:
                conn.execute("ALTER TABLE courses ADD COLUMN video_url TEXT")
                conn.commit()

    def add_category_column_if_not_exists(self):
        with self._connect() as conn:
            cols = self._get_existing_columns(conn)
            if "category" not in cols:
                conn.execute("ALTER TABLE courses ADD COLUMN category TEXT")
                conn.commit()

    def add_tags_column_if_not_exists(self):
        with self._connect() as conn:
            cols = self._get_existing_columns(conn)
            if "tags" not in cols:
                conn.execute("ALTER TABLE courses ADD COLUMN tags TEXT")
                conn.commit()

    def add_caption_url_column_if_not_exists(self):
        with self._connect() as conn:
            cols = self._get_existing_columns(conn)
            if "caption_url" not in cols:
                conn.execute("ALTER TABLE courses ADD COLUMN caption_url TEXT")
                conn.commit()

    def get_related_by_category(self, category: Optional[str], exclude_id: Optional[int] = None, limit: int = 6):
        if not category:
            return []
        with self._connect() as conn:
            if exclude_id is not None:
                sql = """
                    SELECT * FROM courses
                     WHERE id <> ?
                       AND category IS NOT NULL AND TRIM(category) <> ''
                       AND LOWER(category) = LOWER(?)
                     ORDER BY id DESC
                     LIMIT ?
                """
                return conn.execute(sql, (exclude_id, category, limit)).fetchall()
            else:
                sql = """
                    SELECT * FROM courses
                     WHERE category IS NOT NULL AND TRIM(category) <> ''
                       AND LOWER(category) = LOWER(?)
                     ORDER BY id DESC
                     LIMIT ?
                """
                return conn.execute(sql, (category, limit)).fetchall()

    # ---------- Outline (Sections & Items) ----------
    def add_section(self, course_id: int, title: str, sort_order: Optional[int] = None) -> int:
        with self._connect() as conn:
            if sort_order is None:
                row = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM course_sections WHERE course_id=?",
                    (course_id,)
                ).fetchone()
                sort_order = row[0] if row else 0
            cur = conn.execute(
                "INSERT INTO course_sections(course_id, title, sort_order) VALUES (?,?,?)",
                (course_id, title, sort_order)
            )
            conn.commit()
            return cur.lastrowid

    def update_section(self, section_id: int, title: Optional[str] = None, sort_order: Optional[int] = None):
        with self._connect() as conn:
            if title is not None:
                conn.execute("UPDATE course_sections SET title=? WHERE id=?", (title, section_id))
            if sort_order is not None:
                conn.execute("UPDATE course_sections SET sort_order=? WHERE id=?", (sort_order, section_id))
            conn.commit()

    def delete_section(self, section_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM course_sections WHERE id=?", (section_id,))
            conn.commit()

    def add_item(self, section_id: int, title: str, item_type: str,
                 resource_url: Optional[str] = None, duration_sec: Optional[int] = None,
                 content: Optional[str] = None, sort_order: Optional[int] = None) -> int:
        with self._connect() as conn:
            if sort_order is None:
                row = conn.execute(
                    "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM course_items WHERE section_id=?",
                    (section_id,)
                ).fetchone()
                sort_order = row[0] if row else 0
            cur = conn.execute("""
                INSERT INTO course_items(section_id, title, item_type, resource_url, duration_sec, content, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (section_id, title, item_type, resource_url, duration_sec, content, sort_order))
            conn.commit()
            return cur.lastrowid

    def update_item(self, item_id: int, **kwargs):
        # allowed: title, item_type, resource_url, duration_sec, content, sort_order, section_id
        if not kwargs:
            return
        fields, values = [], []
        for k in ["title", "item_type", "resource_url", "duration_sec", "content", "sort_order", "section_id"]:
            if k in kwargs and kwargs[k] is not None:
                fields.append(f"{k}=?")
                values.append(kwargs[k])
        if not fields:
            return
        values.append(item_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE course_items SET {', '.join(fields)} WHERE id=?", values)
            conn.commit()

    def delete_item(self, item_id: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM course_items WHERE id=?", (item_id,))
            conn.commit()

    def set_item_duration(self, item_id: int, duration_sec: int):
        with self._connect() as conn:
            conn.execute("UPDATE course_items SET duration_sec=? WHERE id=?", (duration_sec, item_id))
            conn.commit()

    def replace_outline(self, course_id: int, sections_payload: list):
        """
        sections_payload = [
            {"title": "Module 1", "items": [
                {"title": "Bài 1", "item_type": "video", "resource_url": "/static/uploads/v1.mp4",
                 "duration_sec": 600, "content": "Nội dung HTML/Markdown..."}
            ]},
            ...
        ]
        """
        with self._connect() as conn:
            # Remove old sections/items
            conn.execute("DELETE FROM course_sections WHERE course_id=?", (course_id,))
            s_order = 0
            for s in sections_payload or []:
                cur = conn.execute(
                    "INSERT INTO course_sections(course_id, title, sort_order) VALUES (?, ?, ?)",
                    (course_id, s.get("title", "Module"), s_order)
                )
                s_id = cur.lastrowid
                s_order += 1
                i_order = 0
                for it in (s.get("items") or []):
                    conn.execute("""
                        INSERT INTO course_items(section_id, title, item_type, resource_url, duration_sec, content, sort_order)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        s_id,
                        it.get("title", "Bài học"),
                        it.get("item_type", "lesson"),
                        it.get("resource_url"),
                        it.get("duration_sec"),
                        it.get("content"),
                        i_order
                    ))
                    i_order += 1
            conn.commit()

    def get_outline(self, course_id: int):
        with self._connect() as conn:
            secs = conn.execute(
                "SELECT * FROM course_sections WHERE course_id=? ORDER BY sort_order, id",
                (course_id,)
            ).fetchall()
            items = conn.execute("""
                SELECT i.* FROM course_items i
                JOIN course_sections s ON s.id = i.section_id
                WHERE s.course_id=?
                ORDER BY s.sort_order, i.sort_order, i.id
            """, (course_id,)).fetchall()
        sec_map: Dict[int, Dict[str, Any]] = {s["id"]: {**dict(s), "items": []} for s in secs}
        for it in items:
            sec_map[it["section_id"]]["items"].append(dict(it))
        sections = sorted(sec_map.values(), key=lambda x: int(x.get("sort_order") or 0))
        for s in sections:
            s["items"] = sorted(s["items"], key=lambda x: int(x.get("sort_order") or 0))
        return sections

    # ---------- Progress ----------
    def upsert_progress(self, user_id: int, course_id: int, item_id: int,
                        status: str = "in_progress",
                        seconds_watched: Optional[int] = None,
                        score: Optional[float] = None,
                        completed_at: Optional[str] = None):
        if completed_at is None and status == "done":
            completed_at = datetime.datetime.utcnow().isoformat(" ")
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO user_progress(user_id, course_id, item_id, status, seconds_watched, score, completed_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET
                   status = excluded.status,
                   seconds_watched = MAX(user_progress.seconds_watched, COALESCE(excluded.seconds_watched,0)),
                   score = COALESCE(excluded.score, user_progress.score),
                   completed_at = CASE 
                       WHEN excluded.status='done' THEN COALESCE(excluded.completed_at, user_progress.completed_at)
                       ELSE user_progress.completed_at
                   END
            """, (user_id, course_id, item_id, status, seconds_watched or 0, score, completed_at))
            conn.commit()

    def mark_item_done(self, user_id: int, course_id: int, item_id: int, seconds_watched: Optional[int] = None):
        self.upsert_progress(user_id, course_id, item_id, status="done", seconds_watched=seconds_watched)

    def get_user_progress(self, course_id: int, user_id: int) -> Dict[int, Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT item_id, status, seconds_watched, score, completed_at
                  FROM user_progress
                 WHERE user_id=? AND course_id=?
            """, (user_id, course_id)).fetchall()
        return {r["item_id"]: dict(r) for r in rows}

    def get_completion(self, course_id: int, user_id: int) -> Dict[str, Any]:
        """% completed = done items / total items."""
        with self._connect() as conn:
            total = conn.execute("""
                SELECT COUNT(i.id) FROM course_items i
                JOIN course_sections s ON s.id=i.section_id
                WHERE s.course_id=?
            """, (course_id,)).fetchone()[0]
            done = conn.execute("""
                SELECT COUNT(1) FROM user_progress
                 WHERE course_id=? AND user_id=? AND status='done'
            """, (course_id, user_id)).fetchone()[0]
        pct = (done * 100.0 / total) if total else 0.0
        return {"total_items": total, "done_items": done, "percent": round(pct, 2)}

    # ---------- Exam Tables ----------
    def _create_exam_tables(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exam_attempts (
                    id TEXT PRIMARY KEY,
                    course_id INTEGER,
                    user_id INTEGER,
                    started_at TEXT,
                    ended_at TEXT,
                    cheated INTEGER DEFAULT 0,
                    score REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exam_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT,
                    qid TEXT,
                    qtype TEXT,
                    question TEXT,
                    options_json TEXT,
                    correct_hash TEXT,
                    rubric_json TEXT,
                    cue_text TEXT,
                    topic_hash TEXT,
                    time_limit_ms INTEGER,
                    asked_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS exam_answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT,
                    qid TEXT,
                    answer TEXT,
                    correct INTEGER,
                    time_spent_ms INTEGER,
                    submitted_at TEXT
                )
            """)
            conn.commit()

    # Exam API (logging)
    def create_attempt(self, course_id: int, user_id: int) -> str:
        attempt_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO exam_attempts(id, course_id, user_id, started_at, cheated) VALUES(?,?,?,?,0)",
                (attempt_id, course_id, user_id, datetime.datetime.utcnow().isoformat(" "))
            )
            conn.commit()
        return attempt_id

    def log_question(self, attempt_id: str, qa: dict):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO exam_questions(attempt_id, qid, qtype, question, options_json, correct_hash,
                                           rubric_json, cue_text, topic_hash, time_limit_ms, asked_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                attempt_id,
                qa.get("qid"),
                qa.get("type"),
                qa.get("question"),
                json.dumps(qa.get("options") or [], ensure_ascii=False),
                qa.get("correct_hash"),
                json.dumps(qa.get("rubric") or {}, ensure_ascii=False),
                qa.get("cue_text"),
                qa.get("topic_hash"),
                int(qa.get("time_limit_ms") or 0),
                datetime.datetime.utcnow().isoformat(" ")
            ))
            conn.commit()

    def log_answer(self, attempt_id: str, qid: str, answer: str, correct: bool, time_spent_ms: int):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO exam_answers(attempt_id, qid, answer, correct, time_spent_ms, submitted_at)
                VALUES (?,?,?,?,?,?)
            """, (
                attempt_id,
                qid,
                str(answer),
                int(bool(correct)),
                int(time_spent_ms),
                datetime.datetime.utcnow().isoformat(" ")
            ))
            conn.commit()

    def finish_attempt(self, attempt_id: str, score: float, cheated: bool):
        with self._connect() as conn:
            conn.execute("""
                UPDATE exam_attempts
                   SET ended_at=?, cheated=?, score=?
                 WHERE id=?
            """, (
                datetime.datetime.utcnow().isoformat(" "),
                int(bool(cheated)),
                float(score),
                attempt_id
            ))
            conn.commit()

    def get_exam_results(self, attempt_id: str):
        """Lấy tất cả câu hỏi và câu trả lời của một attempt để AI phân tích"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Lấy tất cả câu hỏi
            cursor.execute("""
                SELECT qid, qtype, question, options_json, correct_hash, rubric_json, topic_hash
                FROM exam_questions
                WHERE attempt_id = ?
                ORDER BY asked_at
            """, (attempt_id,))
            questions = []
            for row in cursor.fetchall():
                questions.append({
                    "qid": row[0],
                    "type": row[1],
                    "question": row[2],
                    "options": json.loads(row[3] or "[]"),
                    "correct_hash": row[4],
                    "rubric": json.loads(row[5] or "{}"),
                    "topic_hash": row[6]
                })
            
            # Lấy tất cả câu trả lời
            cursor.execute("""
                SELECT qid, answer, time_spent_ms, submitted_at
                FROM exam_answers
                WHERE attempt_id = ?
                ORDER BY submitted_at
            """, (attempt_id,))
            answers = {}
            for row in cursor.fetchall():
                answers[row[0]] = {
                    "answer": row[1],
                    "time_spent_ms": row[2],
                    "submitted_at": row[3]
                }
            
            # Kết hợp câu hỏi và câu trả lời
            results = []
            for q in questions:
                qid = q["qid"]
                answer_data = answers.get(qid, {})
                results.append({
                    **q,
                    "user_answer": answer_data.get("answer", ""),
                    "time_spent_ms": answer_data.get("time_spent_ms", 0),
                    "submitted_at": answer_data.get("submitted_at")
                })
            
            return results

    def _create_segment_questions_table(self):
        """Tạo bảng lưu câu hỏi đã pre-generate cho từng segment 50s"""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS segment_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    segment_start INTEGER NOT NULL,
                    segment_end INTEGER NOT NULL,
                    question TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    correct_index INTEGER NOT NULL,
                    explanation TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(course_id, segment_start)
                )
            """)
            conn.commit()

    def insert_segment_question(self, course_id: int, segment_start: int, segment_end: int,
                               question: str, options: list, correct_index: int, explanation: str = ""):
        """Lưu câu hỏi cho một segment"""
        import json
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO segment_questions 
                (course_id, segment_start, segment_end, question, options_json, correct_index, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (course_id, segment_start, segment_end, question, json.dumps(options), correct_index, explanation))
            conn.commit()

    def get_segment_question(self, course_id: int, segment_start: int):
        """Lấy câu hỏi cho một segment"""
        import json
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT question, options_json, correct_index, explanation, segment_start, segment_end
                FROM segment_questions
                WHERE course_id = ? AND segment_start = ?
            """, (course_id, segment_start))
            row = cursor.fetchone()
            if row:
                return {
                    "question": row[0],
                    "options": json.loads(row[1]),
                    "correct_index": row[2],
                    "explanation": row[3] or "",
                    "segment_start": row[4],
                    "segment_end": row[5]
                }
            return None

    def get_all_segment_questions(self, course_id: int):
        """Lấy tất cả câu hỏi đã pre-generate cho một course"""
        import json
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT segment_start, segment_end, question, options_json, correct_index, explanation
                FROM segment_questions
                WHERE course_id = ?
                ORDER BY segment_start
            """, (course_id,))
            results = []
            for row in cursor.fetchall():
                results.append({
                    "segment_start": row[0],
                    "segment_end": row[1],
                    "question": row[2],
                    "options": json.loads(row[3]),
                    "correct_index": row[4],
                    "explanation": row[5] or ""
                })
            return results

    def delete_segment_questions(self, course_id: int):
        """Xóa tất cả câu hỏi của một course (để regenerate)"""
        with self._connect() as conn:
            conn.execute("DELETE FROM segment_questions WHERE course_id = ?", (course_id,))
            conn.commit()

    def _create_comprehensive_exam_tables(self):
        """Tạo bảng cho comprehensive exam (20 câu, 15 phút)"""
        import datetime
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comprehensive_exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    course_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    attempt_id TEXT UNIQUE NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    time_limit_seconds INTEGER DEFAULT 900,
                    total_questions INTEGER DEFAULT 20,
                    completed_questions INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    score REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'in_progress',
                    strengths_analysis TEXT,
                    weaknesses_analysis TEXT,
                    course_recommendations TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comprehensive_exam_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attempt_id TEXT NOT NULL,
                    question_index INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    correct_index INTEGER NOT NULL,
                    segment_start INTEGER,
                    segment_end INTEGER,
                    selected_index INTEGER,
                    is_correct INTEGER DEFAULT 0,
                    time_spent_seconds REAL DEFAULT 0.0,
                    answered_at TEXT
                )
            """)
            conn.commit()

    def create_comprehensive_exam(self, course_id: int, user_id: int, time_limit: int = 900) -> str:
        """Tạo một comprehensive exam attempt"""
        import datetime
        attempt_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO comprehensive_exams 
                (course_id, user_id, attempt_id, started_at, time_limit_seconds, total_questions, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (course_id, user_id, attempt_id, datetime.datetime.utcnow().isoformat(), time_limit, 20, 'in_progress'))
            conn.commit()
        return attempt_id

    def save_comprehensive_exam_question(self, attempt_id: str, question_index: int, question_text: str, 
                                         options: list, correct_index: int, segment_start: int = None, 
                                         segment_end: int = None):
        """Lưu câu hỏi vào exam"""
        import json
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO comprehensive_exam_questions
                (attempt_id, question_index, question_text, options_json, correct_index, segment_start, segment_end)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (attempt_id, question_index, question_text, json.dumps(options), correct_index, segment_start, segment_end))
            conn.commit()

    def submit_comprehensive_exam_answer(self, attempt_id: str, question_index: int, selected_index: int, time_spent: float):
        """Submit đáp án cho một câu hỏi"""
        import datetime
        import json
        with self._connect() as conn:
            cursor = conn.cursor()
            # Lấy correct_index từ question
            cursor.execute("""
                SELECT correct_index FROM comprehensive_exam_questions
                WHERE attempt_id = ? AND question_index = ?
            """, (attempt_id, question_index))
            row = cursor.fetchone()
            if row:
                correct_index = row[0]
                is_correct = 1 if selected_index == correct_index else 0
                
                cursor.execute("""
                    UPDATE comprehensive_exam_questions
                    SET selected_index = ?, is_correct = ?, time_spent_seconds = ?, answered_at = ?
                    WHERE attempt_id = ? AND question_index = ?
                """, (selected_index, is_correct, time_spent, datetime.datetime.utcnow().isoformat(), attempt_id, question_index))
                conn.commit()

    def finish_comprehensive_exam(self, attempt_id: str, strengths: str = None, weaknesses: str = None, 
                                 recommendations: str = None):
        """Hoàn thành exam và tính điểm"""
        import datetime
        import json
        with self._connect() as conn:
            cursor = conn.cursor()
            # Tính điểm
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(is_correct) as correct,
                    AVG(time_spent_seconds) as avg_time
                FROM comprehensive_exam_questions
                WHERE attempt_id = ? AND selected_index IS NOT NULL
            """, (attempt_id,))
            row = cursor.fetchone()
            if row:
                total = row[0] or 0
                correct = row[1] or 0
                score = round((correct / total * 100) if total > 0 else 0, 2)
                
                # Update exam
                cursor.execute("""
                    UPDATE comprehensive_exams
                    SET ended_at = ?, completed_questions = ?, correct_answers = ?, score = ?, status = ?,
                        strengths_analysis = ?, weaknesses_analysis = ?, course_recommendations = ?
                    WHERE attempt_id = ?
                """, (datetime.datetime.utcnow().isoformat(), total, correct, score, 'completed', 
                      strengths, weaknesses, recommendations, attempt_id))
                conn.commit()
                return score
        return 0.0

    def get_all_exam_scores_for_teacher(self, course_id: int = None):
      """
      Gom điểm cho giáo viên từ 2 nguồn:
      - comprehensive_exams (luồng mới)
      - student_submissions  (luồng cũ submit_exam)
      Trả về: user, course, attempt_count, highest_score, average_score.
      """
      with self._connect() as conn:
        params_ce = []
        where_ce = ""
        if course_id:
            where_ce = "AND ce.course_id = ?"
            params_ce.append(course_id)

        # Nguồn 1: comprehensive_exams (mỗi bản ghi là 1 attempt với score đã tính sẵn)
        sql_ce = f"""
        SELECT ce.user_id AS user_id,
               ce.course_id AS course_id,
               ce.score AS score
          FROM comprehensive_exams ce
         WHERE ce.status IN ('completed','terminated') {where_ce}
        """

        # Nguồn 2: student_submissions (gộp theo attempt_id nếu có; nếu không thì gộp theo ngày)
        params_ss = []
        where_ss = ""
        if course_id:
            where_ss = "WHERE COALESCE(s.course_id, q.course_id) = ?"
            params_ss.append(course_id)

        sql_ss = f"""
        SELECT s.student_id AS user_id,
               COALESCE(s.course_id, q.course_id) AS course_id,
               ROUND(SUM(s.score) * 100.0 / COUNT(1), 2) AS score
          FROM student_submissions s
          LEFT JOIN questions q ON q.id = s.question_id
          {where_ss}
         GROUP BY s.student_id, COALESCE(s.course_id, q.course_id),
                  COALESCE(s.attempt_id, DATE(s.submitted_at))
        """

        sql = f"""
        WITH raw AS (
            {sql_ce}
            UNION ALL
            {sql_ss}
        )
        SELECT u.id AS user_id, u.username,
               c.id AS course_id, c.title AS course_title,
               COUNT(1)                       AS attempt_count,
               COALESCE(MAX(raw.score), 0)    AS highest_score,
               ROUND(COALESCE(AVG(raw.score),0), 2) AS average_score
          FROM raw
          JOIN users   u ON u.id = raw.user_id
          JOIN courses c ON c.id = raw.course_id
         GROUP BY u.id, u.username, c.id, c.title
         ORDER BY u.username, c.id
        """
        rows = conn.execute(sql, params_ce + params_ss).fetchall()
        try:
            return [dict(r) for r in rows]
        except Exception:
            out = []
            for r in rows:
                out.append({
                    "user_id": r[0], "username": r[1],
                    "course_id": r[2], "course_title": r[3],
                    "attempt_count": r[4],
                    "highest_score": float(r[5] or 0),
                    "average_score": float(r[6] or 0),
                })
            return out

    def get_user_exam_details(self, user_id: int, course_id: int | None = None) -> list[dict]:
      """
      Trả về danh sách các lần làm bài của 1 user (lọc theo course nếu truyền vào).
      Hợp nhất:
      - comprehensive_exams (luồng mới)
      - student_submissions + questions (legacy)
       Không để cột mơ hồ: mọi course_id/user_id đều prefix alias.
      """
      with self._connect() as conn:
        cur = conn.cursor()

        # --- 1) comprehensive_exams ---
        params_ce = [user_id]
        where_ce = "ce.user_id = ?"
        if course_id:
            where_ce += " AND ce.course_id = ?"
            params_ce.append(course_id)

        sql_ce = f"""
        SELECT
            ce.attempt_id                     AS attempt_id,
            ce.user_id                        AS user_id,
            ce.course_id                      AS course_id,
            c.title                           AS course_title,
            ce.started_at                     AS started_at,
            ce.ended_at                       AS ended_at,
            ce.score                          AS score,
            ce.status                         AS status,
            (
                SELECT COUNT(1)
                FROM comprehensive_exam_questions q
                WHERE q.attempt_id = ce.attempt_id
                  AND q.selected_index IS NOT NULL
            )                                  AS completed
        FROM comprehensive_exams AS ce
        LEFT JOIN courses AS c ON c.id = ce.course_id
        WHERE {where_ce}
        """

        # --- 2) legacy: student_submissions (+ questions để lấy course_id chuẩn) ---
        params_legacy = [user_id]
        where_legacy = "s.student_id = ?"
        if course_id:
            where_legacy += " AND COALESCE(s.course_id, q.course_id) = ?"
            params_legacy.append(course_id)

        sql_legacy = f"""
        SELECT
            -- gom theo attempt_id; nếu thiếu attempt_id thì gom theo ngày + user + course
            COALESCE(
                s.attempt_id,
                'legacy-' || DATE(s.submitted_at) || '-' || s.student_id || '-' || COALESCE(s.course_id, q.course_id)
            )                                   AS attempt_id,
            s.student_id                         AS user_id,
            COALESCE(s.course_id, q.course_id)   AS course_id,
            c.title                              AS course_title,
            MIN(s.submitted_at)                  AS started_at,
            MAX(s.submitted_at)                  AS ended_at,
            ROUND(SUM(s.score) * 100.0 / COUNT(1), 2) AS score,
            'completed'                          AS status,
            COUNT(1)                             AS completed
        FROM student_submissions AS s
        LEFT JOIN questions AS q ON q.id = s.question_id
        LEFT JOIN courses   AS c ON c.id = COALESCE(s.course_id, q.course_id)
        WHERE {where_legacy}
        GROUP BY attempt_id, s.student_id, COALESCE(s.course_id, q.course_id)
        """

        # --- UNION và sắp xếp ngoài cùng theo alias ---
        sql = f"""
        SELECT * FROM (
            {sql_ce}
            UNION ALL
            {sql_legacy}
        ) AS all_attempts
        ORDER BY all_attempts.ended_at DESC, all_attempts.started_at DESC
        """

        rows = cur.execute(sql, params_ce + params_legacy).fetchall()

        # Chuẩn hoá list[dict]
        out = []
        for r in rows:
            try:
                out.append(dict(r))
            except Exception:
                cols = [c[0] for c in cur.description]
                out.append({k: v for k, v in zip(cols, r)})
        return out

    
    def update_exam_score(self, attempt_id: str, new_score: float):
        """Cập nhật điểm cho một exam attempt"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Tính lại correct_answers dựa trên score
            cursor.execute("SELECT total_questions FROM comprehensive_exams WHERE attempt_id = ?", (attempt_id,))
            row = cursor.fetchone()
            if row:
                total_questions = row[0] or 20
                correct_answers = int((new_score / 100) * total_questions)
                
                cursor.execute("""
                    UPDATE comprehensive_exams
                    SET score = ?, correct_answers = ?
                    WHERE attempt_id = ?
                """, (new_score, correct_answers, attempt_id))
                conn.commit()
                return True
            return False
    
    def delete_exam_attempt(self, attempt_id: str):
        """Xóa một exam attempt"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Xóa các câu hỏi trước
            cursor.execute("DELETE FROM comprehensive_exam_questions WHERE attempt_id = ?", (attempt_id,))
            # Xóa exam
            cursor.execute("DELETE FROM comprehensive_exams WHERE attempt_id = ?", (attempt_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_comprehensive_exam_results(self, attempt_id: str):
        """Lấy kết quả exam"""
        import json
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM comprehensive_exams WHERE attempt_id = ?
            """, (attempt_id,))
            exam_row = cursor.fetchone()
            if exam_row:
                cursor.execute("""
                    SELECT * FROM comprehensive_exam_questions
                    WHERE attempt_id = ? ORDER BY question_index
                """, (attempt_id,))
                questions = []
                for q_row in cursor.fetchall():
                    questions.append({
                        "index": q_row[2],
                        "question": q_row[3],
                        "options": json.loads(q_row[4]),
                        "correct_index": q_row[5],
                        "selected_index": q_row[7],
                        "is_correct": q_row[8],
                        "time_spent": q_row[9]
                    })
                return {
                    "attempt_id": attempt_id,
                    "course_id": exam_row[1],
                    "score": exam_row[10],
                    "completed": exam_row[8],
                    "correct": exam_row[9],
                    "total": exam_row[7],
                    "strengths": exam_row[12],
                    "weaknesses": exam_row[13],
                    "recommendations": exam_row[14],
                    "questions": questions
                }
            return None
    # --- PROCTORING TABLES & HELPERS (ADD THESE METHODS INSIDE CourseModel) ---

    def _create_proctoring_tables(self):
      """
      Tạo 2 bảng proctor nếu chưa có. Gọi an toàn nhiều lần.
      """
      with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
        cur = conn.cursor()
        # Lưu khung hình + mức tập trung
        cur.execute("""
            CREATE TABLE IF NOT EXISTS proctor_frames (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id   TEXT NOT NULL,
                user_id      INTEGER,
                course_id    INTEGER,
                frame_no     INTEGER,
                face_count   INTEGER,
                attention_score REAL,
                objects_json TEXT,
                snapshot_url TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Lưu sự kiện cảnh báo/gian lận
        cur.execute("""
            CREATE TABLE IF NOT EXISTS proctor_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attempt_id   TEXT NOT NULL,
                user_id      INTEGER,
                course_id    INTEGER,
                event_type   TEXT,       -- 'warn' | 'block' | 'cheating' | 'suspicious_objects'...
                reason       TEXT,       -- lý do chi tiết nếu có
                confidence   REAL DEFAULT 1.0,
                meta_json    TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Index cơ bản
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pf_attempt ON proctor_frames(attempt_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pf_user ON proctor_frames(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pf_course ON proctor_frames(course_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pe_attempt ON proctor_events(attempt_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pe_user ON proctor_events(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_pe_course ON proctor_events(course_id)")
        conn.commit()
        # Đảm bảo cột mới (nếu DB cũ)
        self._ensure_proctor_events_schema(conn)


    def _ensure_proctor_events_schema(self, conn):
      """
      Bảo toàn schema khi DB đã tồn tại từ trước.
      - Bổ sung các cột còn thiếu (reason/confidence/meta_json/snapshot_url)
      """
      def _cols(tbl):
        cur = conn.execute(f"PRAGMA table_info({tbl})")
        return {row[1] for row in cur.fetchall()}

    # proctor_events
      pe = _cols("proctor_events")
      with conn:
        if "event_type" not in pe:
            conn.execute("ALTER TABLE proctor_events ADD COLUMN event_type TEXT")
        if "reason" not in pe:
            conn.execute("ALTER TABLE proctor_events ADD COLUMN reason TEXT")
        if "confidence" not in pe:
            conn.execute("ALTER TABLE proctor_events ADD COLUMN confidence REAL DEFAULT 1.0")
        if "meta_json" not in pe:
            conn.execute("ALTER TABLE proctor_events ADD COLUMN meta_json TEXT")

    # proctor_frames
      pf = _cols("proctor_frames")
      with conn:
        if "snapshot_url" not in pf:
            conn.execute("ALTER TABLE proctor_frames ADD COLUMN snapshot_url TEXT")
        if "objects_json" not in pf:
            conn.execute("ALTER TABLE proctor_frames ADD COLUMN objects_json TEXT")
        if "attention_score" not in pf:
            conn.execute("ALTER TABLE proctor_frames ADD COLUMN attention_score REAL")


    def log_proctor_frame(self, attempt_id: str, user_id: int, course_id: int,
                      frame_no: int, face_count: int, attention_score: float,
                      objects_json: str = None, snapshot_url: str = None):
      """
      Lưu 1 khung hình giám sát.
      """
      with self._connect() as conn:
        conn.execute("""
            INSERT INTO proctor_frames (attempt_id, user_id, course_id, frame_no, face_count,
                                        attention_score, objects_json, snapshot_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (attempt_id, user_id, course_id, int(frame_no or 0), int(face_count or 0),
              float(attention_score or 0.0), objects_json, snapshot_url))
        conn.commit()


    def log_proctor_event(self, attempt_id: str, user_id: int, course_id: int,
                      event: str = None, reason: str = None, meta: str = None,
                      event_type: str = None, confidence: float = 1.0, meta_json: str = None):
      """
      Lưu sự kiện giám sát. Hỗ trợ cả hai chữ ký:
        - log_proctor_event(..., event=..., reason=..., meta=...)
        - log_proctor_event(..., event_type=..., confidence=..., meta_json=...)
      """
      evt = (event_type or event or "").strip() or "event"
      mjs = meta_json if meta_json is not None else meta
      with self._connect() as conn:
        conn.execute("""
            INSERT INTO proctor_events (attempt_id, user_id, course_id, event_type, reason, confidence, meta_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (attempt_id, user_id, course_id, evt, reason, float(confidence or 1.0), mjs))
        conn.commit()

        
    def get_course_id_by_attempt(self, attempt_id):
      with self._connect() as conn:
        cur = conn.cursor()
        # 1) thử comprehensive_exams
        cur.execute("""SELECT course_id, user_id FROM comprehensive_exams
                       WHERE attempt_id=? ORDER BY id DESC LIMIT 1""", (attempt_id,))
        row = cur.fetchone()
        if row: return row[0], row[1]
        # 2) fallback exam_attempts
        cur.execute("""SELECT course_id, user_id FROM exam_attempts
                       WHERE id=? LIMIT 1""", (attempt_id,))
        row = cur.fetchone()
        return (row[0], row[1]) if row else (None, None)
    
    def get_ai_progress(self, course_id: int = None):
      sql = """
      SELECT
      u.username, u.email,
      c.title AS course_title,
      COUNT(ce.id) AS attempt_count,
      COALESCE(MAX(ce.score), 0) AS highest_score,
      ROUND(COALESCE(AVG(ce.score), 0), 2) AS average_score,
      -- cheat_events: tính từ proctor_events
      COALESCE((
        SELECT COUNT(1) FROM proctor_events pe
        WHERE pe.user_id = ce.user_id
          AND pe.course_id = ce.course_id
          AND pe.event_type IN ('cheat','terminated','multiple_faces','multiple_faces_detected',
                                'suspicious_objects','camera_denied','face_mismatch',
                                'face_monitoring_failed','page_hide','window_blur')
      ),0) AS cheat_events,
      -- focus_percent: trung bình attention_score
      ROUND(COALESCE((
        SELECT AVG(pf.attention_score) FROM proctor_frames pf
        WHERE pf.user_id = ce.user_id AND pf.course_id = ce.course_id
      ),0),1) AS focus_percent,
      -- last_seen: sự kiện proctor gần nhất hoặc lần làm bài gần nhất
      COALESCE((
        SELECT MAX(created_at) FROM proctor_events pe
        WHERE pe.user_id = ce.user_id AND pe.course_id = ce.course_id
      ), ce.ended_at, ce.started_at) AS last_seen,
      -- behavior_analysis: text ngắn gọn
      CASE
        WHEN EXISTS(SELECT 1 FROM proctor_events pe
                    WHERE pe.user_id=ce.user_id AND pe.course_id=ce.course_id
                      AND pe.event_type IN ('cheat','terminated')) THEN 'Phát hiện gian lận'
        ELSE '—'
      END AS behavior_analysis
    FROM comprehensive_exams ce
    JOIN users u ON u.id = ce.user_id
    JOIN courses c ON c.id = ce.course_id
    WHERE ce.status IN ('completed','terminated')
    """
      params = []
      if course_id:
        sql += " AND ce.course_id = ?"
        params.append(course_id)
      sql += """
      GROUP BY u.id, c.id
      ORDER BY last_seen DESC
      """
      with self._connect() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]



    # model/course_model.py
    def get_ai_progress_overview(self, course_id=None, include_teachers=False):
      where_course = ""
      if course_id:
        where_course = "AND {tbl}.course_id = ?"

      with self._connect() as conn:
        # <-- NEW: phát hiện có cột email không
        user_cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        has_email = "email" in user_cols
        email_expr = "u.email AS email" if has_email else "'' AS email"

        sql = f"""
        WITH attempts AS (
          SELECT
              ea.user_id,
              ea.course_id,
              COUNT(*)                                   AS attempt_count,
              MAX(COALESCE(ea.score,0))                  AS highest_score,
              ROUND(AVG(COALESCE(ea.score,0)), 2)        AS average_score,
              MAX(COALESCE(ea.ended_at, ea.started_at))  AS last_seen_attempt
          FROM exam_attempts ea
          WHERE 1=1 {where_course.format(tbl='ea')}
          GROUP BY ea.user_id, ea.course_id
        ),
        events AS (
  SELECT
    pe.user_id,
    COALESCE(pe.course_id, ea.course_id) AS course_id,
    SUM(CASE WHEN LOWER(COALESCE(pe.event_type,'')) IN
      ('terminated','cheat','suspicious_objects','multiple_faces','multiple_faces_detected',
       'camera_denied','face_mismatch','face_monitoring_failed')
      THEN 1 ELSE 0 END) AS cheat_events,
    MAX(pe.created_at) AS last_seen_event
  FROM proctor_events pe
  LEFT JOIN exam_attempts ea ON ea.id = pe.attempt_id
  WHERE 1=1 {where_course.format(tbl='pe')}
  GROUP BY pe.user_id, COALESCE(pe.course_id, ea.course_id)
),
        frames AS (
          SELECT
              pf.user_id,
              pf.course_id,
              ROUND(AVG(COALESCE(pf.attention_score,0)) * 100, 0) AS focus_percent,
              MAX(pf.created_at)                                   AS last_seen_frame
          FROM proctor_frames pf
          WHERE 1=1 {where_course.format(tbl='pf')}
          GROUP BY pf.user_id, pf.course_id
        )
        SELECT
            u.id                          AS user_id,
            u.username,
            {email_expr},
            c.id                          AS course_id,
            c.title                       AS course_title,
            COALESCE(a.attempt_count, 0)  AS attempt_count,
            COALESCE(a.highest_score, 0)  AS highest_score,
            COALESCE(a.average_score, 0)  AS average_score,
            COALESCE(e.cheat_events, 0)   AS cheat_events,
            COALESCE(f.focus_percent, 0)  AS focus_percent,
            (SELECT 
                CASE 
                    WHEN COUNT(*) = 0 THEN '—'
                    ELSE GROUP_CONCAT(
                        CASE 
                            WHEN pe.meta_json LIKE '%"cheat_type"%' 
                                 AND pe.meta_json NOT LIKE '%"cheat_type":"unknown"%'
                                 AND pe.meta_json NOT LIKE '%"cheat_type":"normal"%'
                            THEN SUBSTR(pe.meta_json, 
                                INSTR(pe.meta_json, '"cheat_type":"') + 14,
                                INSTR(SUBSTR(pe.meta_json, INSTR(pe.meta_json, '"cheat_type":"') + 14), '"') - 1
                            )
                            WHEN pe.event_type IN ('suspicious_objects', 'block', 'warn') 
                                 AND pe.meta_json LIKE '%"cheating_reason"%'
                            THEN SUBSTR(pe.meta_json,
                                INSTR(pe.meta_json, '"cheating_reason":"') + 19,
                                CASE 
                                    WHEN INSTR(SUBSTR(pe.meta_json, INSTR(pe.meta_json, '"cheating_reason":"') + 19), '",') > 0
                                    THEN INSTR(SUBSTR(pe.meta_json, INSTR(pe.meta_json, '"cheating_reason":"') + 19), '",') - 1
                                    ELSE 50
                                END
                            )
                            ELSE pe.event_type
                        END,
                        ', '
                    )
                END
             FROM proctor_events pe
             WHERE pe.user_id = ea.user_id 
               AND pe.course_id = ea.course_id
               AND (pe.event_type IN ('cheat', 'suspicious_objects', 'block', 'warn', 'terminated', 'multiple_faces_detected')
                    OR pe.meta_json LIKE '%"cheating_detected":true%'
                    OR pe.meta_json LIKE '%"should_block":true%'
                    OR pe.meta_json LIKE '%"should_warn":true%')
             ORDER BY pe.created_at DESC
             LIMIT 5
            ) AS behavior_analysis,
            COALESCE(a.last_seen_attempt, e.last_seen_event, f.last_seen_frame) AS last_seen
        FROM exam_attempts ea
        JOIN users   u ON u.id = ea.user_id
        JOIN courses c ON c.id = ea.course_id
        LEFT JOIN attempts a ON a.user_id = ea.user_id AND a.course_id = ea.course_id
        LEFT JOIN events   e ON e.user_id = ea.user_id AND e.course_id = ea.course_id
        LEFT JOIN frames   f ON f.user_id = ea.user_id AND f.course_id = ea.course_id
        WHERE 1=1 {where_course.format(tbl='ea')}
        GROUP BY u.id, c.id
        ORDER BY COALESCE(e.cheat_events,0) DESC, COALESCE(a.highest_score,0) DESC
        """

        cur = conn.execute(sql, [int(course_id)]*4 if course_id else [])
        rows = cur.fetchall()

        # (giữ nguyên) lọc teacher nếu có cột role
        role_map = {}
        try:
            rcur = conn.execute("SELECT id, role FROM users")
            role_map = {r["id"]: r["role"] for r in rcur.fetchall()}
        except Exception:
            role_map = {}

      items = []
      for r in rows:
        if not include_teachers and role_map.get(r["user_id"]) == "teacher":
            continue
        
        # Xử lý behavior_analysis: nếu NULL hoặc rỗng thì tạo từ dữ liệu thực tế
        behavior_analysis = r["behavior_analysis"] or ""
        if not behavior_analysis or behavior_analysis == "—":
            # Fallback: lấy từ các sự kiện gian lận gần nhất
            try:
                with self._connect() as conn2:
                    behavior_events = conn2.execute("""
                        SELECT event_type, meta_json
                        FROM proctor_events
                        WHERE user_id = ? AND course_id = ?
                        ORDER BY created_at DESC
                        LIMIT 5
                    """, (r["user_id"], r["course_id"])).fetchall()
                    
                    behaviors = []
                    for be in behavior_events:
                        meta = {}
                        try:
                            if be["meta_json"]:
                                meta = json.loads(be["meta_json"])
                        except:
                            pass
                        
                        cheat_type = meta.get("cheat_type", "")
                        cheating_reason = meta.get("cheating_reason", "")
                        event_type = be["event_type"]
                        
                        if cheat_type and cheat_type not in ("unknown", "normal"):
                            behaviors.append(cheat_type)
                        elif cheating_reason:
                            behaviors.append(cheating_reason[:30])  # Giới hạn độ dài
                        elif event_type:
                            behaviors.append(event_type)
                    
                    if behaviors:
                        behavior_analysis = ", ".join(behaviors[:3])  # Tối đa 3 hành vi
            except Exception:
                pass
        
        items.append({
            "user_id": r["user_id"],
            "username": r["username"],
            "email": r["email"],  # sẽ là '' nếu DB không có cột email
            "course_id": r["course_id"],
            "course_title": r["course_title"],
            "attempt_count": r["attempt_count"],
            "highest_score": float(r["highest_score"] or 0),
            "average_score": float(r["average_score"] or 0),
            "cheat_events": int(r["cheat_events"] or 0),
            "focus_percent": int(r["focus_percent"] or 0),
            "behavior_analysis": behavior_analysis or "—",
            "last_seen": r["last_seen"],
        })
      return items



    
    
    def mark_attempt_cheated(self, attempt_id: int, user_id=None, course_id=None, reason: str = None):
      """
      Đánh dấu attempt gian lận: cheated=1, score=0, ended_at=NOW().
      """
      with self._connect() as conn:
        conn.execute("""
            UPDATE exam_attempts
               SET cheated = 1,
                   score   = 0,
                   ended_at = COALESCE(ended_at, CURRENT_TIMESTAMP)
             WHERE id = ?
        """, (attempt_id,))
        # (tùy chọn) ghi thêm 1 event “terminated”
        if reason:
            conn.execute("""
                INSERT INTO proctor_events (attempt_id, user_id, course_id, event_type, meta_json, created_at)
                SELECT a.id, a.user_id, a.course_id, ?, ?, CURRENT_TIMESTAMP
                  FROM exam_attempts a
                 WHERE a.id = ?
            """, ('terminated', json.dumps({"reason": reason}, ensure_ascii=False), attempt_id))
        conn.commit()

    def force_close_attempt_zero(self, attempt_id: int):
      """
      Fallback an toàn khi không gọi được hàm trên: khóa attempt & về 0 điểm.
      """
      with self._connect() as conn:
        conn.execute("""
            UPDATE exam_attempts
               SET cheated = 1,
                   score   = 0,
                   ended_at = COALESCE(ended_at, CURRENT_TIMESTAMP)
             WHERE id = ?
        """, (attempt_id,))
        conn.commit()
    
    def log_proctor_event(
        self,
        attempt_id=None,
        user_id=None,
        course_id=None,
        *,
        # chấp nhận cả hai phong cách gọi
        event_type=None,
        event=None,
        confidence=1.0,
        meta_json=None,
        reason=None,
        **_
    ):
        """
        Ghi 1 sự kiện proctor an toàn về schema.
        - Ưu tiên 'event_type' nếu có; nếu không sẽ lấy từ 'event'.
        - 'reason' (nếu có) sẽ được gói vào meta_json để tránh yêu cầu cột 'reason'.
        """
        evt = (event_type or event or "").strip() or "event"

        # hợp nhất meta
        meta_obj = {}
        try:
            if meta_json:
                meta_obj = json.loads(meta_json) if isinstance(meta_json, str) else dict(meta_json)
        except Exception:
            meta_obj = {}

        if reason and "reason" not in meta_obj:
            meta_obj["reason"] = reason

        meta_json_final = json.dumps(meta_obj, ensure_ascii=False)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO proctor_events
                    (attempt_id, user_id, course_id, event_type, confidence, meta_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    user_id,
                    course_id,
                    evt,
                    float(confidence or 1.0),
                    meta_json_final,
                ),
            )
            conn.commit()

    def get_cheating_incidents(self, course_id=None, user_id=None, limit=100):
        """
        Lấy danh sách chi tiết các sự kiện gian lận với đầy đủ thông tin
        """
        where_clauses = []
        params = []
        
        if course_id:
            where_clauses.append("pe.course_id = ?")
            params.append(int(course_id))
        if user_id:
            where_clauses.append("pe.user_id = ?")
            params.append(int(user_id))
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        with self._connect() as conn:
            sql = f"""
            SELECT 
                pe.id,
                pe.attempt_id,
                pe.user_id,
                pe.course_id,
                pe.event_type,
                pe.confidence,
                pe.meta_json,
                pe.created_at,
                u.username,
                c.title AS course_title
            FROM proctor_events pe
            LEFT JOIN users u ON u.id = pe.user_id
            LEFT JOIN courses c ON c.id = pe.course_id
            {where_sql}
            ORDER BY pe.created_at DESC
            LIMIT ?
            """
            params.append(limit)
            
            cur = conn.execute(sql, params)
            rows = cur.fetchall()
            
            incidents = []
            for r in rows:
                meta = {}
                try:
                    if r["meta_json"]:
                        meta = json.loads(r["meta_json"])
                except Exception:
                    meta = {}
                
                # Extract thông tin từ meta
                cheating_reason = meta.get("cheating_reason") or meta.get("reason") or r["event_type"]
                cheat_type = meta.get("cheat_type", "unknown")
                detected_date = meta.get("detected_date") or (r["created_at"][:10] if r["created_at"] else "")
                detected_time = meta.get("detected_time") or (r["created_at"][11:19] if r["created_at"] and len(r["created_at"]) > 19 else "")
                screenshot_path = meta.get("screenshot_path")
                
                # Convert screenshot path thành URL có thể truy cập được
                screenshot_url = None
                if screenshot_path:
                    # Chuyển đổi đường dẫn Windows thành URL
                    # Ví dụ: cheat_screenshots\user_20241215_143025\file.jpg -> /cheat_screenshots/user_20241215_143025/file.jpg
                    # Đảm bảo path không bắt đầu bằng / để tránh double slash
                    clean_path = screenshot_path.replace("\\", "/").lstrip("/")
                    screenshot_url = "/" + clean_path
                    
                    # Kiểm tra file có tồn tại không (optional, chỉ để debug)
                    import os
                    if not os.path.exists(screenshot_path):
                        # Thử với relative path
                        if os.path.exists(clean_path):
                            screenshot_path = clean_path
                
                incidents.append({
                    "id": r["id"],
                    "attempt_id": r["attempt_id"],
                    "user_id": r["user_id"],
                    "username": r["username"],
                    "course_id": r["course_id"],
                    "course_title": r["course_title"],
                    "event_type": r["event_type"],
                    "cheating_reason": cheating_reason,
                    "cheat_type": cheat_type,
                    "confidence": float(r["confidence"] or 0.0),
                    "detected_date": detected_date,
                    "detected_time": detected_time,
                    "detected_at": r["created_at"],
                    "screenshot_path": screenshot_path,
                    "screenshot_url": screenshot_url,  # URL để hiển thị trong browser
                    "suspicious_count": meta.get("suspicious_count", 0),
                    "face_count": meta.get("face_count", 0),
                    "attention_score": meta.get("attention_score", 0.0),
                    "should_block": meta.get("should_block", False),
                    "should_warn": meta.get("should_warn", False),
                    "suspicious_objects": meta.get("suspicious_objects", []),
                })
            
            return incidents

    def terminate_comprehensive_attempt(self, attempt_id: str):
      """Đóng bài thi tổng hợp: set score=0, status='terminated', ended_at=NOW (idempotent)."""
      import datetime
      with self._connect() as conn:
        conn.execute("""
            UPDATE comprehensive_exams
               SET ended_at = COALESCE(ended_at, ?),
                   score = 0.0,
                   status = 'terminated'
             WHERE attempt_id = ?
        """, (datetime.datetime.utcnow().isoformat(), attempt_id))
        conn.commit()
    
    
    def _column_exists(self, conn, table, col):
      rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
      return any(r[1] == col for r in rows)

    def _ensure_proctor_events_schema(self, conn):
      cur = conn.cursor()
      cur.execute("""
        CREATE TABLE IF NOT EXISTS proctor_frames (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id TEXT, user_id INTEGER, course_id INTEGER,
            frame_no INTEGER, face_count INTEGER, attention_score REAL,
            objects_json TEXT, snapshot_url TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
      """)
      cur.execute("CREATE INDEX IF NOT EXISTS idx_pf_attempt ON proctor_frames(attempt_id)")
      cur.execute("CREATE INDEX IF NOT EXISTS idx_pf_user ON proctor_frames(user_id)")
      cur.execute("""
        CREATE TABLE IF NOT EXISTS proctor_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attempt_id TEXT, user_id INTEGER, course_id INTEGER,
            event_type TEXT, confidence REAL, meta_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
      """)
      cur.execute("CREATE INDEX IF NOT EXISTS idx_pe_attempt ON proctor_events(attempt_id)")
      cur.execute("CREATE INDEX IF NOT EXISTS idx_pe_user ON proctor_events(user_id)")
      conn.commit()
    
    
    
    def get_caption_path(self, course_id: int) -> str:
      """
      Trả về đường dẫn local đến file phụ đề/transcript (.vtt/.srt) của khóa học.
      Ưu tiên cột caption_path trong bảng courses; nếu không có thì thử một số tên mặc định.
      """
      with self._connect() as conn:
        # nếu DB có cột caption_path
        try:
            row = conn.execute("SELECT caption_path FROM courses WHERE id=?", (course_id,)).fetchone()
            if row and (row["caption_path"] or row[0]):
                return row["caption_path"] if "caption_path" in row.keys() else row[0]
        except Exception:
            pass

    # Fallback: đoán theo convention
      candidates = [
        f"static/captions/course_{course_id}.vtt",
        f"static/captions/{course_id}.vtt",
        f"static/uploads/course_{course_id}.vtt",
      ]
      import os
      for p in candidates:
        if os.path.exists(p):
            return p
      return ""
    
    
    def get_random_legacy_questions(self, course_id: int, limit: int = 20):
      import sqlite3, json
      with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, question, option_a, option_b, option_c, option_d, correct_answer
              FROM questions
             WHERE course_id = ?
             ORDER BY RANDOM()
             LIMIT ?
        """, (course_id, limit))
        rows = cur.fetchall()

      out = []
      for r in rows:
        opts = [r["option_a"], r["option_b"], r["option_c"], r["option_d"]]
        # convert 'A'..'D' -> index 0..3 an toàn
        idx = "ABCD".find((r["correct_answer"] or "").strip().upper())
        idx = idx if 0 <= idx <= 3 else 0
        out.append({
            "legacy_qid": r["id"],           # phòng khi cần lưu tham chiếu
            "question": r["question"],
            "options": opts,
            "correct_index": idx
        })
      return out
  
    def get_next_unanswered_question(self, attempt_id: str):
      """Trả về câu hỏi chưa trả lời có question_index nhỏ nhất của attempt."""
      import json, sqlite3
      with self._connect() as conn:
        row = conn.execute("""
            SELECT question_index, question_text, options_json, correct_index,
                   segment_start, segment_end
              FROM comprehensive_exam_questions
             WHERE attempt_id = ? AND selected_index IS NULL
             ORDER BY question_index
             LIMIT 1
        """, (attempt_id,)).fetchone()
        if not row:
            return None
        return {
            "question_index": row["question_index"],
            "question": row["question_text"],
            "options": json.loads(row["options_json"] or "[]"),
            "correct_index": row["correct_index"],
            "segment_start": row["segment_start"],
            "segment_end": row["segment_end"],
        }

    def get_unanswered_count(self, attempt_id: str) -> int:
      with self._connect() as conn:
        n = conn.execute("""
            SELECT COUNT(1)
              FROM comprehensive_exam_questions
             WHERE attempt_id = ? AND selected_index IS NULL
        """, (attempt_id,)).fetchone()[0]
      return int(n or 0)
  
  
    def list_courses_catalog(self, limit: int = 200) -> list[dict]:
      """
      Trả về danh mục khóa học cho AI/đề xuất.
      Cột không có trong DB sẽ trả rỗng để an toàn.
      """
      with self._connect() as conn:
        rows = conn.execute("""
            SELECT
                id,
                title,
                COALESCE(level, '')           AS level,
                COALESCE(category, '')        AS category,
                COALESCE(tags, '')            AS tags,
                COALESCE(thumbnail_url, '')   AS thumbnail
            FROM courses
            WHERE (is_active IS NULL OR is_active = 1)
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        try:
            return [dict(r) for r in rows]
        except Exception:
            cols = ["id","title","level","category","tags","thumbnail"]
            return [ {k:v for k,v in zip(cols, r)} for r in rows ]













