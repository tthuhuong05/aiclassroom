#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script để import tất cả ảnh trong cheat_screenshots vào proctor_events
Giúp hiển thị tất cả ảnh gian lận lên dashboard
"""

import os
import sys
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model.course_model import CourseModel

def extract_user_info_from_path(file_path: str) -> dict:
    """
    Extract username và timestamp từ đường dẫn file
    Format: cheat_screenshots/username_YYYYMMDD_HHMMSS/filename.jpg
    """
    path = Path(file_path)
    folder_name = path.parent.name
    
    # Pattern: username_YYYYMMDD_HHMMSS
    match = re.match(r'^(.+?)_(\d{8})_(\d{6})', folder_name)
    if match:
        username = match.group(1)
        date_str = match.group(2)
        time_str = match.group(3)
        
        # Parse timestamp
        try:
            dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            return {
                "username": username,
                "timestamp": dt.isoformat(),
                "date": date_str,
                "time": time_str
            }
        except Exception:
            pass
    
    # Fallback: dùng tên folder và file
    return {
        "username": folder_name,
        "timestamp": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
        "date": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d"),
        "time": datetime.fromtimestamp(path.stat().st_mtime).strftime("%H%M%S")
    }

def get_user_id_from_username(course_model: CourseModel, username: str) -> int:
    """Tìm user_id từ username"""
    with course_model._connect() as conn:
        cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if row:
            return row[0]
        
        # Thử tìm theo tên thư mục (có thể là user_id)
        try:
            user_id = int(username)
            cur = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if cur.fetchone():
                return user_id
        except ValueError:
            pass
    
    return None

def import_screenshots_to_db(course_model: CourseModel, cheat_screenshots_dir: str = "cheat_screenshots"):
    """
    Scan thư mục cheat_screenshots và tạo event cho mỗi ảnh chưa có trong DB
    """
    screenshots_dir = Path(cheat_screenshots_dir)
    if not screenshots_dir.exists():
        print(f"❌ Thư mục {cheat_screenshots_dir} không tồn tại")
        return
    
    print(f"📂 Đang scan thư mục: {screenshots_dir}")
    
    # Tìm tất cả file .jpg, .png, .jpeg
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(screenshots_dir.rglob(ext))
    
    print(f"📸 Tìm thấy {len(image_files)} ảnh")
    
    imported = 0
    skipped = 0
    errors = 0
    
    for img_path in image_files:
        try:
            # Extract thông tin từ đường dẫn
            info = extract_user_info_from_path(str(img_path))
            username = info["username"]
            screenshot_path = str(img_path).replace("\\", "/")
            
            # Kiểm tra xem đã có event cho ảnh này chưa
            with course_model._connect() as conn:
                cur = conn.execute(
                    "SELECT id FROM proctor_events WHERE meta_json LIKE ?",
                    (f'%"screenshot_path":"{screenshot_path}"%',)
                )
                if cur.fetchone():
                    skipped += 1
                    continue
            
            # Tìm user_id
            user_id = get_user_id_from_username(course_model, username)
            if not user_id:
                # Tạo user giả nếu không tìm thấy (hoặc bỏ qua)
                print(f"⚠️  Không tìm thấy user: {username}, bỏ qua {img_path.name}")
                errors += 1
                continue
            
            # Extract cheating reason từ tên file (nếu có)
            filename = img_path.stem
            cheating_reason = "Phát hiện hành vi gian lận"
            if "_" in filename:
                parts = filename.split("_")
                if len(parts) > 3:
                    reason_part = "_".join(parts[3:])
                    cheating_reason = reason_part.replace("_", " ").title()
            
            # Tạo meta_json
            meta_json = {
                "source": "import_screenshots_script",
                "screenshot_path": screenshot_path,
                "screenshot_url": "/" + screenshot_path.lstrip("/"),
                "cheating_reason": cheating_reason,
                "cheat_type": "cheating_generic",
                "imported_at": datetime.now().isoformat(),
                "original_timestamp": info["timestamp"]
            }
            
            # Tạo event trong DB
            with course_model._connect() as conn:
                conn.execute("""
                    INSERT INTO proctor_events 
                    (user_id, course_id, attempt_id, event_type, confidence, meta_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    0,  # course_id = 0 nếu không xác định được
                    None,  # attempt_id = NULL nếu không xác định được
                    "cheating",
                    0.8,
                    json.dumps(meta_json, ensure_ascii=False),
                    info["timestamp"]
                ))
                conn.commit()
            
            imported += 1
            print(f"✅ Imported: {img_path.name} (user: {username})")
            
        except Exception as e:
            errors += 1
            print(f"❌ Lỗi khi import {img_path.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 Kết quả:")
    print(f"   ✅ Đã import: {imported} ảnh")
    print(f"   ⏭️  Đã bỏ qua (đã có): {skipped} ảnh")
    print(f"   ❌ Lỗi: {errors} ảnh")

if __name__ == "__main__":
    print("="*60)
    print("🔄 IMPORT CHEAT SCREENSHOTS TO DATABASE")
    print("="*60)
    
    course_model = CourseModel()
    import_screenshots_to_db(course_model)
    
    print("\n✅ Hoàn thành!")
    print("📌 Bây giờ hãy refresh dashboard để xem tất cả ảnh")

