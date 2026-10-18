"""
Virality scoring for candidate clip moments (v1: heuristic, no API key needed).

Takes whisper word/segment transcript and finds self-contained moments likely
to perform as standalone short-form clips. Each candidate gets a 0-100 score
from hook strength, emotional charge, clarity and self-containment signals.
"""
import re

# Signals that open loops / grab attention in the first 3 seconds
HOOK_PATTERNS = [
    r"\b(stop|wait|listen|look)\b",
    r"\b(nobody talks? about|no one tells? you|secret|truth about)\b",
    r"\b(i made|i earned|i lost|i learned)\b",
    r"\b(here's why|this is why|the reason)\b",
    r"\b(never|always|everyone|no one)\b",
    r"\b(free|mistake|warning|scam|lie)\b",
    r"\?\s*$",  # ends on a question
]
HOOK_RES = [re.compile(p, re.I) for p in HOOK_PATTERNS]

QUESTION_RE = re.compile(r"\?")
NUMBER_RE = re.compile(r"\b(\d+[%$kmb]?|\$[\d,]+|first|second|third|top \d+)\b", re.I)
YOU_RE = re.compile(r"\b(you|your|you're)\b", re.I)
EMOTION_WORDS = {
    "crazy", "insane", "unbelievable", "shocking", "amazing", "secret",
    "free", "mistake", "warning", "brutal", "honest", "truth", "lie",
    "scam", "hack", "broke", "rich", "million", "viral", "guaranteed",
}
PAYOFF_RES = [re.compile(p, re.I) for p in [
    r"\b(so|and) that's (why|how)\b",
    r"\b(the result|turns out|in the end)\b",
    r"\bhere's what happened\b",
]]
FILLER_RE = re.compile(r"\b(um+|uh+|like,|you know,)\b", re.I)


def score_text(text):
    """Score a chunk of transcript text 0-100 for clip-worthiness."""
    t = text.strip()
    if not t:
        return 0
    words = t.split()
    n = len(words)
    if n < 12:  # too thin to stand alone
        return 0
    score = 40.0  # base: coherent speech is clip-able

    first_40 = " ".join(words[:40])
    hooks = sum(1 for rx in HOOK_RES if rx.search(first_40))
    score += min(hooks, 3) * 8

    if QUESTION_RE.search(first_40):
        score += 6
    nums = len(NUMBER_RE.findall(t))
    score += min(nums, 3) * 4
    yous = len(YOU_RE.findall(t))
    score += min(yous, 6) * 2

    emo = sum(1 for w in words if w.lower().strip(".,!?") in EMOTION_WORDS)
    score += min(emo, 5) * 3

    if any(rx.search(t) for rx in PAYOFF_RES):
        score += 8  # has a payoff, feels complete

    fillers = len(FILLER_RE.findall(t))
    score -= min(fillers, 8) * 1.5

    # sweet spot length for a standalone clip: 30-90 words (~20-60s of speech)
    if 30 <= n <= 90:
        score += 6
    elif n > 150:
        score -= 8

    return round(max(0, min(100, score)), 1)


def find_moments(segments, min_score=55, target_len_s=(20, 60)):
    """
    segments: list of {start, end, text} from whisper (word or segment level).
    Returns ranked list of {start, end, score, text, title}.
    Uses a sliding window over segments to build candidate clips.
    """
    # flatten to word list with times if word-level available
    words = []
    for s in segments:
        ws = s.get("words")
        if ws:
            words.extend(ws)
        else:
            # segment-level fallback: spread evenly
            txt_words = s["text"].split()
            dur = max(0.01, s["end"] - s["start"])
            per = dur / max(1, len(txt_words))
            for i, w in enumerate(txt_words):
                words.append({"word": w, "start": s["start"] + i * per,
                              "end": s["start"] + (i + 1) * per})
    if not words:
        return []

    total_dur = words[-1]["end"]
    candidates = []
    # window sizes in seconds
    for win in (25, 35, 50):
        step = win // 2
        t = 0.0
        while t + 15 < total_dur:
            chunk = [w for w in words if t <= w["start"] < t + win]
            if chunk:
                text = " ".join(w["word"] for w in chunk)
                sc = score_text(text)
                if sc >= min_score:
                    candidates.append({
                        "start": round(chunk[0]["start"], 2),
                        "end": round(chunk[-1]["end"], 2),
                        "score": sc,
                        "text": text,
                        "words": chunk,
                    })
            t += step

    # de-duplicate overlapping candidates, keep highest score
    candidates.sort(key=lambda c: -c["score"])
    picked = []
    for c in candidates:
        if all(c["end"] < p["start"] + 5 or c["start"] > p["end"] - 5
               for p in picked):
            c["title"] = make_title(c["text"])
            picked.append(c)
        if len(picked) >= 10:
            break
    return sorted(picked, key=lambda c: -c["score"])


def make_title(text):
    """Auto-generate a short hook title: pick the highest-scoring
    sentence in the clip, not just the first words (chunks often
    start mid-sentence)."""
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    if not sentences:
        return "Untitled clip"
    best = max(sentences, key=lambda s: (score_text(s), -abs(len(s.split()) - 12)))
    words = best.split()[:12]
    title = " ".join(words).strip(" ,")
    if len(title) > 70:
        title = title[:67].rsplit(" ", 1)[0] + "…"
    return title or "Untitled clip"


def make_hashtags(text, n=5):
    """Extract keyword hashtags from clip text."""
    stop = {"the", "a", "an", "and", "or", "but", "to", "of", "in", "on",
            "for", "with", "is", "are", "was", "were", "it", "this", "that",
            "you", "your", "i", "we", "they", "he", "she", "my", "our", "be",
            "have", "has", "had", "do", "does", "did", "so", "if", "just",
            "like", "get", "got", "make", "made", "going", "gonna", "really",
            "very", "much", "more", "most", "all", "can", "will", "would",
            "here", "there", "what", "when", "how", "why", "need", "step",
            "steps", "last", "next", "every", "thing", "things", "some",
            "them", "then", "than", "into", "over", "under", "again",
            "still", "also", "because", "from", "about", "yourself",
            "people", "peoples", "videos", "video", "clip", "clips"}
    freq = {}
    for w in re.findall(r"[a-zA-Z]{4,}", text.lower()):
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1
    top = sorted(freq, key=lambda w: -freq[w])[:n]
    return ["#" + w for w in top]
