"""Job matching: score every JD against the resume, return top-K with optional letters."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from services import analyzer, cover_letter
from services.extractors import extract_company, extract_job_title, extract_name_from_resume
from services.ollama_client import OllamaClient
from services.skill_taxonomy import extract_skills, gap

log = logging.getLogger("applica.matcher")


def load_jobs(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Jobs file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


async def match_resume_to_jobs(
    *,
    resume_text: str,
    jobs: list[dict],
    top_k: int,
    generate_letters_for_top: int,
    ollama: Optional[OllamaClient],
) -> tuple[list[dict], int]:
    applicant_name = extract_name_from_resume(resume_text)
    resume_skills = extract_skills(resume_text)

    scored: list[dict] = []
    for job in jobs:
        jd = job.get("description") or ""
        if len(jd) < 50:
            continue
        sim = analyzer.similarity(resume_text, jd)
        scored.append({"job": job, "similarity": sim})

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top = scored[:top_k]

    out: list[dict] = []
    for idx, item in enumerate(top):
        job = item["job"]
        sim = item["similarity"]
        jd_text = job.get("description") or ""
        title = job.get("title") or extract_job_title(jd_text)
        company = job.get("company") or extract_company(jd_text)

        jd_skills = extract_skills(jd_text)
        matched, missing, extra = gap(resume_skills, jd_skills)

        record = {
            "title": title,
            "company": company,
            "description": jd_text,
            "url": job.get("url"),
            "similarity": sim,
            "recommendation": analyzer.recommendation(sim, len(missing)),
            "skill_gap": {"matched": matched, "missing": missing, "extra": extra},
            "cover_letter": None,
            "cover_letter_source": None,
        }

        if idx < generate_letters_for_top:
            text, source = await cover_letter.generate(
                ollama=ollama,
                resume_text=resume_text,
                jd_text=jd_text,
                matched_skills=matched,
                jd_skills=jd_skills,
                job_title=title,
                company=company,
                applicant_name=applicant_name,
            )
            record["cover_letter"] = text
            record["cover_letter_source"] = source

        out.append(record)

    return out, len(scored)
