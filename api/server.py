import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.models import AnalyzeRequest, AnalyzeResponse, BatchAnalyzeRequest, JobResult
from scripts.pipeline import process_application_text
from scripts.preprocess import preprocess_text
from scripts.semantic_similarity import get_semantic_similarity as get_similarity

app = FastAPI(title="Applica-Smart ML API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS_PATH = os.path.join(os.path.dirname(__file__), "..", "jobs.json")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/pipeline/analyze", response_model=AnalyzeResponse)
def analyze_single(req: AnalyzeRequest):
    """Analyze one resume text against one job description."""
    try:
        result = process_application_text(
            resume_text=req.resume_text,
            job_description_text=req.job_description,
            job_title=req.job_title,
            company=req.company,
        )
        return AnalyzeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/analyze-batch", response_model=list[JobResult])
def analyze_batch(req: BatchAnalyzeRequest):
    """Score resume against all jobs in jobs.json, return top 5 with cover letters."""
    if not os.path.exists(JOBS_PATH):
        raise HTTPException(
            status_code=404,
            detail="jobs.json not found — run the scraper first: cd FYP/job_scraper && node main_scraper.js"
        )
    with open(JOBS_PATH, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    cleaned_resume = preprocess_text(req.resume_text)

    scored = []
    for job in jobs:
        jd = job.get("description", "")
        if not jd or len(jd) < 50:
            continue
        cleaned_jd = preprocess_text(jd)
        try:
            score = float(get_similarity(cleaned_resume, cleaned_jd))
        except Exception:
            score = 0.0
        scored.append({"job": job, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:5]

    results = []
    for idx, item in enumerate(top):
        job = item["job"]
        output = process_application_text(
            resume_text=req.resume_text,
            job_description_text=job.get("description", ""),
            job_title=job.get("title"),
            company=job.get("company"),
        )
        cover_letter = output["cover_letter"] if idx < 3 else "Not generated (only top 3)"
        results.append(JobResult(
            title=job.get("title"),
            company=job.get("company"),
            similarity=output["similarity"],
            recommendation=output["recommendation"],
            cover_letter=cover_letter,
            cover_letter_file=None,
        ))

    return results


@app.get("/api/jobs", response_model=list[dict])
def get_jobs():
    """Return raw jobs from jobs.json."""
    if not os.path.exists(JOBS_PATH):
        raise HTTPException(status_code=404, detail="jobs.json not found")
    with open(JOBS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
