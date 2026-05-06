"""Skill normalization. Lightweight curated taxonomy + alias map.

Industry-standard alternatives (ESCO, O*NET) require a downloaded dataset; this
file maintains an in-process subset covering the high-frequency tech skills.
Extending it is mechanical: add to ALIASES.
"""

from __future__ import annotations

import re
from typing import Iterable


# Canonical skills. Lowercase. Multi-word skills MUST appear before their
# single-word substrings to win the longest-match.
CANONICAL: list[str] = [
    # languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "kotlin", "swift", "scala", "r", "matlab",
    # frontend
    "react", "next.js", "vue.js", "angular", "svelte", "tailwind css", "redux",
    "html", "css", "sass",
    # backend
    "node.js", "express", "fastapi", "django", "flask", "spring boot", "rails",
    "laravel", "asp.net", "graphql", "rest api", "grpc", "websocket",
    # data
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "snowflake", "bigquery", "kafka", "rabbitmq",
    # ml / data sci
    "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow", "keras",
    "huggingface transformers", "spacy", "nltk", "opencv", "computer vision",
    "natural language processing", "deep learning", "machine learning",
    "reinforcement learning",
    # cloud / devops
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "github actions", "gitlab ci", "jenkins", "ci/cd",
    # other
    "git", "linux", "agile", "scrum", "rest", "microservices", "serverless",
]


# Aliases: { alias_lower: canonical_lower }
ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "node": "node.js",
    "nodejs": "node.js",
    "next": "next.js",
    "nextjs": "next.js",
    "vue": "vue.js",
    "vuejs": "vue.js",
    "py": "python",
    "tf": "tensorflow",
    "torch": "pytorch",
    "huggingface": "huggingface transformers",
    "hf": "huggingface transformers",
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "tailwind": "tailwind css",
    "tailwindcss": "tailwind css",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "rl": "reinforcement learning",
    "psql": "postgresql",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "es": "elasticsearch",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "rest api": "rest api",
    "ci cd": "ci/cd",
    "ci-cd": "ci/cd",
    "gh actions": "github actions",
}


# Pre-build a sorted list (longest first) for greedy matching.
_TAXONOMY = sorted(set(CANONICAL) | set(ALIASES.keys()), key=len, reverse=True)


def normalize(name: str) -> str:
    """Map an alias / variant to its canonical form. Returns the input lowercased if unknown."""
    n = name.strip().lower()
    return ALIASES.get(n, n)


def extract_skills(text: str) -> list[str]:
    """Return canonical skill list found in `text`, in order of first appearance, deduped."""
    if not text:
        return []
    lower = text.lower()
    found: list[str] = []
    seen: set[str] = set()
    # Use a regex with word boundaries when possible. Skills with punctuation
    # (c++, c#, .net) need careful escaping.
    for term in _TAXONOMY:
        # boundary trick: surround alpha-only terms with \b; otherwise use literal
        if term.replace(" ", "").isalpha():
            pattern = r"\b" + re.escape(term) + r"\b"
        else:
            pattern = re.escape(term)
        if re.search(pattern, lower):
            canonical = ALIASES.get(term, term)
            if canonical not in seen:
                seen.add(canonical)
                found.append(canonical)
    return found


def gap(resume_skills: Iterable[str], jd_skills: Iterable[str]) -> tuple[list[str], list[str], list[str]]:
    """Return (matched, missing, extra)."""
    r = {normalize(s) for s in resume_skills}
    j = {normalize(s) for s in jd_skills}
    matched = sorted(r & j)
    missing = sorted(j - r)
    extra = sorted(r - j)
    return matched, missing, extra
