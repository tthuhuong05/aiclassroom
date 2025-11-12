# -*- coding: utf-8 -*-
"""
AI Image Service — multi-backend template

Implements 2 functions used by doc_video_service.py:
  - is_ai_image_available() -> bool
  - generate_thematic_image(prompt, negative_prompt, width, height, model) -> dict|bytes|str

Backends supported (auto-detected in this order):
  1) AUTOMATIC1111 Stable Diffusion Web UI (local): set env A1111_BASE_URL (default http://127.0.0.1:7860)
  2) Stability AI SDXL API: set env STABILITY_API_KEY
  3) OpenAI Images API: set env OPENAI_API_KEY (uses gpt-image-1)

Return format (any of):
  - {"image_bytes": <bytes>}
  - {"image_path": "/path/to/file.jpg"} OR {"path": "/path/to/file.jpg"}
  - raw bytes OR a file path string

All branches raise descriptive exceptions so doc_video_service can log why generation failed.
"""
from __future__ import annotations
import os, io, base64, tempfile
from typing import Optional, Dict, Any

import requests
from PIL import Image

# ==== Helpers =============================================================

def _b64_to_bytes(b64: str) -> bytes:
    if b64.startswith("data:image"):
        b64 = b64.split(",", 1)[-1]
    return base64.b64decode(b64)


def _save_bytes_as_temp_png(data: bytes) -> str:
    fd, path = tempfile.mkstemp(prefix="aiimg_", suffix=".png")
    os.close(fd)
    with open(path, "wb") as f:
        f.write(data)
    return path


# ==== Backend 1: AUTOMATIC1111 (local) ====================================
A1111_BASE_URL = os.getenv("A1111_BASE_URL", "http://127.0.0.1:7860").rstrip("/")


def _a1111_available() -> bool:
    try:
        r = requests.get(f"{A1111_BASE_URL}/sdapi/v1/sd-models", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def _a1111_generate(prompt: str, negative: str, width: int, height: int, model: str = "sdxl") -> bytes:
    # Snap to multiples of 64 to stay compatible with most checkpoints
    w = max(256, (int(width) // 64) * 64)
    h = max(256, (int(height) // 64) * 64)
    payload = {
        "prompt": prompt,
        "negative_prompt": negative or "",
        "width": w,
        "height": h,
        "steps": 28,
        "cfg_scale": 6.5,
        "sampler_name": "DPM++ 2M Karras",
        "clip_skip": 2,
        "seed": -1,
        "enable_hr": False,
    }
    r = requests.post(f"{A1111_BASE_URL}/sdapi/v1/txt2img", json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"A1111 txt2img status {r.status_code}: {r.text[:300]}")
    data = r.json()
    images = data.get("images") or []
    if not images:
        raise RuntimeError("A1111 returned 0 images")
    return _b64_to_bytes(images[0])


# ==== Backend 2: STABILITY AI (SDXL) ======================================
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "").strip()


def _stability_available() -> bool:
    return bool(STABILITY_API_KEY)


def _stability_generate(prompt: str, negative: str, width: int, height: int, model: str = "sdxl") -> bytes:
    """Generate via Stability SDXL using ONLY allowed dimensions to avoid 400 errors.
    Picks the nearest valid size from the official list for v1 engines.
    """
    engine = "stable-diffusion-xl-1024-v1-0"
    url = f"https://api.stability.ai/v1/generation/{engine}/text-to-image"
    headers = {"Authorization": f"Bearer {STABILITY_API_KEY}", "Accept": "application/json"}

    # Allowed sizes for SDXL v1 according to server error hints
    allowed_landscape = [(1536,640), (1344,768), (1216,832), (1152,896)]
    allowed_portrait  = [(640,1536), (768,1344), (832,1216), (896,1152)]
    allowed_square    = [(1024,1024)]

    if width == height:
        candidates = allowed_square
    elif width > height:
        candidates = allowed_landscape
    else:
        candidates = allowed_portrait

    def _dist(a, b):
        return abs(a[0]-b[0]) + abs(a[1]-b[1])

    w, h = min(candidates, key=lambda wh: _dist(wh, (int(width), int(height))))
    print(f"[AI IMG][STABILITY] using {w}x{h} (requested {width}x{height})")

    payload = {
        "text_prompts": [{"text": prompt, "weight": 1.0}] + ([{"text": negative, "weight": -1.0}] if negative else []),
        "cfg_scale": 7,
        "width": w,
        "height": h,
        "samples": 1,
        "steps": 30,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"Stability status {r.status_code}: {r.text[:300]}")
    out = r.json()
    arts = out.get("artifacts") or []
    if not arts:
        raise RuntimeError("Stability returned 0 artifacts")
    b64 = arts[0].get("base64")
    if not b64:
        raise RuntimeError("No base64 in Stability response")
    return _b64_to_bytes(b64)


# ==== Backend 3: OpenAI Images ============================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


def _openai_available() -> bool:
    return bool(OPENAI_API_KEY)


def _openai_generate(prompt: str, negative: str, width: int, height: int, model: str = "gpt-image-1") -> bytes:
    # OpenAI Images chỉ hỗ trợ size: 1024x1024, 1792x1024 (landscape), 1024x1792 (portrait)
    landscape = width >= height
    size = "1792x1024" if landscape else "1024x1792"

    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    prompt_full = prompt + ". Do not include people, faces, hands, or text. Photorealistic."
    payload = {"model": model, "prompt": prompt_full, "size": size, "n": 1}
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI status {r.status_code}: {r.text[:300]}")
    data = r.json()
    arr = data.get("data") or []
    if not arr:
        raise RuntimeError("OpenAI returned 0 images")
    b64 = arr[0].get("b64_json")
    if not b64:
        raise RuntimeError("No b64_json in OpenAI response")
    return _b64_to_bytes(b64)


# ==== Backend 4: Google Gemini Images (AI Studio) ==========================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_IMAGE_MODEL = os.getenv("GEMINI_IMAGE_MODEL", "imagen-3.0").strip()
PREFERRED_AI_BACKEND = os.getenv("PREFERRED_AI_BACKEND", "").upper().strip()


def _gemini_available() -> bool:
    return bool(GOOGLE_API_KEY)


def _gemini_generate(prompt: str, negative: str, width: int, height: int, model: str = None) -> bytes:
    """Try Google AI Studio Images API. Different deployments may expose slightly different endpoints,
    so we attempt a few common ones. We also choose a safe 16:9 size allowed by Imagen 3.
    """
    # Chọn kích thước 16:9 an toàn được tài liệu cho phép (bội số 64): 1152x896 hoặc 1344x768/1536x640.
    # Ưu tiên 1344x768 nếu chiều rộng yêu cầu lớn; nếu không, dùng 1152x896.
    desired_w, desired_h = (1344, 768) if width >= 1280 else (1152, 896)

    headers = {"Content-Type": "application/json"}
    params = {"key": GOOGLE_API_KEY}
    prompt_full = f"{prompt}. No people, no faces, no hands, no watermark or text."

    # Candidate payloads/endpoints
    payloads = [
        # 1) Newer Images API style
        (f"https://generativelanguage.googleapis.com/v1beta/images:generate", {
            "model": GEMINI_IMAGE_MODEL or "imagen-3.0",
            "prompt": {"text": prompt_full},
            "imageGenerationConfig": {"numberOfImages": 1, "width": desired_w, "height": desired_h}
        }),
        # 2) models/*:generateImages style
        (f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_IMAGE_MODEL or 'imagen-3.0'}:generateImages", {
            "prompt": {"text": prompt_full},
            "imageGenerationConfig": {"numberOfImages": 1, "width": desired_w, "height": desired_h}
        }),
    ]

    last_err = None
    for url, body in payloads:
        try:
            r = requests.post(url, params=params, json=body, timeout=120)
            if r.status_code != 200:
                last_err = RuntimeError(f"Gemini status {r.status_code}: {r.text[:300]}")
                continue
            data = r.json() or {}
            # Response variants: {"images":[{"base64Data":"..."}]} or {"candidates":[{"image":{"base64Data":"..."}}]}
            b64 = None
            if isinstance(data.get("images"), list) and data["images"]:
                b64 = data["images"][0].get("base64Data")
            if not b64 and isinstance(data.get("candidates"), list) and data["candidates"]:
                img_obj = data["candidates"][0].get("image") or {}
                b64 = img_obj.get("base64Data")
            if not b64:
                last_err = RuntimeError("Gemini response without base64 image")
                continue
            return _b64_to_bytes(b64)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Gemini generation failed: {last_err}")


# ==== Public API ===========================================================

def is_ai_image_available() -> bool:
    """Return True if at least one backend is configured and reachable."""
    # Prefer explicit backend if provided
    if PREFERRED_AI_BACKEND == "GEMINI" and _gemini_available():
        return True
    if PREFERRED_AI_BACKEND == "A1111" and _a1111_available():
        return True
    if PREFERRED_AI_BACKEND == "STABILITY" and _stability_available():
        return True
    if PREFERRED_AI_BACKEND == "OPENAI" and _openai_available():
        return True

    # Auto-detect order (Gemini first if available)
    if _gemini_available():
        return True
    if _a1111_available():
        return True
    if _stability_available():
        return True
    if _openai_available():
        return True
    return False


def generate_thematic_image(prompt: str, negative_prompt: str = "", width: int = 1280,
                            height: int = 720, model: str = "sdxl") -> Dict[str, Any]:
    last_err = None

    # Respect preferred backend via env
    order = []
    if PREFERRED_AI_BACKEND in {"GEMINI","A1111","STABILITY","OPENAI"}:
        order = [PREFERRED_AI_BACKEND]
    # Append the rest in a sensible order
    for b in ["GEMINI","A1111","STABILITY","OPENAI"]:
        if b not in order:
            order.append(b)

    for backend in order:
        try:
            if backend == "GEMINI" and _gemini_available():
                img_bytes = _gemini_generate(prompt, negative_prompt, width, height, model)
                return {"image_bytes": img_bytes}
            if backend == "A1111" and _a1111_available():
                img_bytes = _a1111_generate(prompt, negative_prompt, width, height, model)
                return {"image_bytes": img_bytes}
            if backend == "STABILITY" and _stability_available():
                img_bytes = _stability_generate(prompt, negative_prompt, width, height, model)
                return {"image_bytes": img_bytes}
            if backend == "OPENAI" and _openai_available():
                img_bytes = _openai_generate(prompt, negative_prompt, width, height, model="gpt-image-1")
                return {"image_bytes": img_bytes}
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"No AI backend available or all backends failed: {last_err}")
