#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App AI Content Processor - Ứng dụng web với AI Content Processor
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
import uuid
from ai_content_processor import process_file_to_video
from services.human_voice_service import is_human_voice_available

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

@app.route('/')
def index():
    """Trang chủ với AI Content Processor"""
    return render_template('ai_content_processor_interface.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Upload và xử lý file với AI Content Processor"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Kiểm tra định dạng file
        allowed_extensions = {'.pdf', '.docx', '.pptx', '.txt'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': f'Unsupported file type: {file_ext}'}), 400
        
        # Lưu file
        upload_dir = 'static/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # Lấy thông tin từ form
        title = request.form.get('title', 'AI Generated Video')
        require_human_voice = request.form.get('require_human_voice', '1') == '1'
        
        # Kiểm tra giọng người thật
        if require_human_voice and not is_human_voice_available():
            return jsonify({
                'error': 'Human voice required but ElevenLabs not configured. Please set ELEVENLABS_API_KEY.'
            }), 400
        
        # Xử lý file với AI Content Processor
        result = process_file_to_video(
            file_path=file_path,
            output_dir=upload_dir,
            title=title
        )
        
        return jsonify({
            'success': True,
            'video_path': result['video_path'],
            'caption_path': result['caption_path'],
            'duration': result['duration'],
            'slide_count': result['slide_count'],
            'title': result['title'],
            'features': {
                'ai_analysis': True,
                'realistic_images': True,
                'human_voice': require_human_voice,
                'professional_video': True,
                'auto_captions': True
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/video/<path:filename>')
def serve_video(filename):
    """Serve video file"""
    try:
        return send_file(f'static/uploads/{filename}', as_attachment=False)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/caption/<path:filename>')
def serve_caption(filename):
    """Serve caption file"""
    try:
        return send_file(f'static/uploads/{filename}', as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/status')
def status():
    """Kiểm tra trạng thái hệ thống"""
    try:
        # Kiểm tra API keys
        gemini_available = bool(os.getenv('GEMINI_API_KEY'))
        elevenlabs_available = is_human_voice_available()
        pexels_available = bool(os.getenv('PEXELS_API_KEY'))
        unsplash_available = bool(os.getenv('UNSPLASH_ACCESS_KEY'))
        
        return jsonify({
            'gemini_available': gemini_available,
            'elevenlabs_available': elevenlabs_available,
            'pexels_available': pexels_available,
            'unsplash_available': unsplash_available,
            'human_voice_required': os.getenv('REQUIRE_HUMAN_VOICE', '0') == '1',
            'features': {
                'ai_analysis': gemini_available,
                'human_voice': elevenlabs_available,
                'realistic_images': pexels_available or unsplash_available,
                'professional_video': True
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
║           🌐 AI CONTENT PROCESSOR WEB APP                      ║
║                                                                ║
║  Luồng công việc hoàn chỉnh:                                  ║
║  📄 File → 🤖 AI Gemini → 🖼️ Hình ảnh → 🎤 Giọng người → 🎬 Video ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Kiểm tra cấu hình
    print("🔍 Checking system configuration...")
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    elevenlabs_key = os.getenv('ELEVENLABS_API_KEY')
    pexels_key = os.getenv('PEXELS_API_KEY')
    unsplash_key = os.getenv('UNSPLASH_ACCESS_KEY')
    
    if not gemini_key:
        print("❌ GEMINI_API_KEY not found")
        print("💡 Please set GEMINI_API_KEY in your .env file")
    else:
        print("✅ GEMINI_API_KEY configured")
    
    if not elevenlabs_key:
        print("❌ ELEVENLABS_API_KEY not found")
        print("💡 Please set ELEVENLABS_API_KEY in your .env file")
        print("💡 Human voice will not be available")
    else:
        print("✅ ELEVENLABS_API_KEY configured")
    
    if not pexels_key and not unsplash_key:
        print("❌ No image API keys found")
        print("💡 Please set PEXELS_API_KEY or UNSPLASH_ACCESS_KEY")
        print("💡 Realistic images will not be available")
    else:
        print("✅ Image API keys configured")
    
    print("\n🚀 Starting AI Content Processor Web App...")
    print("🌐 Open your browser and go to: http://127.0.0.1:5002")
    print("📱 Upload a PDF/DOCX/PPTX file to create AI video")
    print("🎯 Features: AI analysis, realistic images, human voice")
    
    app.run(host='127.0.0.1', port=5002, debug=True)
