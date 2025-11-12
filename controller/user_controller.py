from flask import Blueprint, request, redirect, url_for, render_template, flash
from model.user_model import UserModel
from code_generator import generate_code
import os
from werkzeug.utils import secure_filename

user_bp = Blueprint('user', __name__)
class UserController:
    def __init__(self):
        self.model = UserModel()

    def list_users(self):
        """Hiển thị danh sách tất cả người dùng."""
        users = self.model.get_all_users()
        return render_template("user_list.html", users=users)

    def create_user_form(self):
        """Hiển thị form tạo người dùng mới."""
        return render_template("create_user.html")

    def store_user(self):
        """Xử lý dữ liệu tạo người dùng mới."""
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        if not username or not email or not password:
            flash("Vui lòng điền đầy đủ thông tin.", "danger")
            return redirect(url_for("create_user"))

        self.model.create_user(username, password, role)
        flash("Tạo người dùng thành công!", "success")
        return redirect(url_for("list_users"))

    def delete_user(self, user_id):
        """Xóa người dùng."""
        self.model.delete_user(user_id)
        flash("Đã xóa người dùng.", "info")
        return redirect(url_for("list_users"))

    def edit_user_form(self, user_id):
        """Hiển thị form chỉnh sửa người dùng."""
        user = self.model.get_user_by_id(user_id)
        if not user:
            flash("Người dùng không tồn tại.", "danger")
            return redirect(url_for("user.list_users"))
        return render_template("edit_user.html", user=user)

    def update_user(self, user_id):
        """Cập nhật thông tin người dùng."""
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")
        
        # Xử lý upload avatar
        avatar_path = None
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '':
                # Kiểm tra file hợp lệ
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                filename = secure_filename(file.filename)
                if '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # Tạo thư mục avatars nếu chưa có
                    upload_folder = 'static/avatars'
                    os.makedirs(upload_folder, exist_ok=True)
                    
                    # Lưu file với tên user_id
                    file_extension = filename.rsplit('.', 1)[1].lower()
                    avatar_filename = f"user_{user_id}.{file_extension}"
                    avatar_path = f"avatars/{avatar_filename}"
                    
                    file_path = os.path.join(upload_folder, avatar_filename)
                    file.save(file_path)
                    
                    # Cập nhật avatar trong database
                    self.model.update_avatar_by_id(user_id, avatar_path)
        
        user = self.model.get_user_by_id(user_id)
        if not user:
            flash("Người dùng không tồn tại.", "danger")
            return redirect(url_for("list_users"))

        if not password:
            password = user['password']

        self.model.update_user(user_id, username, password, role)
        flash("Cập nhật người dùng thành công!", "success")
        return redirect(url_for("list_users"))
    

@user_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        invite_code = generate_code()
        user = UserModel.find_by_email(email)

        if user:
            user.invite_code = invite_code
            user.save_to_db()
            print(f"[DEBUG] Mã xác nhận gửi tới {email}: {invite_code}")
            flash("Mã xác nhận đã được gửi qua email.", "info")
            return redirect(url_for('user.enter_reset_code'))

        flash("Không tìm thấy email này trong hệ thống.", "warning")
        return redirect(url_for('user.forgot_password'))

    return render_template('forgot_password.html')

