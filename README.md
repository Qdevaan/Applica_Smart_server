# Applica-Smart ML Server

FastAPI backend for the Applica-Smart job-application platform.
Resume parsing, JD analysis, cover letter generation, job matching.

## Architecture

```
api/
  server.py        FastAPI app + middleware + legacy aliases
  config.py        Pydantic settings (env-driven)
  schemas.py       Pydantic v2 models (JSON Resume v1.0.0 spec)
  errors.py        RFC 7807 problem-details handlers
  middleware.py    Request-ID middleware
  deps.py          FastAPI DI (Ollama client)
  routes/
    health.py        /healthz, /readyz, /v1/version
    resumes.py       /v1/resumes/parse, /parse-file, /analyze
    cover_letters.py /v1/cover-letters/generate
    jobs.py          /v1/jobs, /v1/jobs/match
services/
  ollama_client.py    Async httpx wrapper with JSON mode
  resume_parser.py    PDF/text -> JSON Resume (LLM + heuristic fallback)
  cover_letter.py     LLM-first with deterministic template fallback
  matcher.py          Score + rank jobs, optional letters for top-N
  analyzer.py         Cosine similarity + recommendation
  extractors.py       Heuristic name/title/company extraction
  skill_taxonomy.py   Curated tech skill set + alias normalization
scripts/              Legacy CLI helpers (kept for offline use)
job_scraper/          Node.js scrapers that produce jobs.json
```

## Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"
copy .env.example .env
```

Install Ollama and pull a model:

```powershell
ollama pull mistral
```

## Run

```powershell
uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI docs at `http://localhost:8000/docs`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/healthz` | Liveness |
| GET | `/readyz` | Readiness — checks Ollama reachability |
| GET | `/v1/version` | Build info |
| POST | `/v1/resumes/parse` | Parse text -> JSON Resume |
| POST | `/v1/resumes/parse-file` | Upload PDF -> JSON Resume |
| POST | `/v1/resumes/analyze` | Resume vs JD: similarity, skills, gap |
| POST | `/v1/cover-letters/generate` | Generate cover letter (tone configurable) |
| GET | `/v1/jobs` | List scraped jobs |
| POST | `/v1/jobs/match` | Top-K matched jobs with letters |

Legacy `/api/pipeline/*` and `/api/jobs` remain for backward compatibility.

## Environment

See `.env.example`. Highlights:

- `OLLAMA_URL` / `OLLAMA_MODEL` / `OLLAMA_TIMEOUT`
- `CORS_ORIGINS` — comma-separated allow-list
- `CORS_ORIGIN_REGEX` — defaults to `^https://([a-z0-9-]+\.)*ngrok-free\.app$`
- `JOBS_PATH` — path to `jobs.json` (relative to repo root)

## Behaviour when Ollama is down

Every LLM-backed endpoint returns degraded but valid output:

- `/v1/resumes/parse*` returns a heuristic-extracted resume (`parser: "heuristic"`).
- `/v1/cover-letters/generate` returns a template letter (`source: "template"`).
- `/readyz` reports `degraded` so callers know.
