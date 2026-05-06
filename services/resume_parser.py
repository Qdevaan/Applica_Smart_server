"""Resume parser: PDF/text → JSON Resume v1.0.0 schema.

Strategy:
1. Try LLM (Ollama JSON mode) with a strict schema-shaped prompt.
2. On failure (Ollama unreachable, malformed JSON, validation error), fall back
   to a deterministic heuristic extractor that fills the basics + a single
   work entry from the raw text. The heuristic is intentionally minimal — it
   guarantees the API never fails.
"""

from __future__ import annotations

import logging
from typing import Optional

from pydantic import ValidationError

from api.schemas import Basics, Resume, Skill, Work
from services.extractors import extract_name_from_resume
from services.ollama_client import OllamaClient, OllamaError
from services.skill_taxonomy import extract_skills

log = logging.getLogger("applica.resume_parser")


_SYSTEM_PROMPT = (
    "You are a resume parser. Extract structured data from the provided resume text "
    "and respond with a single valid JSON Resume v1.0.0 object — no commentary, no "
    "markdown fences. Do not invent information. Leave fields empty when unsure."
)


def _build_user_prompt(text: str) -> str:
    return f"""Extract a JSON Resume v1.0.0 object from the resume below.

Required top-level keys: basics, work, education, skills, projects, awards,
certificates, languages, interests. Use exactly these key names. Each list may
be empty.

basics shape: {{name, label, email, phone, url, summary, location: {{city, region, countryCode}}, profiles: [{{network, username, url}}]}}
work[] shape: {{name, position, startDate, endDate, summary, highlights: []}}
education[] shape: {{institution, area, studyType, startDate, endDate, score}}
skills[] shape: {{name, level, keywords: []}}
projects[] shape: {{name, description, highlights: [], keywords: []}}

Dates: ISO 8601 (YYYY-MM or YYYY-MM-DD) when known, otherwise empty string.

Resume:
\"\"\"
{text}
\"\"\"

Respond with the JSON object only.
"""


async def parse_with_llm(text: str, ollama: OllamaClient) -> Resume:
    payload = await ollama.generate_json(
        _build_user_prompt(text),
        system=_SYSTEM_PROMPT,
        temperature=0.1,
        num_predict=2000,
    )
    return Resume.model_validate(payload)


def parse_heuristic(text: str) -> Resume:
    """Deterministic minimal parser. Always returns a Resume (never raises)."""
    name = extract_name_from_resume(text)
    skills = [Skill(name=s) for s in extract_skills(text)]

    summary = ""
    for line in text.split("\n"):
        s = line.strip()
        if len(s) > 60:
            summary = s
            break

    return Resume(
        basics=Basics(name=name, summary=summary[:500] if summary else None),
        skills=skills,
        work=[Work(summary=summary)] if summary else [],
    )


async def parse_resume(text: str, ollama: Optional[OllamaClient]) -> tuple[Resume, str]:
    """Returns (resume, parser) where parser ∈ {'llm', 'heuristic'}."""
    if ollama is not None:
        try:
            resume = await parse_with_llm(text, ollama)
            return resume, "llm"
        except (OllamaError, ValidationError) as e:
            log.warning("LLM parse failed, falling back to heuristic: %s", e)
    return parse_heuristic(text), "heuristic"
