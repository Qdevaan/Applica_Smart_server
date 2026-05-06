import subprocess
import json
from pipeline import process_application

# your resume path
resume_path = "data/raw/resumes/TAAHA-IJAZ-RESUME.pdf"

print("Fetching jobs using Puppeteer...\n")

# STEP 1: Run Node scraper
result = subprocess.run(
    ["node", "job_scraper/scraper.js"],
    capture_output=True,
    text=True
)

# STEP 2: Convert JSON output to Python
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)

print(f"Total jobs fetched: {len(jobs)}\n")

results = []

print("Analyzing jobs using AI pipeline...\n")

# STEP 3: Run pipeline for each job
for job in jobs:

    output = process_application(
        resume_path,
        job["description"],
        save_outputs=False
    )

    results.append({
        "title": job["title"],
        "company": job["company"],
        "score": output["similarity"],
        "recommendation": output["recommendation"]
    })

# STEP 4: Sort jobs by similarity
results.sort(key=lambda x: x["score"], reverse=True)

# STEP 5: Display top matches
print("\n========== TOP MATCHING JOBS ==========\n")

for job in results[:10]:
    print(f"Job: {job['title']} - {job['company']}")
    print(f"Match Score: {round(job['score'] * 100, 2)}%")
    print(f"Recommendation: {job['recommendation']}")
    print("-------------------------------------")

# STEP 6: Save results to file
with open("data/job_matches.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nResults saved to data/job_matches.json")