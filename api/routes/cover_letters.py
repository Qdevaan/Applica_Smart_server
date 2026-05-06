"""Cover letter generation endpoint."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from api.deps import get_ollama_or_none
from api.schemas import CoverLetterRequest, CoverLetterResponse
from services import cover_letter
from services.extractors import extract_company, extract_job_title, extract_name_from_resume
from services.ollama_client import OllamaClient
from services.skill_taxonomy import extract_skills, gap

router = APIRouter(prefix="/v1/cover-letters", tags=["cover-letters"])


@router.post("/generate", response_model=CoverLetterResponse)
async def generate(
    body: CoverLetterRequest,
    ollama: Optional[OllamaClient] = Depends(get_ollama_or_none),
) -> CoverLetterResponse:
    job_title = body.job_title or extract_job_title(body.job_description)
    company = body.company or extract_company(body.job_description)
    applicant_name = body.applicant_name or extract_name_from_resume(body.resume_text)

    resume_skills = extract_skills(body.resume_text)
    jd_skills = extract_skills(body.job_description)
    matched, _missing, _extra = gap(resume_skills, jd_skills)

    text, source = await cover_letter.generate(
        ollama=ollama,
        resume_text=body.resume_text,
        jd_text=body.job_description,
        matched_skills=matched,
        jd_skills=jd_skills,
        job_title=job_title,
        company=company,
        applicant_name=applicant_name,
        tone=body.tone,
        word_target=body.word_target,
    )
    return CoverLetterResponse(
        cover_letter=text,
        source=source,
        job_title=job_title,
        company=company,
        applicant_name=applicant_name,
    )
