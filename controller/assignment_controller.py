from flask import request, render_template, redirect, url_for, session
from model.assignment_model import AssignmentModel
from ai_generator import generate_questions_from_text
import json
from model.course_model import CourseModel

try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None  # Xử lý nếu moviepy không được cài đặt

try:
    from transcriber import whisper_transcribe
except ImportError:
    def whisper_transcribe(video_path: str) -> str:
        return ""

class AssignmentController:
    def __init__(self):
        self.model = AssignmentModel()

   

    def generate_questions_from_video(self, course_id):
        course = CourseModel().get_course_by_id(course_id)
        video_path = "." + course["video_url"]  # Ví dụ: /static/uploads/video.mp4

        # 🔁 Dùng OpenAI Whisper API
        lecture_text = whisper_transcribe(video_path)

        # 🧠 Gửi lên GPT để tạo câu hỏi
        ai_result = generate_questions_from_text(lecture_text)
        questions = json.loads(ai_result)

        for q in questions:
            self.model.add_question(
                course_id=course_id,
                level=q["level"],
                question=q["question"],
                option_a=q["options"]["A"],
                option_b=q["options"]["B"],
                option_c=q["options"]["C"],
                option_d=q["options"]["D"],
                correct_answer=q["answer"]
            )

        return redirect(url_for("manage_courses"))

    def mock_generate_questions(self, description, level):
        # Giả lập AI tạo câu hỏi từ mô tả bài học
        return [
            {
                "question": "AI là gì?",
                "options": ["Trí thông minh nhân tạo", "Robot", "Máy tính", "Cảm biến"],
                "answer": "A"
            },
            {
                "question": "ML là viết tắt của?",
                "options": ["Machine Learning", "Magic Line", "Math Logic", "Meta Language"],
                "answer": "A"
            },
            {
                "question": "AI dùng để làm gì?",
                "options": ["Tính toán", "Làm toán", "Tự động hóa", "Vẽ tranh"],
                "answer": "C"
            }
        ]

    def create_questions_for_course(self, course_id, description, level="beginner"):
        questions = self.mock_generate_questions(description, level)
        self.model.insert_questions(course_id, level, questions)
        return f"{len(questions)} câu hỏi đã được tạo cho khóa học #{course_id}."

    def start_exam(self, course_id, level="beginner"):
        questions = self.model.get_questions_by_course_and_level(course_id, level)
        return render_template("exam.html", course_id=course_id, questions=questions)

    def submit_exam(self, course_id):
        student_id = session.get("student_id", 1)  # giả lập
        answers = {k: v for k, v in request.form.items() if k.startswith("q")}
        results = []

        for key, answer in answers.items():
            qid = int(key[1:])
            question = next(q for q in self.model.get_questions_by_course_and_level(course_id, "beginner") if q["id"] == qid)
            correct = question["correct_answer"]
            score = 1 if answer == correct else 0
            feedback = "Đúng rồi!" if score == 1 else f"Sai rồi, đáp án đúng là {correct}"
            self.model.save_submission(student_id, qid, answer, score, feedback)
            results.append({
                "question": question["question"],
                "your_answer": answer,
                "correct": correct,
                "feedback": feedback
            })

        return render_template("exam_result.html", results=results)
    
    def view_history(self):
    # Ưu tiên id từ session['user']['id'], fallback sang session['student_id']
      student_id = session.get("user", {}).get("id") or session.get("student_id", 1)
      submissions = self.model.get_submission_history(student_id)
      return render_template("submission_history.html", submissions=submissions)


