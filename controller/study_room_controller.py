from flask import render_template, request, redirect, url_for, session, jsonify, flash, abort
from model.study_room_model import StudyRoomModel
from model.course_model import CourseModel
from functools import wraps


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


class StudyRoomController:
    def __init__(self):
        self.model = StudyRoomModel()
        self.course_model = CourseModel()

    def list_rooms(self):
        """Hiển thị danh sách phòng học"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return redirect(url_for("login"))
        
        # Lấy tất cả phòng học công khai
        all_rooms = self.model.get_all_rooms(user_id=user_id, is_public_only=True)
        print(f"[DEBUG StudyRoomController] Found {len(all_rooms)} public rooms for user {user_id}")
        
        # Lấy phòng học của user
        my_rooms = self.model.get_user_rooms(user_id)
        print(f"[DEBUG StudyRoomController] Found {len(my_rooms)} user rooms")
        
        # Lấy danh sách thành viên cho mỗi phòng
        for room in all_rooms:
            room['members'] = self.model.get_room_members(room['id'])
        
        for room in my_rooms:
            room['members'] = self.model.get_room_members(room['id'])
        
        # Filter theo language nếu có
        language_filter = request.args.get("language")
        if language_filter:
            all_rooms = [r for r in all_rooms if r.get("language") == language_filter]
            print(f"[DEBUG StudyRoomController] After language filter: {len(all_rooms)} rooms")
        
        print(f"[DEBUG StudyRoomController] Rendering template: study_rooms/list.html")
        print(f"[DEBUG StudyRoomController] all_rooms type: {type(all_rooms)}, length: {len(all_rooms) if all_rooms else 0}")
        
        try:
            result = render_template(
                "study_rooms/list.html",
                all_rooms=all_rooms or [],
                my_rooms=my_rooms or [],
                current_user_id=user_id
            )
            print(f"[DEBUG StudyRoomController] Template rendered successfully, type: {type(result)}")
            return result
        except Exception as e:
            print(f"[ERROR StudyRoomController] Failed to render template: {e}")
            import traceback
            traceback.print_exc()
            raise

    def create_room_form(self):
        """Hiển thị form tạo phòng học"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return redirect(url_for("login"))
        
        # Lấy danh sách khóa học để chọn
        courses = []
        try:
            courses_data = self.course_model.get_all_courses()
            if courses_data:
                # Convert Row objects to dicts
                courses = [dict(row) for row in courses_data]
        except Exception as e:
            print(f"Error loading courses: {e}")
            pass
        
        return render_template("study_rooms/create.html", courses=courses)

    def create_room(self):
        """Xử lý tạo phòng học"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            print(f"[ERROR StudyRoomController] User not logged in")
            return jsonify({"ok": False, "error": "Chưa đăng nhập"}), 401
        
        try:
            # Lấy dữ liệu từ request
            if request.is_json:
                data = request.get_json(force=True)
            else:
                data = request.form.to_dict()
            
            print(f"[DEBUG StudyRoomController] Received data: {data}")
            
            name = (data.get("name") or "").strip()
            description = (data.get("description") or "").strip()
            course_id = data.get("course_id")
            max_members = data.get("max_members")
            is_public = data.get("is_public")
            language = (data.get("language") or "").strip() or None
            level = (data.get("level") or "").strip() or None
            topic = (data.get("topic") or "").strip() or None
            
            # Xử lý max_members
            try:
                if isinstance(max_members, str):
                    max_members = int(max_members) if max_members else 10
                else:
                    max_members = int(max_members) if max_members else 10
            except (ValueError, TypeError):
                max_members = 10
            
            # Xử lý is_public
            if isinstance(is_public, bool):
                is_public = is_public
            elif isinstance(is_public, str):
                is_public = is_public.lower() in ("true", "1", "yes", "on")
            else:
                is_public = True
            
            print(f"[DEBUG StudyRoomController] Parsed: name={name}, max_members={max_members}, is_public={is_public}")
            
            if not name:
                error_msg = "Tên phòng học không được để trống"
                print(f"[ERROR StudyRoomController] {error_msg}")
                if request.is_json:
                    return jsonify({"ok": False, "error": error_msg}), 400
                flash(error_msg, "error")
                return redirect(url_for("create_study_room"))
            
            # Xử lý course_id
            try:
                course_id = int(course_id) if course_id and str(course_id).strip() and str(course_id) != "None" else None
            except (ValueError, TypeError):
                course_id = None
            
            print(f"[DEBUG StudyRoomController] Creating room with: name={name}, user_id={user_id}, course_id={course_id}")
            
            room_id = self.model.create_room(
                name=name,
                description=description,
                created_by=user_id,
                course_id=course_id,
                max_members=max_members,
                is_public=is_public,
                language=language,
                level=level,
                topic=topic
            )
            
            print(f"[DEBUG StudyRoomController] Room created successfully with ID: {room_id}")
            
            # Lấy thông tin phòng mới tạo để lấy slug và invite_key
            room = self.model.get_room_by_id(room_id)
            
            if request.is_json:
                response_data = {
                    "ok": True, 
                    "room_id": room_id, 
                    "message": "Tạo phòng học thành công"
                }
                if room:
                    response_data["slug"] = room.get("slug")
                    response_data["invite_key"] = room.get("invite_key")
                return jsonify(response_data)
            
            flash("Tạo phòng học thành công!", "success")
            return redirect(url_for("study_room_detail", room_id=room_id))
        except Exception as e:
            import traceback
            error_msg = str(e)
            print(f"[ERROR StudyRoomController] Failed to create room: {error_msg}")
            traceback.print_exc()
            if request.is_json:
                return jsonify({"ok": False, "error": error_msg}), 500
            flash(f"Lỗi: {error_msg}", "error")
            return redirect(url_for("create_study_room"))

    def room_detail(self, room_id: int, force_fullscreen: bool = False):
        """Chi tiết phòng học - Room page với video/chat"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return redirect(url_for("login"))
        
        room = self.model.get_room_by_id(room_id)
        if not room:
            flash("Phòng học không tồn tại", "error")
            return redirect(url_for("list_study_rooms"))
        
        # Lấy danh sách thành viên
        members = self.model.get_room_members(room_id)
        
        # Kiểm tra user có trong phòng không, nếu chưa thì tự động tham gia
        is_member = any(m.get("user_id") == user_id for m in members)
        if not is_member:
            # Tự động tham gia phòng khi vào trang
            self.model.join_room(room_id, user_id)
            members = self.model.get_room_members(room_id)
        
        is_admin = any(m.get("user_id") == user_id and m.get("role") == "admin" for m in members)
        
        # Render room page với video/chat
        template_name = "study_rooms/room_fullscreen.html" if force_fullscreen else "study_rooms/room.html"
        return render_template(template_name, 
                             room=room, 
                             members=members,
                             is_member=True,
                             is_admin=is_admin,
                             current_user_id=user_id,
                             force_fullscreen=force_fullscreen)

    def room_detail_by_slug(self, slug: str):
        """Điều hướng vào phòng bằng đường dẫn slug + key"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return redirect(url_for("login"))
        
        room = self.model.get_room_by_slug(slug)
        if not room:
            abort(404)
        
        invite_key = room.get("invite_key")
        provided_key = request.args.get("key")
        if invite_key and invite_key != provided_key:
            flash("Link phòng không hợp lệ hoặc đã hết hạn", "error")
            return redirect(url_for("list_study_rooms"))
        
        return self.room_detail(room_id=room["id"], force_fullscreen=True)

    def join_room(self, room_id: int):
        """Tham gia phòng học"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return jsonify({"ok": False, "error": "Chưa đăng nhập"}), 401
        
        success = self.model.join_room(room_id, user_id)
        if success:
            return jsonify({"ok": True, "message": "Tham gia phòng học thành công"})
        else:
            return jsonify({"ok": False, "error": "Không thể tham gia phòng học (có thể đã tham gia hoặc phòng đã đầy)"}), 400

    def leave_room(self, room_id: int):
        """Rời khỏi phòng học"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return jsonify({"ok": False, "error": "Chưa đăng nhập"}), 401
        
        success = self.model.leave_room(room_id, user_id)
        if success:
            return jsonify({"ok": True, "message": "Đã rời khỏi phòng học"})
        else:
            return jsonify({"ok": False, "error": "Không thể rời khỏi phòng học"}), 400

    def delete_room(self, room_id: int):
        """Xóa phòng học"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return jsonify({"ok": False, "error": "Chưa đăng nhập"}), 401
        
        success = self.model.delete_room(room_id, user_id)
        if success:
            return jsonify({"ok": True, "message": "Đã xóa phòng học"})
        else:
            return jsonify({"ok": False, "error": "Không có quyền xóa phòng học"}), 403

    def update_room(self, room_id: int):
        """Cập nhật thông tin phòng học"""
        user_id = session.get("user", {}).get("id")
        if not user_id:
            return jsonify({"ok": False, "error": "Chưa đăng nhập"}), 401
        
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"ok": False, "error": "Payload không hợp lệ"}), 400
        
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "Payload không hợp lệ"}), 400
        
        # Lấy dữ liệu và chuẩn hóa
        name = (data.get("name") or "").strip() if "name" in data else None
        description = (data.get("description") or "").strip() if "description" in data else None
        topic = (data.get("topic") or "").strip() if "topic" in data else None
        language = (data.get("language") or "").strip() if "language" in data else None
        level = (data.get("level") or "").strip() if "level" in data else None
        is_public = data.get("is_public") if "is_public" in data else None
        
        max_members = None
        if "max_members" in data:
            try:
                max_members = int(data.get("max_members"))
                if max_members < 1:
                    raise ValueError("max_members must be positive")
            except Exception:
                return jsonify({"ok": False, "error": "Số lượng thành viên tối đa không hợp lệ"}), 400
        
        if isinstance(is_public, str):
            is_public = is_public.lower() in ("true", "1", "yes", "on")
        
        success = self.model.update_room(
            room_id=room_id,
            user_id=user_id,
            name=name if name is not None else None,
            description=description if description is not None else None,
            max_members=max_members,
            is_public=is_public,
            language=language if language is not None else None,
            level=level if level is not None else None,
            topic=topic if topic is not None else None
        )
        
        if not success:
            return jsonify({"ok": False, "error": "Không có quyền cập nhật phòng hoặc dữ liệu không thay đổi"}), 403
        
        updated_room = self.model.get_room_by_id(room_id)
        return jsonify({"ok": True, "room": updated_room})

