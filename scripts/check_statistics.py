import sqlite3
import json

conn = sqlite3.connect('database.db')
conn.row_factory = sqlite3.Row

# Kiểm tra tổng số events
cur = conn.execute('SELECT COUNT(*) as total FROM proctor_events')
total = cur.fetchone()[0]
print(f"Total events: {total}")

# Kiểm tra sample events
cur = conn.execute('SELECT meta_json, event_type FROM proctor_events LIMIT 10')
rows = cur.fetchall()

print("\nSample events:")
for i, row in enumerate(rows, 1):
    event_type = row['event_type']
    meta_json = row['meta_json']
    
    cheat_type = "unknown"
    if meta_json:
        try:
            meta = json.loads(meta_json)
            cheat_type = meta.get('cheat_type', 'unknown')
        except:
            pass
    
    print(f"{i}. Event: {event_type}, Cheat Type: {cheat_type}")

# Kiểm tra thống kê theo cheat_type
cur = conn.execute('SELECT meta_json, event_type FROM proctor_events')
rows = cur.fetchall()

by_type = {}
for row in rows:
    meta = {}
    cheat_type = "unknown"
    
    try:
        if row['meta_json']:
            meta = json.loads(row['meta_json'])
            cheat_type = meta.get("cheat_type", "unknown")
    except:
        pass
    
    if cheat_type in ["normal", None, "unknown"]:
        event_type = row['event_type']
        if event_type and event_type not in ["normal", "unknown"]:
            if "phone" in event_type.lower():
                cheat_type = "phone"
            elif "book" in event_type.lower():
                cheat_type = "book"
            elif "looking" in event_type.lower() or "away" in event_type.lower():
                cheat_type = "looking_away"
            elif "down" in event_type.lower():
                cheat_type = "looking_down"
            elif "face" in event_type.lower() and "no" in event_type.lower():
                cheat_type = "no_face"
            else:
                cheat_type = "cheating_generic"
        else:
            cheat_type = "unknown"
    
    by_type[cheat_type] = by_type.get(cheat_type, 0) + 1

print("\nStatistics by cheat_type:")
for cheat_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
    percent = (count / total * 100) if total > 0 else 0
    print(f"  {cheat_type}: {count} ({percent:.1f}%)")

conn.close()




