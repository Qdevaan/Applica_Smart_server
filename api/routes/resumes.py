"""Resume parsing + analysis endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.deps import get_ollama_or_none
from api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ParseResumeRequest,
    ParseResumeResponse,
    SkillGap,
)
from services import analyzer, resume_parser
from services.extractors import extract_company, extract_job_title, extract_name_from_resume
from services.ollama_client import OllamaClient
from services.skill_taxonomy import extract_skills, gap

router = APIRouter(prefix="/v1/resumes", tags=["resumes"])

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_TEXT_LEN = 200_000


@router.post("/parse", response_model=ParseResumeResponse)
async def parse_text(
    body: ParseResumeRequest,
    ollama: Optional[OllamaClient] = Depends(get_ollama_or_none),
) -> ParseResumeResponse:
    """Parse resume text into a JSON Resume v1.0.0 structure."""
    resume, parser = await resume_parser.parse_resume(body.text, ollama)
    return ParseResumeResponse(resume=resume, raw_text=body.text, parser=parser)


@router.post("/parse-file", response_model=ParseResumeResponse)
async def parse_file(
    file: UploadFile = File(...),
    ollama: Optional[OllamaClient] = Depends(get_ollama_or_none),
) -> ParseResumeResponse:
    """Upload a PDF and receive structured JSON Resume."""
    raw = await file.read()
    if len(raw) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_PDF_BYTES // (1024*1024)}MB limit.")
    if not raw:
        raise HTTPException(status_code=400, detail="Empty upload.")

    text = _extract_pdf_text(raw, filename=file.filename or "upload.pdf")
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN]

    resume, parser = await resume_parser.parse_resume(text, ollama)
    return ParseResumeResponse(resume=resume, raw_text=text, parser=parser)


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest) -> AnalyzeResponse:
    """Analyze resume vs JD: similarity, skills, gap, recommendation."""
    sim = analyzer.similarity(body.resume_text, body.job_description)
    resume_skills = extract_skills(body.resume_text)
    jd_skills = extract_skills(body.job_description)
    matched, missing, extra = gap(resume_skills, jd_skills)

    return AnalyzeResponse(
        job_title=body.job_title or extract_job_title(body.job_description),
        company=body.company or extract_company(body.job_description),
        applicant_name=extract_name_from_resume(body.resume_text),
        similarity=sim,
        recommendation=analyzer.recommendation(sim, len(missing)),
        resume_skills=resume_skills,
        jd_skills=jd_skills,
        skill_gap=SkillGap(matched=matched, missing=missing, extra=extra),
    )


def _extract_pdf_text(data: bytes, filename: str) -> str:
    """Lazily import pdfplumber and extract text from in-memory bytes."""
    import io
    import pdfplumber

    out: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t:
                    out.append(t)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read PDF '{filename}': {e}") from e
    return "\n".join(out)
