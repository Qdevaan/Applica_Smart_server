from pydantic import BaseModel
from typing import Optional


class AnalyzeRequest(BaseModel):
    resume_text: str
    job_description: str
    job_title: Optional[str] = None
    company: Optional[str] = None


class AnalyzeResponse(BaseModel):
    resume_skills: list[str]
    jd_skills: list[str]
    missing_skills: list[str]
    similarity: float
    cover_letter: str
    cover_letter_source: str = "llm"
    recommendation: str
    applicant_name: str
    job_title: str
    company: str


class BatchAnalyzeRequest(BaseModel):
    resume_text: str


class JobResult(BaseModel):
    title: Optional[str]
    company: Optional[str]
    similarity: float
    recommendation: str
    cover_letter: str
    cover_letter_file: Optional[str]
