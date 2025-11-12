import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel:
    def __init__(self, db_path="database.db"):
        self.db_path = db_path
        self._create_table()

    def _create_table(self):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                avatar_path TEXT DEFAULT NULL
            )
        """)
        connection.commit()
        
        # Thêm cột avatar_path nếu chưa có (cho database cũ)
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN avatar_path TEXT DEFAULT NULL")
            connection.commit()
        except sqlite3.OperationalError:
            # Cột đã tồn tại, bỏ qua
            pass
        
        connection.close()

    def create_user(self, username, password, role="customer", avatar_path=None):
        hashed = generate_password_hash(password)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password, role, avatar_path)
            VALUES (?, ?, ?, ?)
        """, (username, hashed, role, avatar_path))
        conn.commit()
        conn.close()

    def find_user_by_username(self, username):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        return user

    def verify_password(self, input_password, stored_hash):
        return check_password_hash(stored_hash, input_password)

    def update_password(self, username, new_password):
        hashed = generate_password_hash(new_password)
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE users SET password = ? WHERE username = ?
            """, (hashed, username))
            connection.commit()

    def get_all_users(self):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("SELECT id, username, password, role, avatar_path FROM users")
        results = cursor.fetchall()
        connection.close()
        users = []
        for row in results:
            user_id, username, password, role, avatar_path = row
            users.append({
                "id": user_id,
                "username": username,
                "password": password,
                "role": role,
                "avatar_path": avatar_path
            })
        return users

    def get_user_by_id(self, user_id):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("SELECT id, username, password, role, avatar_path FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        connection.close()

        if result:
            user_id, username, password, role, avatar_path = result
            return {
                "id": user_id,
                "username": username,
                "password": password,
                "role": role,
                "avatar_path": avatar_path
            }
        return None

    def update_user(self, user_id, username, password=None, role=None):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            if password:
                hashed_password = generate_password_hash(password)
                cursor.execute("""
                    UPDATE users
                    SET username = ?, password = ?, role = ?
                    WHERE id = ?
                """, (username, hashed_password, role, user_id))
            else:
                cursor.execute("""
                    UPDATE users
                    SET username = ?, role = ?
                    WHERE id = ?
                """, (username, role, user_id))
            connection.commit()

    def delete_user(self, user_id):
        connection = sqlite3.connect(self.db_path)
        cursor = connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.commit()
        connection.close()


    def find_by_email(self, email):
      conn = sqlite3.connect(self.db_path)
      conn.row_factory = sqlite3.Row
      cursor = conn.cursor()
      cursor.execute("SELECT * FROM users WHERE username = ?", (email,))
      user = cursor.fetchone()
      conn.close()
      return user

    def update_avatar(self, username, avatar_path):
        """Cập nhật avatar cho user"""
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE users SET avatar_path = ? WHERE username = ?
            """, (avatar_path, username))
            connection.commit()
    
    def update_avatar_by_id(self, user_id, avatar_path):
        """Cập nhật avatar cho user theo ID"""
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE users SET avatar_path = ? WHERE id = ?
            """, (avatar_path, user_id))
            connection.commit()
    
    def find_user_by_id(self, user_id):
        """Tìm user theo ID (như trong face recognition API)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user


