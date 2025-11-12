import sqlite3
from typing import List, Any, Dict

class AssignmentModel:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self.create_tables()

    def create_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            # Câu hỏi (giữ nguyên cấu trúc cũ để tương thích)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER,
                level TEXT,
                question TEXT,
                option_a TEXT,
                option_b TEXT,
                option_c TEXT,
                option_d TEXT,
                correct_answer TEXT
            )
            """)

            # Lịch sử nộp bài (mở rộng cột)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS student_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                question_id INTEGER,
                student_answer TEXT,
                score INTEGER,
                ai_feedback TEXT,
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                course_id INTEGER,
                question_text TEXT,
                correct_answer_text TEXT,
                attempt_id TEXT
            )
            """)

            # Bổ sung cột còn thiếu (migrate DB cũ)
            cols = [r[1] for r in cur.execute("PRAGMA table_info(student_submissions)").fetchall()]
            add_col = lambda name, ddl: (name not in cols) and cur.execute(f"ALTER TABLE student_submissions ADD COLUMN {name} {ddl}")
            add_col("course_id", "INTEGER")
            add_col("question_text", "TEXT")
            add_col("correct_answer_text", "TEXT")
            add_col("attempt_id", "TEXT")

            # Index + Unique (idempotent theo student/attempt/question)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ss_student ON student_submissions(student_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ss_course  ON student_submissions(course_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ss_attempt ON student_submissions(attempt_id)")
            cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS u_ss_student_attempt_q
            ON student_submissions(student_id, attempt_id, question_id)
            """)
            conn.commit()

    def insert_questions(self, course_id, level, question_list: List[Dict[str, Any]]):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            for q in question_list:
                cur.execute("""
                INSERT INTO questions (course_id, level, question, option_a, option_b, option_c, option_d, correct_answer)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (course_id, level, q["question"], *q["options"], q["answer"]))
            conn.commit()

    def get_questions_by_course_and_level(self, course_id, level):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM questions WHERE course_id=? AND level=?", (course_id, level))
            return cur.fetchall()

    # <-- chữ ký mới: tương thích phần ghi lịch sử trong app.py
    def save_submission(self, student_id, question_id, student_answer, score, ai_feedback,
                        course_id=None, question_text=None, correct_answer_text=None, attempt_id=None):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO student_submissions
              (student_id, question_id, student_answer, score, ai_feedback, course_id, question_text, correct_answer_text, attempt_id)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(student_id, attempt_id, question_id) DO UPDATE SET
              student_answer       = excluded.student_answer,
              score               = excluded.score,
              ai_feedback         = COALESCE(excluded.ai_feedback, student_submissions.ai_feedback),
              submitted_at        = CURRENT_TIMESTAMP,
              course_id           = COALESCE(excluded.course_id, student_submissions.course_id),
              question_text       = COALESCE(excluded.question_text, student_submissions.question_text),
              correct_answer_text = COALESCE(excluded.correct_answer_text, student_submissions.correct_answer_text)
            """, (student_id, question_id, student_answer, int(score), ai_feedback, course_id, question_text, correct_answer_text, attempt_id))
            conn.commit()

    def get_submission_history(self, student_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
            SELECT
              s.id, s.submitted_at, s.student_answer, s.score, s.ai_feedback,
              COALESCE(s.question_text, q.question)          AS question,
              COALESCE(s.correct_answer_text, q.correct_answer) AS correct_answer,
              COALESCE(c.title, (SELECT title FROM courses WHERE id=COALESCE(s.course_id, q.course_id))) AS course_title
            FROM student_submissions s
            LEFT JOIN questions q ON q.id = s.question_id
            LEFT JOIN courses  c ON c.id = COALESCE(s.course_id, q.course_id)
            WHERE s.student_id = ?
            ORDER BY s.submitted_at DESC, s.id DESC
            """, (student_id,))
            return cur.fetchall()
    
    
    def count_questions(self, course_id: int, level: str = None) -> int:
      import sqlite3
      with sqlite3.connect(self.db_path) as conn:
        cur = conn.cursor()
        if level:
            cur.execute("SELECT COUNT(*) FROM questions WHERE course_id=? AND level=?", (course_id, level))
        else:
            cur.execute("SELECT COUNT(*) FROM questions WHERE course_id=?", (course_id,))
        row = cur.fetchone()
        return int(row[0] if row and row[0] else 0)

