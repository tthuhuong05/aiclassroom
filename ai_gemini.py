"""
Minimal local fallback for ai_gemini used in this repository.

This provides small, deterministic implementations of the functions the
project imports so the application can run without the external
`ai_gemini` package. The implementations are intentionally simple and
safe: they avoid external API calls and return reasonable defaults.
"""
import os
import re
import random
from typing import List, Optional, Dict, Any


def _ensure() -> bool:
    """Return True if a real Gemini/Generative AI integration should be used.

    By default this returns False. You can enable real Gemini behavior by
    setting the environment variable ENABLE_GEMINI=1 and installing the
    real dependency.
    """
    return os.environ.get("ENABLE_GEMINI", "0") in ("1", "true", "True")


def _normalize_words(text: str) -> List[str]:
    words = re.findall(r"\b[\wÀ-ỹ]{3,}\b", (text or ""), flags=re.UNICODE)
    words = [w.strip().strip('.,;:\"\'()[]') for w in words]
    words = [w for w in words if w]
    return words


def mcq_from_snippet(text: str) -> Optional[Dict[str, Any]]:
    """Produce a simple MCQ dict from a text snippet as a local fallback.

    Returns a dict with keys: question, options (list of 4), correct_index.
    Returns None when input is too short.
    """
    if not text or len(text.strip()) < 20:
        return None
    words = _normalize_words(text)
    if not words:
        return None
    # pick an answer word
    answer = random.choice(words)
    # build distractors from other words (or simple fillers)
    pool = [w for w in words if w.lower() != answer.lower()]
    distractors = random.sample(pool, k=min(3, len(pool))) if pool else []
    while len(distractors) < 3:
        distractors.append(random.choice(["không", "biết", "được", "n/a"]))
    options = [answer] + distractors[:3]
    random.shuffle(options)
    correct_index = options.index(answer)
    question = f"Trong đoạn sau, từ nào phù hợp để điền vào chỗ trống?\n\n{(text[:200] + '...') if len(text) > 200 else text}"
    return {"question": question, "options": options, "correct_index": correct_index}


def keywords_from_snippet(text: str, k: int = 5) -> List[str]:
    words = _normalize_words(text)
    # frequency-based selection
    freq = {}
    for w in words:
        key = w.lower()
        freq[key] = freq.get(key, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in sorted_words][:k]


def grade_free_text(answer: str, rubric: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Very small grader based on keyword overlap.

    rubric can be a dict like {"keywords": [...], "threshold": int}
    Returns: {"score": 0-1 float, "raw": int, "max": int}
    """
    ans_words = set(w.lower() for w in _normalize_words(answer))
    keywords = []
    thresh = None
    if isinstance(rubric, dict):
        keywords = [k.lower() for k in (rubric.get("keywords") or [])]
        thresh = rubric.get("threshold")
    if not keywords:
        # fallback: pick top 5 words from answer
        keywords = list(ans_words)[:5]
    matched = sum(1 for kw in keywords if kw and kw in ans_words)
    maxk = max(1, len(keywords))
    score = matched / maxk
    passed = True if (thresh is None or matched >= thresh) else False
    return {"score": score, "matched": matched, "max": maxk, "passed": passed}


def extract_main_content_from_document(raw: str) -> Dict[str, Any]:
    """Extract a minimal content structure from a raw document/text.

    This is a safe fallback used by doc-to-video helpers: it returns a
    dict containing a cleaned plaintext version and rudimentary sections.
    """
    if not raw:
        return {"title": "", "plain_text": "", "sections": []}

    # strip simple HTML tags
    text = re.sub(r"<[^>]+>", "\n", raw)
    # normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # split into pseudo-sections by looking for double newlines or headings
    chunks = [c.strip() for c in re.split(r"\n\s*\n|\r\n\s*\r\n", raw) if c.strip()]
    sections = []
    for c in chunks[:10]:
        # take first line as heading if short
        heading = None
        lines = [l.strip() for l in c.splitlines() if l.strip()]
        if lines and len(lines[0]) < 120:
            heading = lines[0]
        sections.append({"heading": heading, "text": re.sub(r"\s+", " ", c).strip()})
    title = sections[0]["heading"] if sections else (text[:60] + "...")
    return {"title": title, "plain_text": text, "sections": sections}


if __name__ == "__main__":
    print("ai_gemini fallback module loaded. _ensure()=", _ensure())
