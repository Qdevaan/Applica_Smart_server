TECH_SKILLS = [
    "python", "java", "c++", "c#", "javascript", "typescript", "html", "css",
    "django", "flask", "fastapi", "react", "node", "nodejs", "express",
    "sql", "mysql", "postgresql", "mongodb",
    "nlp", "machine learning", "deep learning", "tensorflow",
    "pytorch", "pyspark", "aws", "azure", "gcp", "docker", "kubernetes",
    "rest api", "graphql", "git", "linux", "computer vision", "api", "ml",
    "scikit-learn", "pandas", "numpy", "redis", "elasticsearch",
]


def extract_skills(text: str) -> list[str]:
    """Extract tech skills from text via substring matching."""
    text_lower = text.lower()
    return [skill for skill in TECH_SKILLS if skill in text_lower]
