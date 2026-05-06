# scripts/pipeline.py
import requests
#from langchain_core.prompts import PromptTemplate
#from langchain_openai import ChatOpenAI
import os
import uuid
import json
from datetime import datetime


# import your helper modules (they must be in scripts/ or in PYTHONPATH)
from pdf_extractor import extract_text_from_pdf
from preprocess import preprocess_text
from skill_extractor import extract_skills
# use semantic similarity instead of TF-IDF
from semantic_similarity import get_semantic_similarity as get_similarity
# This Function will extract name from resume
def extract_name_from_resume(text):
    """
    Extracts the applicant's name from the resume.
    Strategy: Take the first non-empty line of the resume.
    """
    for line in text.split("\n"):
        line = line.strip()
        if line and len(line.split()) <= 4:  # names are usually short
            return line
    return "Applicant"
#this Function will extract the job title from job description
def extract_company(jd_text):
    """
    Extract company name from job description using simple patterns.
    """
    lines = jd_text.split("\n")

    for line in lines:
        line_low = line.lower()

        if "company:" in line_low:
            return line.split(":")[1].strip().title()

        if "join" in line_low:
            after = line_low.split("join")[1].strip()
            if len(after.split()) <= 4:
                return after.title()

        if "about" in line_low:
            after = line_low.split("about")[1].strip()
            if len(after.split()) <= 4:
                return after.title()

        if "at" in line_low and "we are" in line_low:
            # pattern: At Google we are hiring...
            comp = line_low.split("at")[1].split("we")[0].strip()
            if 1 <= len(comp.split()) <= 4:
                return comp.title()

    return "Your Company"

def extract_job_title(jd_text):
    """
    Extract job title from job description using simple keyword patterns.
    Example: 'We are hiring a Python Developer...' → Python Developer
    """
    jd_text = jd_text.lower()

    keywords = ["hiring", "looking for", "seeking", "we need", "we require"]

    for word in keywords:
        if word in jd_text:
            part = jd_text.split(word)[1].strip()
            title = part.split("with")[0].split("who")[0].split("and")[0]
            title = title.strip().title()
            if len(title.split()) <= 5:  # job titles usually short
                return title

    return "The Position"




# ---- Configuration ----
PROCESSED_DIR = os.path.join("data", "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ---- Simple template-based cover letter generator ----
def generate_cover_letter_pro(resume_text, jd_text, resume_skills, jd_skills, missing_skills, job_title, company, applicant_name):

    matched_skills = [s for s in jd_skills if s in resume_skills]
    matched_text = ", ".join(matched_skills[:5]) if matched_skills else "relevant skills"

    jd_lines = jd_text.split(".")
    key_line = jd_lines[0] if jd_lines else "your requirements"
    skills_text = ", ".join(jd_skills[:5]) if jd_skills else "relevant skills or technologies"

    letter = f"""Dear Hiring Manager at {company},

I am writing to apply for the {job_title} at {company}. Based on your job description, you are looking for candidates with expertise in {skills_text}.

My background includes experience with {matched_text}. I have worked on projects where I applied these skills in practical scenarios.

I noticed that your job emphasizes {key_line.strip()}. I believe my experience aligns well with these expectations.

I am excited about the opportunity and would love to contribute to your team.

Sincerely,
{applicant_name}
"""


    return letter


def generate_cover_letter_mistral(resume_skills, jd_skills, job_title, company, applicant_name,resume_snippet):

    prompt = f"""
Write a highly professional and natural cover letter.

STRICT RULES:
- Do NOT be generic
- Do NOT use phrases like "I am passionate" or "I am excited"
- Use a natural human tone
- Use achievement-based writing
- Mention real skills and how they were used
- Include one real example/project
- Avoid repetition

Job Title: {job_title}
Company: {company}

Candidate Skills: {', '.join(resume_skills[:5])}
Job Requirements: {', '.join(jd_skills[:5])}

Candidate Background:
{resume_snippet}

Structure:
1. Introduction (role + company)
2. Experience matching job
3. One real example
4. Why interested in company
5. Professional closing

Start with: Dear Hiring Manager at {company}

End EXACTLY with:
Sincerely,
{applicant_name}

Write 180–220 words only.
"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "mistral",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.9,
                "num_predict": 600
            }
        }
    )

    output = response.json()["response"]

    # STEP 3: FORCE ENDING
    if "Sincerely" not in output:
        output += f"\n\nSincerely,\n{applicant_name}"

    # STEP 4: FIX CUT-OFF TEXT
    output = output.strip()

    

    # CLEAN START
    if "Dear Hiring Manager" in output:
        output = output.split("Dear Hiring Manager")[-1]
        output = "Dear Hiring Manager" + output

    return output.strip()
# ---- Main pipeline function ----
def process_application(resume_pdf_path: str, job_description_text: str,job_title = None, company= None, save_outputs: bool = True):
    """
    Process a resume PDF and a pasted job description text.
    Returns a dictionary with:
      - cleaned_resume_text
      - cleaned_jd_text
      - resume_skills
      - jd_skills
      - missing_skills
      - similarity (float)
      - cover_letter (string)
      - saved_paths (optional)
    """
    # 1) Extract resume raw text
    raw_resume = extract_text_from_pdf(resume_pdf_path) or ""
    cleaned_resume = preprocess_text(raw_resume)
    resume_snippet = cleaned_resume[:500]

    # 2) Preprocess JD text
    cleaned_jd = preprocess_text(job_description_text or "")
    #calling extract job title function
    job_title = job_title if job_title and job_title.strip() != "" else extract_job_title(job_description_text)
    company = company if company and company.strip() != "" else extract_company(job_description_text)



    # 3) Extract skills (both)
    resume_skills = extract_skills(cleaned_resume)
    jd_skills = extract_skills(cleaned_jd)

    # normalize skills to lower-case strings for comparison
    resume_skills_norm = [s.lower() for s in resume_skills]
    jd_skills_norm = [s.lower() for s in jd_skills]

    # 4) Compute similarity
    try:
        similarity = float(get_similarity(cleaned_resume, cleaned_jd))
    except Exception:
        # fallback: similarity 0.0 if TF-IDF fails
        similarity = 0.0

    # 5) Missing skills (jd \ resume)
    missing_skills = [s for s in jd_skills_norm if s not in resume_skills_norm]
    # job recommendation based on similarity and missing skills
    recommendation = get_recommendation(similarity, missing_skills)
    #name extraction
    applicant_name = extract_name_from_resume(raw_resume)
    


    # 6) Generate cover letter
    cover_letter = generate_cover_letter_mistral(
    resume_skills_norm,
    jd_skills_norm,
    job_title,
    company,
    applicant_name,
    resume_snippet
)
  

    # 7) Save outputs (optional)
    saved_paths = {}

    if save_outputs:
        uid = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        resume_out = os.path.join(PROCESSED_DIR, f"resume_{uid}_{timestamp}.txt")
        jd_out = os.path.join(PROCESSED_DIR, f"jd_{uid}_{timestamp}.txt")
        letter_out = os.path.join(PROCESSED_DIR, f"cover_letter_{uid}_{timestamp}.txt")
        meta_out = os.path.join(PROCESSED_DIR, f"meta_{uid}_{timestamp}.json")

        with open(resume_out, "w", encoding="utf-8") as f:
            f.write(cleaned_resume)

        with open(jd_out, "w", encoding="utf-8") as f:
            f.write(cleaned_jd)

        with open(letter_out, "w", encoding="utf-8") as f:
            f.write(cover_letter)

        meta = {
            "uid": uid,
            "timestamp": timestamp,
            "resume_path": resume_pdf_path,
            "resume_saved": resume_out,
            "jd_saved": jd_out,
            "cover_letter_saved": letter_out,
            "similarity": similarity,
            "resume_skills": resume_skills_norm,
            "jd_skills": jd_skills_norm,
            "missing_skills": missing_skills
        }
        with open(meta_out, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        saved_paths = {
            "resume_text": resume_out,
            "jd_text": jd_out,
            "cover_letter": letter_out,
            "meta": meta_out
        }

    result = {
        "cleaned_resume": cleaned_resume,
        "cleaned_jd": cleaned_jd,
        "resume_skills": resume_skills_norm,
        "jd_skills": jd_skills_norm,
        "missing_skills": missing_skills,
        "similarity": similarity,
        "cover_letter": cover_letter,
        "saved_paths": saved_paths,
        "recommendation": recommendation,
        "applicant_name": applicant_name,
        "job_title": job_title,
        "company": company


    }

    return result


def process_application_text(resume_text: str, job_description_text: str,
                              job_title=None, company=None):
    """
    Same as process_application but accepts resume text directly.
    Used by the FastAPI server so the frontend can post profile text instead of uploading a PDF.
    """
    cleaned_resume = preprocess_text(resume_text or "")
    resume_snippet = cleaned_resume[:500]
    cleaned_jd = preprocess_text(job_description_text or "")

    job_title = job_title or extract_job_title(job_description_text)
    company = company or extract_company(job_description_text)

    resume_skills = extract_skills(cleaned_resume)
    jd_skills = extract_skills(cleaned_jd)
    resume_skills_norm = [s.lower() for s in resume_skills]
    jd_skills_norm = [s.lower() for s in jd_skills]

    try:
        similarity = float(get_similarity(cleaned_resume, cleaned_jd))
    except Exception:
        similarity = 0.0

    missing_skills = [s for s in jd_skills_norm if s not in resume_skills_norm]
    recommendation = get_recommendation(similarity, missing_skills)
    applicant_name = extract_name_from_resume(resume_text)

    cover_letter = generate_cover_letter_mistral(
        resume_skills_norm,
        jd_skills_norm,
        job_title,
        company,
        applicant_name,
        resume_snippet,
    )

    return {
        "resume_skills": resume_skills_norm,
        "jd_skills": jd_skills_norm,
        "missing_skills": missing_skills,
        "similarity": similarity,
        "cover_letter": cover_letter,
        "recommendation": recommendation,
        "applicant_name": applicant_name,
        "job_title": job_title,
        "company": company,
    }


# this is the function to generate recommendation based on similarity and missing skills
def get_recommendation(similarity: float, missing_skills: list):
    """
    Generate recommendation decision based on similarity score and missing skills.
    """
    # Strong match
    if similarity >= 0.70 and len(missing_skills) <= 2:
        return "STRONG MATCH – Recommended to Apply"

    # Medium match
    elif similarity >= 0.40:
        return "MODERATE MATCH – You Can Apply"

    # Weak match
    else:
        return "WEAK MATCH – Not Recommended"

def process_multiple_jobs(resume_pdf_path, jobs, top_k=5):

    results = []

    # -------- STEP 1: PROCESS RESUME ONCE --------
    raw_resume = extract_text_from_pdf(resume_pdf_path) or ""
    cleaned_resume = preprocess_text(raw_resume)

    print("Resume processed once ✅")

    # -------- STEP 2: FILTER + QUICK SIMILARITY --------
    scored_jobs = []

    for job in jobs:

        jd_text = job.get("description", "")

        # ❗ FILTERING (skip empty jobs)
        if not jd_text or len(jd_text) < 50:
            continue

        cleaned_jd = preprocess_text(jd_text)

        try:
            score = float(get_similarity(cleaned_resume, cleaned_jd))
        except:
            score = 0.0

        scored_jobs.append({
            "job": job,
            "score": score
        })

    print(f"Total valid jobs: {len(scored_jobs)}")

    # -------- STEP 3: RANKING --------
    scored_jobs = sorted(scored_jobs, key=lambda x: x["score"], reverse=True)

    # -------- STEP 4: SELECT TOP K --------
    top_jobs = scored_jobs[:top_k]

    print(f"Top {top_k} jobs selected ⭐")

    # -------- STEP 5: FULL PIPELINE --------
    for idx, item in enumerate(top_jobs):
        print(f"Generating cover letter {idx+1}/{len(top_jobs)}...")

        job = item["job"]

        output = process_application(
            resume_pdf_path,
            job["description"],
            job_title=job.get("title"),
            company=job.get("company"),
            save_outputs=False
        )

        result_item = {
            "title": job.get("title"),
            "company": job.get("company"),
            "similarity": output["similarity"],
            "recommendation": output["recommendation"],
        }

        if idx < 3:
            cover_letter = output["cover_letter"]
            safe_company = job.get("company", "company").replace(" ", "_")
            filename = f"cover_letter_{idx+1}_{safe_company}.txt"
            file_path = os.path.join(PROCESSED_DIR, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(cover_letter)
            result_item["cover_letter"] = cover_letter
            result_item["cover_letter_file"] = file_path
        else:
            result_item["cover_letter"] = "Not generated (only top 3)"
            result_item["cover_letter_file"] = None

        results.append(result_item)
    

    return results
if __name__ == "__main__":

    demo_resume = os.path.join("data", "raw", "resumes", "TAAHA-IJAZ-RESUME.pdf")

    import json

    with open("jobs.json", "r", encoding="utf-8") as f:
        jobs = json.load(f)

    results = process_multiple_jobs(demo_resume, jobs, top_k=5)

    # ✅ Save results
    with open("final_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("✅ Results saved to final_results.json")

    for r in results:
        print("\n-------------------------")
        print("Title:", r["title"])
        print("Company:", r["company"])
        print("Similarity:", r["similarity"])
        print("Recommendation:", r["recommendation"])