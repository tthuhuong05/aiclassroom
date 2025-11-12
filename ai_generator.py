"""
Lightweight local fallback for ai_generator used by assignment_controller.

Provides generate_questions_from_text(text, n=5) which returns a JSON
string with a list of question objects. This is intentionally simple and
meant to allow the app to run without an external AI generator.
"""
import json
import random
import re
from typing import List


def _sentences_from_text(text: str) -> List[str]:
    if not text:
        return []
    # Split into sentences using simple punctuation heuristics
    s = re.split(r'(?<=[\.\?!])\s+', text.strip())
    s = [x.strip() for x in s if len(x.strip()) > 20]
    return s


def _words_from_text(text: str) -> List[str]:
    words = re.findall(r"\b[\wÀ-ỹ]{3,}\b", text, flags=re.UNICODE)
    # Filter short words and numeric tokens
    words = [w for w in words if not w.isdigit() and len(w) >= 3]
    return words


def generate_questions_from_text(text: str, n: int = 5) -> str:
    """Generate a small list of MCQs from input text and return as JSON string.

    Each question has fields: level, question, options (dict A-D), answer (letter).
    """
    out = []
    if not text or not text.strip():
        return json.dumps(out)

    sents = _sentences_from_text(text)
    words = _words_from_text(text)
    rnd = random.SystemRandom()

    # If no good sentences, fallback to splitting by paragraphs
    if not sents:
        sents = [p.strip() for p in text.split('\n') if len(p.strip()) > 40]

    for i in range(min(n, max(1, len(sents)) )):
        sent = sents[i % len(sents)]
        # pick an answer word from sentence or from overall words
        cand_words = _words_from_text(sent) or words
        if cand_words:
            answer = rnd.choice(cand_words)
        else:
            answer = "đáp án"

        # build options
        pool = [w for w in (words or []) if w.lower() != answer.lower()]
        distractors = rnd.sample(pool, k=min(3, len(pool))) if pool else []
        while len(distractors) < 3:
            distractors.append(rnd.choice(["không", "biết", "được", "n/a"]))

        options_list = [answer] + distractors[:3]
        rnd.shuffle(options_list)
        # map to A-D
        opts = {k: v for k, v in zip(["A", "B", "C", "D"], options_list)}
        correct_letter = next(k for k, v in opts.items() if v == answer)

        q = {
            "level": "beginner",
            "question": f"Theo đoạn sau, chọn đáp án đúng: \"{sent[:200]}{'...' if len(sent)>200 else ''}\"",
            "options": opts,
            "answer": correct_letter
        }
        out.append(q)

    return json.dumps(out, ensure_ascii=False)


if __name__ == "__main__":
    sample = "Python là một ngôn ngữ lập trình thông dụng. Nó hỗ trợ nhiều thư viện hữu ích cho xử lý dữ liệu và phát triển web."
    print(generate_questions_from_text(sample, n=3))
