# services/image_search_service.py
import os
import re
import uuid
import tempfile
from typing import Optional, List, Dict, Union

import requests

UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
PEXELS_KEY   = os.getenv("PEXELS_API_KEY")

DEFAULT_TIMEOUT = float(os.getenv("IMAGE_HTTP_TIMEOUT", "20"))
DEFAULT_ORIENTATION = os.getenv("IMAGE_ORIENTATION", "landscape")  # landscape|portrait|square


# ---------- Helpers ----------
def _download(url: str, ext: Optional[str] = None) -> Optional[str]:
    """Tải ảnh về file tạm và trả về đường dẫn; None nếu lỗi."""
    try:
        r = requests.get(url, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        if not ext:
            ext = ".jpg"
        path = os.path.join(tempfile.gettempdir(), f"aiimg_{uuid.uuid4().hex[:8]}{ext}")
        with open(path, "wb") as f:
            f.write(r.content)
        return path
    except Exception:
        return None


def _norm(s: Optional[str]) -> str:
    return (s or "").strip()


def _tokenize(s: str) -> List[str]:
    # tách từ đơn giản, bỏ các từ rất ngắn
    return [w.lower() for w in re.findall(r"[A-Za-zÀ-ỹ0-9\-]+", s) if len(w) >= 4]


# ---------- Public API ----------
def search_images(
    query: str,
    count: int = 3,
    orientation: str = DEFAULT_ORIENTATION
) -> List[Dict]:
    """
    Tìm nhiều ảnh ứng viên theo từ khoá.
    Trả về list dict: {source, url, page_url, author_name, author_url, width, height, description}
    Ưu tiên Pexels trước, sau đó Unsplash.
    """
    results: List[Dict] = []

    # --- PEXELS ---
    if PEXELS_KEY:
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                params={"query": query, "per_page": max(1, min(5, count)), "orientation": orientation},
                headers={"Authorization": PEXELS_KEY},
                timeout=DEFAULT_TIMEOUT,
            )
            if r.ok:
                data = r.json() or {}
                for p in (data.get("photos") or []):
                    results.append({
                        "source": "pexels",
                        "id": p.get("id"),
                        "url": (p.get("src") or {}).get("large") or (p.get("src") or {}).get("original"),
                        "page_url": p.get("url"),
                        "author_name": p.get("photographer"),
                        "author_url": p.get("photographer_url"),
                        "width": p.get("width"),
                        "height": p.get("height"),
                        "description": p.get("alt"),
                    })
        except Exception:
            pass

    # --- UNSPLASH ---
    if UNSPLASH_KEY:
        try:
            r = requests.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": query,
                    "per_page": max(1, min(5, count)),
                    "orientation": orientation,
                    "content_filter": "high",
                },
                headers={"Authorization": f"Client-ID {UNSPLASH_KEY}", "Accept-Version": "v1"},
                timeout=DEFAULT_TIMEOUT,
            )
            if r.ok:
                data = r.json() or {}
                for p in (data.get("results") or []):
                    results.append({
                        "source": "unsplash",
                        "id": p.get("id"),
                        "url": (p.get("urls") or {}).get("regular") or (p.get("urls") or {}).get("full"),
                        "page_url": (p.get("links") or {}).get("html"),
                        "author_name": ((p.get("user") or {}).get("name")),
                        "author_url": ((p.get("user") or {}).get("links") or {}).get("html"),
                        "width": p.get("width"),
                        "height": p.get("height"),
                        "description": p.get("alt_description") or p.get("description"),
                    })
        except Exception:
            pass

    # Loại ứng viên thiếu URL
    dedup = []
    seen_urls = set()
    for item in results:
        url = _norm(item.get("url"))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        dedup.append(item)

    return dedup


def download_image(candidate: Union[str, Dict]) -> Dict:
    """
    Tải ảnh từ URL hoặc từ dict ứng viên.
    Trả về: {"success": bool, "file_path": str|None, "source": "..."}
    """
    url = candidate
    src = "url"
    if isinstance(candidate, dict):
        url = candidate.get("url")
        src = candidate.get("source") or "unknown"

    path = _download(_norm(url))
    return {"success": bool(path), "file_path": path, "source": src}


def _score_candidate(candidate: Dict, query: str, orientation: str) -> float:
    """
    Điểm đơn giản để chọn ảnh tốt nhất:
    - Ưu tiên cùng orientation
    - Ưu tiên kích thước lớn
    - Ưu tiên mô tả khớp nhiều từ khoá
    - Ưu tiên Pexels (chất lượng đồng đều) một chút
    """
    w = candidate.get("width") or 0
    h = candidate.get("height") or 0
    desc = _norm(candidate.get("description")).lower()

    # size score
    size_score = min(w, h) / 1000.0

    # orientation score
    ori_score = 0.0
    if orientation == "landscape" and w > h:
        ori_score = 1.0
    elif orientation == "portrait" and h > w:
        ori_score = 1.0
    elif orientation == "square" and abs(w - h) < 50:
        ori_score = 1.0

    # text match score
    tokens = _tokenize(query)
    text_score = sum(1.0 for t in tokens if t in desc)

    # provider preference
    provider_bonus = 0.2 if candidate.get("source") == "pexels" else 0.0

    return size_score + ori_score + text_score + provider_bonus


def search_image(query: str, orientation: str = DEFAULT_ORIENTATION) -> Optional[str]:
    """
    Tương thích phiên bản cũ: trả về đường dẫn file ảnh đã tải về.
    Dưới nắp capo: thử nhiều ứng viên từ Pexels/Unsplash và chọn ảnh có điểm cao nhất.
    """
    candidates = search_images(query, count=4, orientation=orientation)
    if not candidates:
        return None

    # Chọn ứng viên tốt nhất theo điểm
    best = max(candidates, key=lambda c: _score_candidate(c, query, orientation))

    res = download_image(best)
    if res.get("success"):
        return res.get("file_path")

    # Fallback: thử lần lượt các ứng viên còn lại
    for c in candidates:
        if c is best:
            continue
        res = download_image(c)
        if res.get("success"):
            return res.get("file_path")

    return None

# --- THÊM MỚI ---
def search_best_image_for_queries(
    queries: List[str], 
    min_score: float = 1.2, 
    orientation: str = DEFAULT_ORIENTATION
) -> Optional[str]:
    """
    Duyệt qua nhiều truy vấn, gom các ứng viên từ Pexels/Unsplash,
    chấm điểm & chỉ tải ảnh nếu đạt min_score. Không đạt -> trả None.
    """
    all_candidates: List[Dict] = []
    seen = set()
    for q in queries:
        cands = search_images(q, count=4, orientation=orientation)
        for c in cands:
            key = c.get("source"), c.get("id") or c.get("url")
            if key not in seen:
                seen.add(key)
                # đính kèm truy vấn gốc để tính điểm
                c["_query"] = q
                all_candidates.append(c)

    if not all_candidates:
        return None

    # chấm điểm theo truy vấn gốc của từng ứng viên
    scored = []
    for c in all_candidates:
        s = _score_candidate(c, c.get("_query",""), orientation)
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)

    top_score, top_c = scored[0]
    if top_score < float(min_score):
        return None  # ảnh không đủ khớp, bỏ

    res = download_image(top_c)
    return res.get("file_path") if res.get("success") else None
