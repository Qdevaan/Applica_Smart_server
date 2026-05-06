"""Job listing + matching endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from api.config import Settings, get_settings
from api.deps import get_ollama_or_none
from api.schemas import JobMatch, MatchRequest, MatchResponse, SkillGap
from services import matcher
from services.ollama_client import OllamaClient

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


def _resolve_jobs_path(settings: Settings) -> Path:
    p = Path(settings.jobs_path)
    if not p.is_absolute():
        # relative to repo root
        p = Path(__file__).resolve().parents[2] / settings.jobs_path
    return p


@router.get("", response_model=list[dict])
def list_jobs(settings: Settings = Depends(get_settings)) -> list[dict]:
    path = _resolve_jobs_path(settings)
    try:
        return matcher.load_jobs(path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"jobs.json not found at {path}. Run the scraper: cd job_scraper && node main_scraper.js",
        )


@router.post("/match", response_model=MatchResponse)
async def match(
    body: MatchRequest,
    settings: Settings = Depends(get_settings),
    ollama: Optional[OllamaClient] = Depends(get_ollama_or_none),
) -> MatchResponse:
    path = _resolve_jobs_path(settings)
    try:
        jobs = matcher.load_jobs(path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"jobs.json not found at {path}. Run the scraper first.",
        )

    matches, total = await matcher.match_resume_to_jobs(
        resume_text=body.resume_text,
        jobs=jobs,
        top_k=body.top_k,
        generate_letters_for_top=body.generate_letters_for_top,
        ollama=ollama,
    )

    return MatchResponse(
        matches=[
            JobMatch(
                title=m["title"],
                company=m["company"],
                description=m["description"],
                url=m.get("url"),
                similarity=m["similarity"],
                recommendation=m["recommendation"],
                skill_gap=SkillGap(**m["skill_gap"]),
                cover_letter=m["cover_letter"],
                cover_letter_source=m["cover_letter_source"],
            )
            for m in matches
        ],
        total_jobs_considered=total,
    )
