"""Pydantic v2 schemas. Resume schema follows JSON Resume spec (jsonresume.org/schema)."""

from __future__ import annotations

from typing import Annotated, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


# ---------- JSON Resume schema ----------

class Location(BaseModel):
    address: Optional[str] = None
    postalCode: Optional[str] = None
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None


class Profile(BaseModel):
    network: Optional[str] = None
    username: Optional[str] = None
    url: Optional[str] = None


class Basics(BaseModel):
    name: Optional[str] = None
    label: Optional[str] = None
    image: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: list[Profile] = Field(default_factory=list)


class Work(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class Volunteer(BaseModel):
    organization: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)


class Education(BaseModel):
    institution: Optional[str] = None
    url: Optional[str] = None
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: list[str] = Field(default_factory=list)


class Award(BaseModel):
    title: Optional[str] = None
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class Certificate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None


class Publication(BaseModel):
    name: Optional[str] = None
    publisher: Optional[str] = None
    releaseDate: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None


class Skill(BaseModel):
    name: str
    level: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)


class Language(BaseModel):
    language: Optional[str] = None
    fluency: Optional[str] = None


class Interest(BaseModel):
    name: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)


class Reference(BaseModel):
    name: Optional[str] = None
    reference: Optional[str] = None


class Project(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    highlights: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    url: Optional[str] = None
    roles: list[str] = Field(default_factory=list)
    entity: Optional[str] = None
    type: Optional[str] = None


class Meta(BaseModel):
    canonical: Optional[str] = None
    version: Optional[str] = None
    lastModified: Optional[str] = None


class Resume(BaseModel):
    """JSON Resume v1.0.0 compatible structure."""
    model_config = ConfigDict(extra="ignore")

    basics: Basics = Field(default_factory=Basics)
    work: list[Work] = Field(default_factory=list)
    volunteer: list[Volunteer] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    awards: list[Award] = Field(default_factory=list)
    certificates: list[Certificate] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    interests: list[Interest] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    meta: Meta = Field(default_factory=Meta)


# ---------- Resume parsing ----------

class ParseResumeRequest(BaseModel):
    """Used when the client sends raw text instead of uploading a PDF."""
    text: Annotated[str, Field(min_length=1, max_length=200_000)]


class ParseResumeResponse(BaseModel):
    resume: Resume
    raw_text: str
    parser: Literal["llm", "heuristic"] = "llm"


# ---------- Analyze (resume vs JD) ----------

class AnalyzeRequest(BaseModel):
    resume_text: Annotated[str, Field(min_length=1, max_length=200_000)]
    job_description: Annotated[str, Field(min_length=1, max_length=200_000)]
    job_title: Optional[str] = None
    company: Optional[str] = None


class SkillGap(BaseModel):
    matched: list[str]
    missing: list[str]
    extra: list[str]


class AnalyzeResponse(BaseModel):
    job_title: str
    company: str
    applicant_name: str
    similarity: float
    recommendation: Literal[
        "STRONG MATCH – Recommended to Apply",
        "MODERATE MATCH – You Can Apply",
        "WEAK MATCH – Not Recommended",
    ]
    resume_skills: list[str]
    jd_skills: list[str]
    skill_gap: SkillGap


# ---------- Cover letter ----------

CoverLetterTone = Literal["professional", "enthusiastic", "concise", "narrative"]


class CoverLetterRequest(BaseModel):
    resume_text: Annotated[str, Field(min_length=1, max_length=200_000)]
    job_description: Annotated[str, Field(min_length=1, max_length=200_000)]
    job_title: Optional[str] = None
    company: Optional[str] = None
    applicant_name: Optional[str] = None
    tone: CoverLetterTone = "professional"
    word_target: Annotated[int, Field(ge=80, le=600)] = 220


class CoverLetterResponse(BaseModel):
    cover_letter: str
    source: Literal["llm", "template"]
    job_title: str
    company: str
    applicant_name: str


# ---------- Job match ----------

class MatchRequest(BaseModel):
    resume_text: Annotated[str, Field(min_length=1, max_length=200_000)]
    top_k: Annotated[int, Field(ge=1, le=50)] = 5
    generate_letters_for_top: Annotated[int, Field(ge=0, le=10)] = 3


class JobMatch(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    similarity: float
    recommendation: str
    skill_gap: SkillGap
    cover_letter: Optional[str] = None
    cover_letter_source: Optional[Literal["llm", "template"]] = None


class MatchResponse(BaseModel):
    matches: list[JobMatch]
    total_jobs_considered: int


# ---------- Health ----------

class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    components: dict[str, str]


class VersionResponse(BaseModel):
    name: str
    version: str
    api: str
