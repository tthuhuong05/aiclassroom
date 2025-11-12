# create_video.py
import os, sys
sys.path.append(os.path.dirname(__file__))

from services.doc_video_service import make_ai_lecture_video, make_video_from_file

SRC  = sys.argv[1] if len(sys.argv) > 1 else "sample.pdf"  # đường dẫn file tài liệu
OUT  = sys.argv[2] if len(sys.argv) > 2 else "out"
TITLE= sys.argv[3] if len(sys.argv) > 3 else None

try:
    # Full “NotebookLM-style”: AI phân tích → slide → hình → voice
    result = make_ai_lecture_video(
        src_path=SRC,
        out_dir=OUT,
        title=TITLE,
        width=1280, height=720,
        wpm=140,
        use_human_voice=True,     # tắt nếu chưa có ElevenLabs
        include_images=True       # tắt nếu chưa có Pexels/Unsplash
    )
except Exception as e:
    print("AI pipeline failed, falling back:", e)
    result = make_video_from_file(SRC, OUT, TITLE)

print("\n✅ DONE")
for k, v in result.items():
    print(f"{k}: {v}")
