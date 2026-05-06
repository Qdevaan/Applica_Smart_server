"""Cover letter generation: LLM-first with deterministic template fallback."""

from __future__ import annotations

import logging
from typing import Optional

from services.ollama_client import OllamaClient, OllamaError

log = logging.getLogger("applica.cover_letter")


_TONE_HINTS = {
    "professional": "Use a polished, neutral, business tone. Achievement-led. No flourish.",
    "enthusiastic": "Use a warm, motivated tone — but specific and grounded in real evidence.",
    "concise": "Use short, punchy sentences. Skip filler and hedging.",
    "narrative": "Use a brief story arc: problem → action → result. Concrete examples.",
}


def _system_prompt(tone: str) -> str:
    return (
        "You are a senior career coach writing a cover letter. "
        + _TONE_HINTS.get(tone, _TONE_HINTS["professional"])
        + " STRICT RULES: do NOT start with 'I am passionate' or 'I am excited'. "
          "Do not use clichés. Mention real skills tied to actual usage. "
          "Include exactly one concrete example or project."
    )


def _user_prompt(
    *,
    resume_snippet: str,
    job_title: str,
    company: str,
    applicant_name: str,
    matched_skills: list[str],
    jd_skills: list[str],
    word_target: int,
) -> str:
    return f"""Write a cover letter following this structure:
1. Opening: role + company.
2. Experience that matches the job's requirements.
3. One concrete project or achievement.
4. Why this company specifically.
5. Professional closing.

Job Title: {job_title}
Company: {company}
Candidate Name: {applicant_name}
Candidate Top Skills: {', '.join(matched_skills[:8]) if matched_skills else 'general engineering skills'}
Job Top Requirements: {', '.join(jd_skills[:8]) if jd_skills else 'role responsibilities'}

Candidate background:
\"\"\"
{resume_snippet}
\"\"\"

Begin with: Dear Hiring Manager at {company}
End EXACTLY with:
Sincerely,
{applicant_name}

Target length: {word_target - 30}–{word_target + 30} words.
"""


async def generate_with_llm(
    *,
    ollama: OllamaClient,
    resume_snippet: str,
    job_title: str,
    company: str,
    applicant_name: str,
    matched_skills: list[str],
    jd_skills: list[str],
    tone: str,
    word_target: int,
) -> str:
    raw = await ollama.generate(
        _user_prompt(
            resume_snippet=resume_snippet,
            job_title=job_title,
            company=company,
            applicant_name=applicant_name,
            matched_skills=matched_skills,
            jd_skills=jd_skills,
            word_target=word_target,
        ),
        system=_system_prompt(tone),
        temperature=0.85,
        num_predict=int(word_target * 4),
    )
    return _enforce_envelope(raw, company=company, applicant_name=applicant_name)


def generate_with_template(
    *,
    resume_text: str,
    jd_text: str,
    matched_skills: list[str],
    jd_skills: list[str],
    job_title: str,
    company: str,
    applicant_name: str,
) -> str:
    matched_text = ", ".join(matched_skills[:5]) if matched_skills else "relevant skills"
    skills_text = ", ".join(jd_skills[:5]) if jd_skills else "relevant skills or technologies"
    first_sentence = jd_text.split(".")[0].strip() if jd_text else "your requirements"

    return (
        f"Dear Hiring Manager at {company},\n\n"
        f"I am writing to apply for the {job_title} role at {company}. The role calls for "
        f"experience with {skills_text}, which closely overlaps my background.\n\n"
        f"My work has involved {matched_text}, applied in production settings to ship "
        f"reliable software and resolve real customer needs.\n\n"
        f"Your description emphasises {first_sentence}. I would bring the same focus to "
        f"this role and look forward to contributing to your team.\n\n"
        f"Sincerely,\n{applicant_name}\n"
    )


def _enforce_envelope(text: str, *, company: str, applicant_name: str) -> str:
    out = text.strip()
    # Trim anything before the salutation if model rambled.
    if "Dear Hiring Manager" in out:
        out = "Dear Hiring Manager" + out.split("Dear Hiring Manager", 1)[1]
    # Force a clean closing.
    if "Sincerely" not in out:
        out = out.rstrip() + f"\n\nSincerely,\n{applicant_name}"
    return out


async def generate(
    *,
    ollama: Optional[OllamaClient],
    resume_text: str,
    jd_text: str,
    matched_skills: list[str],
    jd_skills: list[str],
    job_title: str,
    company: str,
    applicant_name: str,
    tone: str = "professional",
    word_target: int = 220,
) -> tuple[str, str]:
    """Returns (text, source) where source ∈ {'llm', 'template'}."""
    if ollama is not None:
        try:
            text = await generate_with_llm(
                ollama=ollama,
                resume_snippet=resume_text[:600],
                job_title=job_title,
                company=company,
                applicant_name=applicant_name,
                matched_skills=matched_skills,
                jd_skills=jd_skills,
                tone=tone,
                word_target=word_target,
            )
            return text, "llm"
        except OllamaError as e:
            log.warning("LLM cover letter failed, falling back to template: %s", e)
    return (
        generate_with_template(
            resume_text=resume_text,
            jd_text=jd_text,
            matched_skills=matched_skills,
            jd_skills=jd_skills,
            job_title=job_title,
            company=company,
            applicant_name=applicant_name,
        ),
        "template",
    )
