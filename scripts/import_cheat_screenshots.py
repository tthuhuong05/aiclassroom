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
    Returns: dict với imported, skipped, errors counts
    """
    screenshots_dir = Path(cheat_screenshots_dir)
    if not screenshots_dir.exists():
        print(f"❌ Thư mục {cheat_screenshots_dir} không tồn tại")
        return {"imported": 0, "skipped": 0, "errors": 0}
    
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
            # Kiểm tra bằng cả screenshot_path và screenshot_url
            with course_model._connect() as conn:
                # Escape special characters cho LIKE query
                escaped_path = screenshot_path.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                cur = conn.execute(
                    "SELECT id FROM proctor_events WHERE meta_json LIKE ? OR meta_json LIKE ?",
                    (f'%"screenshot_path":"{escaped_path}"%', f'%{escaped_path}%')
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
            cheat_type = "cheating_generic"
            
            # Parse tên file: YYYYMMDD_HHMMSS_microseconds_REASON.jpg
            if "_" in filename:
                parts = filename.split("_")
                if len(parts) >= 4:
                    # Lấy phần reason (từ phần thứ 3 trở đi)
                    reason_parts = parts[3:]
                    reason_text = "_".join(reason_parts)
                    
                    # Decode và format lại - xử lý encoding issues
                    try:
                        # Thử decode từ Windows-1252 hoặc latin-1 sang UTF-8
                        if 'á»' in reason_text or 'Ă' in reason_text:
                            # Có vẻ như là Windows-1252 encoding
                            reason_text = reason_text.encode('latin-1').decode('utf-8', errors='ignore')
                        else:
                            # Thử decode trực tiếp
                            reason_text = reason_text.encode('utf-8').decode('utf-8', errors='ignore')
                    except:
                        # Nếu không decode được, giữ nguyên và clean
                        pass
                    
                    # Clean và format lại
                    cheating_reason = reason_text.replace("_", " ").strip()
                    
                    # Map các từ khóa phổ biến
                    if "PHAT HIEN" in cheating_reason.upper() or "PHÁT HIỆN" in cheating_reason:
                        if "NHIN RA NGOAI" in cheating_reason.upper() or "NHÌN RA NGOÀI" in cheating_reason:
                            cheating_reason = "Phát hiện nhìn ra ngoài màn hình"
                        elif "HANH VI GIAN LAN" in cheating_reason.upper() or "HÀNH VI GIAN LẬN" in cheating_reason:
                            cheating_reason = "Phát hiện hành vi gian lận"
                        elif "DIEN THOAI" in cheating_reason.upper() or "ĐIỆN THOẠI" in cheating_reason:
                            cheating_reason = "Phát hiện sử dụng điện thoại"
                        elif "SACH" in cheating_reason.upper() or "SÁCH" in cheating_reason:
                            cheating_reason = "Phát hiện sử dụng sách"
                        elif "CUOI XUONG" in cheating_reason.upper() or "CÚI XUỐNG" in cheating_reason:
                            cheating_reason = "Phát hiện cúi xuống"
                        elif "KHONG CO KHUON MAT" in cheating_reason.upper() or "KHÔNG CÓ KHUÔN MẶT" in cheating_reason:
                            cheating_reason = "Phát hiện không có khuôn mặt"
                        elif "NHIEU KHUON MAT" in cheating_reason.upper() or "NHIỀU KHUÔN MẶT" in cheating_reason:
                            cheating_reason = "Phát hiện nhiều khuôn mặt"
                    
                    # Map reason thành cheat_type
                    reason_lower = cheating_reason.lower()
                    if "nhìn ra ngoài" in reason_lower or "looking away" in reason_lower:
                        cheat_type = "looking_away"
                    elif "điện thoại" in reason_lower or "phone" in reason_lower:
                        cheat_type = "phone"
                    elif "sách" in reason_lower or "book" in reason_lower:
                        cheat_type = "book"
                    elif "tablet" in reason_lower:
                        cheat_type = "tablet"
                    elif "gọi điện" in reason_lower or "phone_call" in reason_lower:
                        cheat_type = "phone_call"
                    elif "cúi xuống" in reason_lower or "looking down" in reason_lower:
                        cheat_type = "looking_down"
                    elif "không có khuôn mặt" in reason_lower or "no face" in reason_lower:
                        cheat_type = "no_face"
                    elif "nhiều khuôn mặt" in reason_lower or "multiple faces" in reason_lower:
                        cheat_type = "multiple_faces"
            
            # Tạo meta_json với đầy đủ thông tin
            meta_json = {
                "source": "import_screenshots_script",
                "screenshot_path": screenshot_path,
                "screenshot_url": "/" + screenshot_path.lstrip("/"),
                "cheating_reason": cheating_reason,
                "cheat_type": cheat_type,
                "detected_date": info["date"],
                "detected_time": info["time"],
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
    
    # Return counts để API có thể sử dụng
    return {"imported": imported, "skipped": skipped, "errors": errors}

if __name__ == "__main__":
    print("="*60)
    print("🔄 IMPORT CHEAT SCREENSHOTS TO DATABASE")
    print("="*60)
    
    course_model = CourseModel()
    import_screenshots_to_db(course_model)
    
    print("\n✅ Hoàn thành!")
    print("📌 Bây giờ hãy refresh dashboard để xem tất cả ảnh")

