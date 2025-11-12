#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App Transcript Quiz - Ứng dụng web tạo câu hỏi từ transcript
"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import uuid
from transcript_question_generator import create_quiz_from_transcript

app = Flask(__name__)

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('transcript_quiz_interface.html')

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    """Tạo câu hỏi từ transcript"""
    try:
        data = request.get_json()
        
        transcript = data.get('transcript', '')
        video_title = data.get('video_title', 'Video Quiz')
        question_types = data.get('question_types', ['mcq', 'essay', 'oral'])
        n_questions_per_type = data.get('n_questions_per_type', 2)
        
        if not transcript.strip():
            return jsonify({'error': 'Transcript không được để trống'}), 400
        
        # Tạo câu hỏi từ transcript
        quiz_result = create_quiz_from_transcript(
            transcript=transcript,
            video_title=video_title,
            question_types=question_types,
            n_questions_per_type=n_questions_per_type
        )
        
        return jsonify({
            'success': True,
            'quiz_data': quiz_result
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_quiz', methods=['POST'])
def save_quiz():
    """Lưu quiz vào file JSON"""
    try:
        data = request.get_json()
        quiz_data = data.get('quiz_data')
        
        if not quiz_data:
            return jsonify({'error': 'Không có dữ liệu quiz'}), 400
        
        # Tạo filename
        quiz_id = str(uuid.uuid4())[:8]
        filename = f"quiz_{quiz_id}.json"
        
        # Lưu vào thư mục data_quiz
        os.makedirs('data_quiz', exist_ok=True)
        file_path = os.path.join('data_quiz', filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(quiz_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'quiz_id': quiz_id,
            'file_path': file_path
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/quiz/<quiz_id>')
def get_quiz(quiz_id):
    """Lấy quiz theo ID"""
    try:
        file_path = os.path.join('data_quiz', f'quiz_{quiz_id}.json')
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Quiz không tồn tại'}), 404
        
        with open(file_path, 'r', encoding='utf-8') as f:
            quiz_data = json.load(f)
        
        return jsonify({
            'success': True,
            'quiz_data': quiz_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_quiz/<quiz_id>')
def download_quiz(quiz_id):
    """Tải quiz file"""
    try:
        file_path = os.path.join('data_quiz', f'quiz_{quiz_id}.json')
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Quiz không tồn tại'}), 404
        
        return send_file(file_path, as_attachment=True, download_name=f'quiz_{quiz_id}.json')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def status():
    """Kiểm tra trạng thái hệ thống"""
    try:
        gemini_available = bool(os.getenv('GEMINI_API_KEY'))
        
        return jsonify({
            'gemini_available': gemini_available,
            'features': {
                'ai_analysis': gemini_available,
                'question_generation': gemini_available,
                'multiple_question_types': True,
                'smart_content_analysis': True
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Load environment
    try:
        from dotenv import load_dotenv
        if os.path.exists('.env'):
            load_dotenv()
    except ImportError:
        pass
    
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           🎯 TRANSCRIPT QUIZ GENERATOR WEB APP                ║
║                                                                ║
║  AI Gemini phân tích transcript và tạo câu hỏi thông minh    ║
║  Dựa trên ý nghĩa, không copy y nguyên text                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Kiểm tra cấu hình
    print("🔍 Checking system configuration...")
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found")
        print("💡 Please set GEMINI_API_KEY in your .env file")
    else:
        print("✅ GEMINI_API_KEY configured")
    
    print("\n🚀 Starting Transcript Quiz Generator...")
    print("🌐 Open your browser and go to: http://127.0.0.1:5003")
    print("📝 Paste transcript and generate smart questions!")
    print("🎯 Features: AI analysis, multiple question types, smart content analysis")
    
    app.run(host='127.0.0.1', port=5003, debug=True)
