import sqlite3
from typing import List, Dict, Any, Optional
import datetime
import uuid
import secrets


class StudyRoomModel:
    """
    Model quản lý phòng học (Study Rooms) - chức năng Social
    """
    def __init__(self, db_path: str = "database.db"):
        self.db_path = db_path
        self._create_table()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _generate_unique_slug(self, cursor) -> str:
        while True:
            candidate = uuid.uuid4().hex[:8]
            cursor.execute("SELECT 1 FROM study_rooms WHERE slug = ?", (candidate,))
            if not cursor.fetchone():
                return candidate

    def _generate_invite_key(self) -> str:
        # Short but hard to guess token
        return secrets.token_urlsafe(4)

    def _backfill_slug_and_invite_keys(self, conn):
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM study_rooms WHERE slug IS NULL OR slug = ''")
        rooms_missing_slug = cursor.fetchall()
        for row in rooms_missing_slug:
            slug = self._generate_unique_slug(cursor)
            cursor.execute(
                "UPDATE study_rooms SET slug = ? WHERE id = ?",
                (slug, row["id"])
            )

        cursor.execute("SELECT id FROM study_rooms WHERE invite_key IS NULL OR invite_key = ''")
        rooms_missing_key = cursor.fetchall()
        for row in rooms_missing_key:
            key = self._generate_invite_key()
            cursor.execute(
                "UPDATE study_rooms SET invite_key = ? WHERE id = ?",
                (key, row["id"])
            )

        conn.commit()

    def _create_table(self):
        """Tạo bảng study_rooms và study_room_members"""
        with self._connect() as conn:
            # Bảng phòng học
            conn.execute("""
                CREATE TABLE IF NOT EXISTS study_rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL,
                    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    max_members INTEGER DEFAULT 10,
                    is_public INTEGER DEFAULT 1,
                    language TEXT,
                    level TEXT,
                    topic TEXT,
                    slug TEXT,
                    invite_key TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            
            # Thêm các cột mới nếu chưa có (migration)
            for column in ("language TEXT", "level TEXT", "topic TEXT", "slug TEXT", "invite_key TEXT", "last_activity_at TEXT"):
                try:
                    conn.execute(f"ALTER TABLE study_rooms ADD COLUMN {column}")
                except sqlite3.OperationalError:
                    pass
            
            # Bảng thành viên phòng học
            conn.execute("""
                CREATE TABLE IF NOT EXISTS study_room_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id INTEGER NOT NULL REFERENCES study_rooms(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    role TEXT DEFAULT 'member',
                    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(room_id, user_id)
                )
            """)
            
            # Tạo indexes
            conn.execute("CREATE INDEX IF NOT EXISTS ix_study_rooms_created_by ON study_rooms(created_by)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_study_rooms_course ON study_rooms(course_id)")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_study_rooms_slug ON study_rooms(slug)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_study_room_members_room ON study_room_members(room_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_study_room_members_user ON study_room_members(user_id)")
            
            self._backfill_slug_and_invite_keys(conn)
            
            conn.commit()

    def create_room(self, name: str, description: str, created_by: int, 
                   course_id: Optional[int] = None, max_members: int = 10, 
                   is_public: bool = True, language: Optional[str] = None,
                   level: Optional[str] = None, topic: Optional[str] = None) -> int:
        """Tạo phòng học mới"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                
                # Kiểm tra user có tồn tại không
                cursor.execute("SELECT id FROM users WHERE id = ?", (created_by,))
                if not cursor.fetchone():
                    raise ValueError(f"User {created_by} không tồn tại")
                
                # Kiểm tra course_id nếu có
                if course_id:
                    cursor.execute("SELECT id FROM courses WHERE id = ?", (course_id,))
                    if not cursor.fetchone():
                        print(f"[WARN] Course {course_id} không tồn tại, bỏ qua course_id")
                        course_id = None
                
                now = datetime.datetime.now().isoformat()
                slug = self._generate_unique_slug(cursor)
                invite_key = self._generate_invite_key()
                
                print(f"[DEBUG StudyRoomModel] Inserting room: name={name}, created_by={created_by}, course_id={course_id}")
                
                cursor.execute("""
                    INSERT INTO study_rooms (name, description, course_id, created_by, 
                                           max_members, is_public, language, level, topic,
                                           slug, invite_key,
                                           created_at, updated_at, last_activity_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, description or "", course_id, created_by, max_members, 
                      1 if is_public else 0, language, level, topic, slug, invite_key, now, now, now))
                room_id = cursor.lastrowid
                
                print(f"[DEBUG StudyRoomModel] Room created with ID: {room_id}")
                
                # Tự động thêm người tạo vào phòng với role 'admin'
                try:
                    cursor.execute("""
                        INSERT INTO study_room_members (room_id, user_id, role, joined_at)
                        VALUES (?, ?, ?, ?)
                    """, (room_id, created_by, 'admin', now))
                    print(f"[DEBUG StudyRoomModel] Added creator as admin member")
                except sqlite3.IntegrityError as e:
                    print(f"[WARN StudyRoomModel] Member already exists: {e}")
                    # Nếu đã tồn tại thì bỏ qua
                    pass
                
                conn.commit()
                print(f"[DEBUG StudyRoomModel] Room creation committed successfully")
                return room_id
        except sqlite3.Error as e:
            print(f"[ERROR StudyRoomModel] Database error: {e}")
            raise Exception(f"Lỗi database: {str(e)}")
        except Exception as e:
            print(f"[ERROR StudyRoomModel] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            raise

    def get_room_by_id(self, room_id: int) -> Optional[Dict[str, Any]]:
        """Lấy thông tin phòng học theo ID"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sr.*, 
                       u.username as creator_username,
                       c.title as course_title,
                       COUNT(srm.user_id) as member_count
                FROM study_rooms sr
                LEFT JOIN users u ON sr.created_by = u.id
                LEFT JOIN courses c ON sr.course_id = c.id
                LEFT JOIN study_room_members srm ON sr.id = srm.room_id
                WHERE sr.id = ?
                GROUP BY sr.id
            """, (room_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_room_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Lấy thông tin phòng học theo slug"""
        if not slug:
            return None
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sr.*, 
                       u.username as creator_username,
                       c.title as course_title,
                       COUNT(srm.user_id) as member_count
                FROM study_rooms sr
                LEFT JOIN users u ON sr.created_by = u.id
                LEFT JOIN courses c ON sr.course_id = c.id
                LEFT JOIN study_room_members srm ON sr.id = srm.room_id
                WHERE sr.slug = ?
                GROUP BY sr.id
            """, (slug,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_rooms(self, user_id: Optional[int] = None, 
                      is_public_only: bool = False) -> List[Dict[str, Any]]:
        """Lấy danh sách tất cả phòng học"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Sử dụng user_id thực tế hoặc -1 (sẽ không match với bất kỳ user nào)
            check_user_id = user_id if user_id is not None else -1
            
            if is_public_only:
                query = """
                    SELECT sr.*, 
                           u.username as creator_username,
                           c.title as course_title,
                           COUNT(DISTINCT srm.user_id) as member_count,
                           CASE WHEN EXISTS (
                               SELECT 1 FROM study_room_members 
                               WHERE room_id = sr.id AND user_id = ?
                           ) THEN 1 ELSE 0 END as is_member
                    FROM study_rooms sr
                    LEFT JOIN users u ON sr.created_by = u.id
                    LEFT JOIN courses c ON sr.course_id = c.id
                    LEFT JOIN study_room_members srm ON sr.id = srm.room_id
                    WHERE sr.is_public = 1
                    GROUP BY sr.id
                    ORDER BY sr.created_at DESC
                """
                cursor.execute(query, (check_user_id,))
            else:
                query = """
                    SELECT sr.*, 
                           u.username as creator_username,
                           c.title as course_title,
                           COUNT(DISTINCT srm.user_id) as member_count,
                           CASE WHEN EXISTS (
                               SELECT 1 FROM study_room_members 
                               WHERE room_id = sr.id AND user_id = ?
                           ) THEN 1 ELSE 0 END as is_member
                    FROM study_rooms sr
                    LEFT JOIN users u ON sr.created_by = u.id
                    LEFT JOIN courses c ON sr.course_id = c.id
                    LEFT JOIN study_room_members srm ON sr.id = srm.room_id
                    GROUP BY sr.id
                    ORDER BY sr.created_at DESC
                """
                cursor.execute(query, (check_user_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_user_rooms(self, user_id: int) -> List[Dict[str, Any]]:
        """Lấy danh sách phòng học của user"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT sr.*, 
                       u.username as creator_username,
                       c.title as course_title,
                       COUNT(DISTINCT srm.user_id) as member_count,
                       srm.role as user_role
                FROM study_rooms sr
                LEFT JOIN users u ON sr.created_by = u.id
                LEFT JOIN courses c ON sr.course_id = c.id
                LEFT JOIN study_room_members srm ON sr.id = srm.room_id
                INNER JOIN study_room_members my_member ON sr.id = my_member.room_id
                WHERE my_member.user_id = ?
                GROUP BY sr.id
                ORDER BY sr.created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def join_room(self, room_id: int, user_id: int) -> bool:
        """Tham gia phòng học"""
        with self._connect() as conn:
            # Kiểm tra xem đã tham gia chưa
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM study_room_members 
                WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            if cursor.fetchone():
                return False  # Đã tham gia rồi
            
            # Kiểm tra số lượng thành viên
            cursor.execute("""
                SELECT max_members, COUNT(user_id) as current_count
                FROM study_rooms sr
                LEFT JOIN study_room_members srm ON sr.id = srm.room_id
                WHERE sr.id = ?
                GROUP BY sr.id
            """, (room_id,))
            row = cursor.fetchone()
            if row and row['current_count'] >= row['max_members']:
                return False  # Đã đầy
            
            # Thêm thành viên
            now = datetime.datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO study_room_members (room_id, user_id, role, joined_at)
                VALUES (?, ?, ?, ?)
            """, (room_id, user_id, 'member', now))
            # Cập nhật last_activity_at
            cursor.execute("""
                UPDATE study_rooms SET last_activity_at = ? WHERE id = ?
            """, (now, room_id))
            conn.commit()
            return True

    def leave_room(self, room_id: int, user_id: int) -> bool:
        """Rời khỏi phòng học (không cho phép admin rời)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Kiểm tra role
            cursor.execute("""
                SELECT role FROM study_room_members 
                WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            row = cursor.fetchone()
            if not row:
                return False
            if row['role'] == 'admin':
                return False  # Admin không thể rời
            
            cursor.execute("""
                DELETE FROM study_room_members 
                WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            # Cập nhật last_activity_at
            now = datetime.datetime.now().isoformat()
            cursor.execute("""
                UPDATE study_rooms SET last_activity_at = ? WHERE id = ?
            """, (now, room_id))
            conn.commit()
            return True

    def get_room_members(self, room_id: int) -> List[Dict[str, Any]]:
        """Lấy danh sách thành viên trong phòng"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT srm.*, u.username, u.avatar_path
                FROM study_room_members srm
                JOIN users u ON srm.user_id = u.id
                WHERE srm.room_id = ?
                ORDER BY 
                    CASE srm.role 
                        WHEN 'admin' THEN 1 
                        ELSE 2 
                    END,
                    srm.joined_at ASC
            """, (room_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_member_role(self, room_id: int, user_id: int) -> Optional[str]:
        """Lấy role của thành viên trong phòng"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role 
                FROM study_room_members 
                WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            row = cursor.fetchone()
            if row:
                try:
                    return row["role"]
                except Exception:
                    return row[0]
            return None

    def delete_room(self, room_id: int, user_id: int) -> bool:
        """Xóa phòng học (chỉ admin mới được xóa)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Kiểm tra quyền
            cursor.execute("""
                SELECT role FROM study_room_members 
                WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            row = cursor.fetchone()
            if not row or row['role'] != 'admin':
                return False
            
            cursor.execute("DELETE FROM study_rooms WHERE id = ?", (room_id,))
            conn.commit()
            return True

    def update_room(self, room_id: int, user_id: int, name: Optional[str] = None,
                   description: Optional[str] = None, max_members: Optional[int] = None,
                   is_public: Optional[bool] = None, language: Optional[str] = None,
                   level: Optional[str] = None, topic: Optional[str] = None) -> bool:
        """Cập nhật thông tin phòng học (chỉ admin)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Kiểm tra quyền
            cursor.execute("""
                SELECT role FROM study_room_members 
                WHERE room_id = ? AND user_id = ?
            """, (room_id, user_id))
            row = cursor.fetchone()
            if not row or row['role'] != 'admin':
                return False
            
            updates = []
            params = []
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if max_members is not None:
                updates.append("max_members = ?")
                params.append(max_members)
            if is_public is not None:
                updates.append("is_public = ?")
                params.append(1 if is_public else 0)
            if language is not None:
                updates.append("language = ?")
                params.append(language)
            if level is not None:
                updates.append("level = ?")
                params.append(level)
            if topic is not None:
                updates.append("topic = ?")
                params.append(topic)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.datetime.now().isoformat())
            params.append(room_id)
            
            cursor.execute(f"""
                UPDATE study_rooms 
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            conn.commit()
            return True

    def cleanup_empty_rooms(self, minutes: int = 1) -> int:
        """Xóa các phòng không có ai trong vòng N phút"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Tính thời gian cutoff
            cutoff_time = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).isoformat()
            
            # Tìm các phòng không có thành viên và last_activity_at < cutoff_time
            cursor.execute("""
                SELECT sr.id, COUNT(srm.id) as member_count
                FROM study_rooms sr
                LEFT JOIN study_room_members srm ON sr.id = srm.room_id
                GROUP BY sr.id
                HAVING member_count = 0
                AND (sr.last_activity_at IS NULL OR sr.last_activity_at < ?)
            """, (cutoff_time,))
            
            empty_rooms = cursor.fetchall()
            deleted_count = 0
            
            for row in empty_rooms:
                room_id = row['id'] if isinstance(row, dict) else row[0]
                try:
                    cursor.execute("DELETE FROM study_rooms WHERE id = ?", (room_id,))
                    deleted_count += 1
                    print(f"[CLEANUP] Đã xóa phòng {room_id} (không có thành viên)")
                except Exception as e:
                    print(f"[WARN] Failed to delete room {room_id}: {e}")
            
            conn.commit()
            return deleted_count

