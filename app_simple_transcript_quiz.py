#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App Simple Transcript Quiz - Ứng dụng web tạo câu hỏi từ transcript đơn giản
"""

from flask import Flask, render_template, request, jsonify
import os
import json
from simple_transcript_quiz import create_questions_from_transcript

app = Flask(__name__)

@app.route('/')
def index():
    """Trang chủ"""
    return render_template('simple_transcript_quiz_interface.html')

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    """Tạo câu hỏi từ transcript"""
    try:
        data = request.get_json()
        
        transcript = data.get('transcript', '')
        video_title = data.get('video_title', 'Video Quiz')
        
        if not transcript.strip():
            return jsonify({'error': 'Transcript không được để trống'}), 400
        
        # Tạo câu hỏi từ transcript
        quiz_result = create_questions_from_transcript(
            transcript=transcript,
            video_title=video_title
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
        import uuid
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

if __name__ == '__main__':
    print("""
╔════════════════════════════════════════════════════════════════╗
║                                                                ║
║           🎯 SIMPLE TRANSCRIPT QUIZ WEB APP                  ║
║                                                                ║
║  Tạo câu hỏi từ transcript dựa trên nội dung chính           ║
║  Dựa trên ý nghĩa, không copy y nguyên text                  ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("🚀 Starting Simple Transcript Quiz Generator...")
    print("🌐 Open your browser and go to: http://127.0.0.1:5004")
    print("📝 Paste transcript and generate smart questions!")
    print("🎯 Features: Smart content analysis, multiple question types")
    
    app.run(host='127.0.0.1', port=5004, debug=True)

