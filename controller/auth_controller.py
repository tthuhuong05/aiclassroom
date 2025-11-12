# auth_controller.py

import os
import uuid
from werkzeug.utils import secure_filename
from flask import request, session, redirect, url_for, render_template, flash, abort
from model.user_model import UserModel
from view.auth_view import AuthView

class AuthController:
    def __init__(self):
        self.user_model = UserModel()
        self.auth_view = AuthView()
    
    def home(self):
        username = session.get("username")
        role = session.get("role")
        return self.auth_view.show_home(username=username, role=role)

    def register(self):
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            role = request.form.get("role")
            invite_code = request.form.get("invite_code")

            # ✅ Nếu chọn giáo viên thì kiểm tra mã
            if role == "teacher" and invite_code != "TEACHER2024":
                flash("Mã đăng ký giáo viên không hợp lệ.", "danger")
                return redirect(url_for("register"))

            # ✅ Kiểm tra username đã tồn tại chưa
            if self.user_model.find_user_by_username(username):
                flash("Tên đăng nhập đã tồn tại.", "danger")
                return redirect(url_for("register"))

            # ✅ Xử lý upload avatar
            avatar_path = None
            if 'avatar' in request.files:
                avatar_file = request.files['avatar']
                if avatar_file and avatar_file.filename:
                    # Kiểm tra định dạng file
                    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                    if '.' in avatar_file.filename and \
                       avatar_file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                        
                        # Tạo tên file unique
                        filename = secure_filename(avatar_file.filename)
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        
                        # Lưu file
                        avatar_dir = "static/avatars"
                        os.makedirs(avatar_dir, exist_ok=True)
                        avatar_path = os.path.join(avatar_dir, unique_filename)
                        avatar_file.save(avatar_path)
                        
                        # Lưu đường dẫn tương đối
                        avatar_path = f"avatars/{unique_filename}"
                    else:
                        flash("Định dạng file không hợp lệ. Chỉ chấp nhận: PNG, JPG, JPEG, GIF, WEBP", "warning")

            # ✅ Tạo tài khoản
            self.user_model.create_user(username, password, role, avatar_path)
            flash("Tạo tài khoản thành công. Vui lòng đăng nhập.", "success")
            return redirect(url_for("login"))

        return render_template("auth/register.html")

    
    def login(self):
      if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = self.user_model.find_by_email(email)
        if user and self.user_model.verify_password(password, user['password']):
            session['username'] = user['username']
            session['role'] = user['role']
            session['user'] = dict(user)  # convert sqlite3.Row to dict if needed

            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.", "danger")
    
      return render_template("auth/login.html")

    def logout(self):
        session.clear()
        return redirect(url_for("home"))

    def forgot_password(self):
        if request.method == "POST":
            username = request.form.get("username")
            user = self.user_model.find_user_by_username(username)
            if user:
                reset_link = url_for("reset_password", username=username, _external=True)
                flash(f"Link đặt lại mật khẩu: {reset_link}", "info")
            else:
                flash("Tài khoản không tồn tại.", "danger")
            return redirect(url_for("forgot_password"))

        return render_template("auth/forgot_password.html")

    def reset_password(self, username):
        if request.method == "POST":
            new_password = request.form.get("new_password")
            self.user_model.update_password(username, new_password)
            flash("Mật khẩu đã được cập nhật.", "success")
            return redirect(url_for("login"))

        return render_template("auth/reset_password.html", username=username)

