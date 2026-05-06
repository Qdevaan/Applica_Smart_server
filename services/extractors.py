"""Heuristic extractors for resume name, JD job title, JD company.

Used as fallback when LLM is unavailable, and for fast field-level extraction.
"""

from __future__ import annotations

import re


_NAME_HINT_RE = re.compile(r"^(curriculum vitae|resume|cv)\b", re.I)


def extract_name_from_resume(text: str) -> str:
    """Take the first non-empty line of the resume that looks like a name (1-4 tokens, mostly alpha)."""
    if not text:
        return "Applicant"
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or _NAME_HINT_RE.match(line):
            continue
        words = line.split()
        if 1 <= len(words) <= 4 and all(w.replace(".", "").replace("-", "").isalpha() for w in words):
            return line
    return "Applicant"


def extract_job_title(jd_text: str) -> str:
    if not jd_text:
        return "The Position"
    text = jd_text.lower()
    for kw in ("hiring", "looking for", "seeking", "we need", "we require"):
        if kw in text:
            tail = text.split(kw, 1)[1].strip()
            tail = tail.split("with")[0].split("who")[0].split("and")[0]
            title = tail.strip(" \t.,:;").title()
            if 1 <= len(title.split()) <= 5 and title:
                return title
    return "The Position"


def extract_company(jd_text: str) -> str:
    if not jd_text:
        return "Your Company"
    for raw in jd_text.split("\n"):
        line = raw.strip()
        low = line.lower()
        if low.startswith("company:"):
            return line.split(":", 1)[1].strip().title() or "Your Company"
        if low.startswith("about "):
            tail = line.split(" ", 1)[1].strip()
            if 1 <= len(tail.split()) <= 4:
                return tail.title()
        if "join " in low and "team" not in low:
            tail = low.split("join", 1)[1].strip().split(" ", 4)
            tail = " ".join(tail[:3]).strip(" .,!:;")
            if tail:
                return tail.title()
    return "Your Company"
