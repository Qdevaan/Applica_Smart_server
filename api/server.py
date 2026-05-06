"""FastAPI application entry point.

Run locally:
    uvicorn api.server:app --reload --host 0.0.0.0 --port 8000

Run via env:
    HOST=0.0.0.0 PORT=8000 python -m api.server
"""

from __future__ import annotations

import logging
import os
import sys

# Allow `from api.*` and `from services.*` imports when launched from anywhere.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import get_settings
from api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from api.middleware import RequestIDMiddleware
from api.routes import cover_letters, health, jobs, resumes


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = FastAPI(
        title="Applica-Smart ML Server",
        version="1.0.0",
        description="Resume parsing, JD analysis, cover letter generation, job matching.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(resumes.router)
    app.include_router(cover_letters.router)
    app.include_router(jobs.router)

    _attach_legacy_aliases(app)
    return app


def _attach_legacy_aliases(app: FastAPI) -> None:
    """Keep old `/api/pipeline/*` and `/api/jobs` routes alive during frontend migration."""
    from fastapi import Depends

    from api.deps import get_ollama_or_none
    from api.routes.jobs import list_jobs as list_jobs_route
    from api.routes.jobs import match as match_route
    from api.routes.resumes import analyze as analyze_route

    @app.get("/health", include_in_schema=False)
    def _legacy_health():
        return {"status": "ok"}

    @app.post("/api/pipeline/analyze", include_in_schema=False)
    async def _legacy_analyze(body: dict):
        from api.schemas import AnalyzeRequest

        req = AnalyzeRequest(
            resume_text=body.get("resume_text", ""),
            job_description=body.get("job_description", ""),
            job_title=body.get("job_title"),
            company=body.get("company"),
        )
        result = await analyze_route(req)
        return {
            "resume_skills": result.resume_skills,
            "jd_skills": result.jd_skills,
            "missing_skills": result.skill_gap.missing,
            "similarity": result.similarity,
            "cover_letter": "",
            "recommendation": result.recommendation,
            "applicant_name": result.applicant_name,
            "job_title": result.job_title,
            "company": result.company,
        }

    @app.post("/api/pipeline/analyze-batch", include_in_schema=False)
    async def _legacy_analyze_batch(body: dict, ollama=Depends(get_ollama_or_none)):
        from api.schemas import MatchRequest

        req = MatchRequest(resume_text=body.get("resume_text", ""))
        result = await match_route(req, ollama=ollama)  # type: ignore[call-arg]
        return [
            {
                "title": m.title,
                "company": m.company,
                "similarity": m.similarity,
                "recommendation": m.recommendation,
                "cover_letter": m.cover_letter or "Not generated (only top 3)",
                "cover_letter_file": None,
            }
            for m in result.matches
        ]

    @app.get("/api/jobs", include_in_schema=False)
    def _legacy_jobs():
        return list_jobs_route()


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level,
    )
