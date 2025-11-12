#!/usr/bin/env python3
"""
Demo Modern UI cho VirtualRoom
Chạy server Flask để xem giao diện mới
"""

import os
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, session

# Tạo Flask app
app = Flask(__name__)
app.secret_key = 'demo-secret-key-2025'

# Sample data cho demo
SAMPLE_COURSES = [
    {
        'id': 1,
        'title': 'Lập trình Python Cơ bản',
        'description': 'Khóa học Python từ cơ bản đến nâng cao với các dự án thực tế',
        'image_url': 'https://picsum.photos/400/250?random=1',
        'tags': ['Python', 'Programming', 'Beginner'],
        'duration': '40 giờ',
        'instructor': 'Nguyễn Văn A',
        'rating': 4.8,
        'students': 1250
    },
    {
        'id': 2,
        'title': 'Machine Learning với Python',
        'description': 'Áp dụng AI và Machine Learning vào các bài toán thực tế',
        'image_url': 'https://picsum.photos/400/250?random=2',
        'tags': ['AI', 'ML', 'Python', 'Data Science'],
        'duration': '60 giờ',
        'instructor': 'Trần Thị B',
        'rating': 4.9,
        'students': 890
    },
    {
        'id': 3,
        'title': 'Web Development với React',
        'description': 'Xây dựng ứng dụng web hiện đại với React và Node.js',
        'image_url': 'https://picsum.photos/400/250?random=3',
        'tags': ['React', 'JavaScript', 'Web Dev', 'Frontend'],
        'duration': '50 giờ',
        'instructor': 'Lê Văn C',
        'rating': 4.7,
        'students': 2100
    },
    {
        'id': 4,
        'title': 'DevOps và Containerization',
        'description': 'Quản lý infrastructure hiện đại với Docker và Kubernetes',
        'image_url': 'https://picsum.photos/400/250?random=4',
        'tags': ['DevOps', 'Docker', 'Kubernetes', 'Cloud'],
        'duration': '45 giờ',
        'instructor': 'Phạm Thị D',
        'rating': 4.6,
        'students': 675
    },
    {
        'id': 5,
        'title': 'UI/UX Design Fundamentals',
        'description': 'Thiết kế giao diện người dùng chuyên nghiệp với Figma',
        'image_url': 'https://picsum.photos/400/250?random=5',
        'tags': ['UI/UX', 'Design', 'Figma', 'Creative'],
        'duration': '35 giờ',
        'instructor': 'Hoàng Văn E',
        'rating': 4.8,
        'students': 1540
    },
    {
        'id': 6,
        'title': 'Database Design & SQL',
        'description': 'Thiết kế và quản trị cơ sở dữ liệu với SQL và NoSQL',
        'image_url': 'https://picsum.photos/400/250?random=6',
        'tags': ['Database', 'SQL', 'MySQL', 'MongoDB'],
        'duration': '30 giờ',
        'instructor': 'Đỗ Thị F',
        'rating': 4.5,
        'students': 980
    }
]

@app.route('/')
def home():
    """Trang chủ hiện đại"""
    username = session.get('username')
    return render_template('home_modern.html',
                         courses=SAMPLE_COURSES,
                         username=username,
                         categories=['Programming', 'AI', 'Web Dev', 'Design', 'Database'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Trang đăng nhập hiện đại"""
    if request.method == 'POST':
        username = request.form.get('email')
        password = request.form.get('password')

        # Simple demo authentication
        if username and password:
            session['username'] = username.split('@')[0]  # Simple username from email
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Email hoặc mật khẩu không đúng!', 'error')

    return render_template('auth/login_modern.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Trang đăng ký hiện đại"""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        role = request.form.get('role')

        if first_name and last_name and email and role:
            session['username'] = f"{first_name} {last_name}"
            flash('Đăng ký thành công! Chào mừng bạn đến với VirtualRoom!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Vui lòng điền đầy đủ thông tin!', 'error')

    return render_template('auth/register_modern.html')

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """Chi tiết khóa học hiện đại"""
    course = next((c for c in SAMPLE_COURSES if c['id'] == course_id), None)
    if not course:
        flash('Không tìm thấy khóa học!', 'error')
        return redirect(url_for('home'))

    return render_template('course_detail_modern.html', course=course)

@app.route('/logout')
def logout():
    """Đăng xuất"""
    session.pop('username', None)
    flash('Đã đăng xuất!', 'info')
    return redirect(url_for('home'))

@app.route('/toggle-theme')
def toggle_theme():
    """API để toggle dark mode (cho demo)"""
    return {'status': 'success'}

def main():
    """Chạy demo server"""
    print("🎨 VirtualRoom Modern UI Demo")
    print("=" * 50)
    print("🚀 Khởi động server demo...")
    print("📱 Truy cập: http://localhost:5000")
    print("🎯 Tính năng demo:")
    print("  • Trang chủ hiện đại với hero section")
    print("  • Form đăng nhập/đăng ký đẹp mắt")
    print("  • Chi tiết khóa học với tabs")
    print("  • Dark mode toggle")
    print("  • Responsive design")
    print("  • Particle animations")
    print("=" * 50)

    # Đảm bảo thư mục static tồn tại
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    # Kiểm tra file CSS và JS
    css_file = 'static/css/modern-style.css'
    js_file = 'static/js/modern-script.js'

    if not os.path.exists(css_file):
        print(f"⚠️  Cảnh báo: Không tìm thấy {css_file}")
        print("   Hãy đảm bảo đã tạo file CSS trước khi chạy demo!")

    if not os.path.exists(js_file):
        print(f"⚠️  Cảnh báo: Không tìm thấy {js_file}")
        print("   Hãy đảm bảo đã tạo file JavaScript trước khi chạy demo!")

    print("\nDừng server bằng Ctrl+C\n")

    # Chạy Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()


