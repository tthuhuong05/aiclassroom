# controller/progress_controller.py
from flask import request, jsonify, session
import sqlite3, datetime

DB_PATH = "database.db"  # trỏ tới DB bạn đang dùng

def _db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

class ProgressController:
    def get_outline(self, course_id:int):
        with _db() as cn:
            cn.row_factory = sqlite3.Row
            secs = cn.execute("""SELECT * FROM course_sections 
                                  WHERE course_id=? ORDER BY sort_order, id""", (course_id,)).fetchall()
            items = cn.execute("""SELECT i.* FROM course_items i 
                                  JOIN course_sections s ON s.id=i.section_id
                                  WHERE s.course_id=? ORDER BY s.sort_order,i.sort_order,i.id""", (course_id,)).fetchall()
        # group
        sec_map = {s["id"]: {**dict(s), "items": []} for s in secs}
        for it in items:
            sec_map[it["section_id"]]["items"].append(dict(it))
        return list(sec_map.values())

    def get_user_progress(self, course_id:int, user_id:int):
        with _db() as cn:
            cn.row_factory = sqlite3.Row
            rows = cn.execute("""SELECT item_id, status, seconds_watched, score, completed_at 
                                FROM user_progress WHERE user_id=? AND course_id=?""", 
                                (user_id, course_id)).fetchall()
        return {r["item_id"]: dict(r) for r in rows}

    def upsert(self):
        p = request.get_json(force=True)
        user = session.get("user") or {}
        user_id = p.get("user_id") or user.get("id") or user.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Not logged in"}), 401
        item_id   = int(p["item_id"])
        course_id = int(p["course_id"])
        status    = p.get("status", "in_progress")
        seconds   = int(p.get("seconds_watched") or 0)
        score     = p.get("score")
        done      = 1 if status == "done" else 0
        now       = datetime.datetime.utcnow().isoformat(" ")

        with _db() as cn:
            cn.execute("""
              INSERT INTO user_progress(user_id, course_id, item_id, status, seconds_watched, score, completed_at)
              VALUES(?,?,?,?,?,?,CASE WHEN ?=1 THEN ? ELSE NULL END)
              ON CONFLICT(user_id, item_id) DO UPDATE SET
                status=excluded.status,
                seconds_watched=MAX(user_progress.seconds_watched, excluded.seconds_watched),
                score=COALESCE(excluded.score, user_progress.score),
                completed_at=CASE 
                  WHEN excluded.status='done' THEN excluded.completed_at
                  ELSE user_progress.completed_at END
            """, (user_id, course_id, item_id, status, seconds, score, done, now))
        return jsonify({"ok": True})
