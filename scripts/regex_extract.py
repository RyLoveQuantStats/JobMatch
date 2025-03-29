#!/usr/bin/env python3
import re
import sqlite3
import logging
from config import DATABASE_FILE
from utils.logging import setup_logging

logger = setup_logging()

# Bonus weights
SALARY_BONUS = 0.1
COLORADO_BONUS = 0.15
EDUCATION_BONUS = 0.1

### Regex patterns:

SALARY_PATTERN = r"(?i)(?:salary|compensation|pay)[^\$]{0,20}\$\s*(\d{1,3}(?:,\d{3})+|\d{1,3})(?:\s*[kK])?" # Searches for a salary component in the job description
LOCATION_PATTERN = r"(?i)\b(?:Colorado|Colo\.|CO|Co\.|Denver|Den\.?|Boulder|Bld\.?)\b" # Searches for if Colorado, Denver or Boulder is mentioned in the job description
EDUCATION_PATTERN = r"\b(?:Master(?:'s)?\s+Degree|Master(?:'s)?\s+of\s+(?:Science\s+in\s+Finance|Finance)|MSF|MSc(?:\s+Finance)?)\b" # Searches for if a Master of Science in Finance is mentioned in the job description

def extract_salary(text):
    match = re.search(SALARY_PATTERN, text)
    if match:
        try:
            # Convert the captured salary figure to an integer.
            salary = int(match.group(1).replace(",", ""))
            return salary
        except ValueError:
            return None
    return None

def check_colorado(text):
    return bool(re.search(LOCATION_PATTERN, text, flags=re.IGNORECASE))

def check_education(text):
    return bool(re.search(EDUCATION_PATTERN, text, flags=re.IGNORECASE))

def load_jobs(db_file):
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    # Fetch job_id, title, description, precomputed semantic similarity score, and location
    cur.execute("SELECT job_id, title, description, similarity_score_sbert, location FROM jobs")
    jobs = cur.fetchall()
    conn.close()
    return jobs

def add_final_score_column(db_file):
    """
    Adds a new column 'final_similarity_score' to the jobs table if it does not exist.
    SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we catch the error if the column exists.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN final_similarity_score REAL")
        conn.commit()
        logger.info("Column 'final_similarity_score' added to jobs table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("Column 'final_similarity_score' already exists.")
        else:
            logger.error("Error adding column 'final_similarity_score': %s", e)
    finally:
        conn.close()

def compute_final_score(job):
    """
    For a given job tuple, compute the final ranking score based on:
    - The base semantic similarity score.
    - A bonus for salary if above 80K.
    - A bonus if the job is in Colorado.
    - A bonus if the education requirement includes 'Master of Science in Finance'.
    """
    job_id, title, description, base_score, db_location = job
    if base_score is None:
        base_score = 0.0

    text = f"{title or ''} {description or ''} {db_location or ''}"
    bonus = 0.0
    salary = extract_salary(text)
    if salary and salary >= 80000:
        bonus += SALARY_BONUS
        logger.debug("Job %s: Salary bonus added (salary: %s)", job_id, salary)
    if check_colorado(text):
        bonus += COLORADO_BONUS
        logger.debug("Job %s: Colorado bonus added", job_id)
    if check_education(text):
        bonus += EDUCATION_BONUS
        logger.debug("Job %s: Education bonus added", job_id)
    final_score = base_score + bonus
    return job_id, final_score

def update_final_scores_in_db(db_file, scored_jobs):
    """
    Update the final_similarity_score column in the jobs table for each job.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    for job_id, final_score in scored_jobs:
        cur.execute("UPDATE jobs SET final_similarity_score = ? WHERE job_id = ?", (final_score, job_id))
    conn.commit()
    conn.close()
    logger.info("Final similarity scores updated in the database.")

def count_regex_matches(text):
    """
    Count and return the number of matches for salary, Colorado, and education patterns in the provided text.
    """
    salary_matches = re.findall(SALARY_PATTERN, text, flags=re.IGNORECASE)
    colorado_matches = re.findall(LOCATION_PATTERN, text, flags=re.IGNORECASE)
    education_matches = re.findall(EDUCATION_PATTERN, text, flags=re.IGNORECASE)
    return len(salary_matches), len(colorado_matches), len(education_matches)

def query_and_analyze(db_file):
    """
    Query the database for jobs and log how many times each regex pattern matched per job,
    along with aggregate counts.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT job_id, title, description, location, final_similarity_score FROM jobs")
    jobs = cur.fetchall()
    conn.close()

    total_salary = 0
    total_colorado = 0
    total_education = 0
    job_count = 0

    for job in jobs:
        job_id, title, description, location, final_score = job
        text = f"{title or ''} {description or ''} {location or ''}"
        salary_count, colorado_count, education_count = count_regex_matches(text)
        total_salary += salary_count
        total_colorado += colorado_count
        total_education += education_count
        job_count += 1
        logger.info("Job ID: %s | Salary Matches: %d | Colorado Matches: %d | Education Matches: %d | Final Score: %s",
                    job_id, salary_count, colorado_count, education_count, final_score)
    
    logger.info("Processed %d jobs.", job_count)
    logger.info("Aggregate counts: Salary Matches: %d, Colorado Matches: %d, Education Matches: %d",
                total_salary, total_colorado, total_education)

def main():
    logger.info("Starting combined ranking and regex analysis pipeline...")
    
    # Ensure the final_similarity_score column exists.
    add_final_score_column(DATABASE_FILE)
    
    # Load jobs from the database.
    jobs = load_jobs(DATABASE_FILE)
    if not jobs:
        logger.error("No jobs found in the database.")
        return
    
    # Compute final scores for each job.
    scored_jobs = []
    for job in jobs:
        job_id, final_score = compute_final_score(job)
        scored_jobs.append((job_id, final_score))
    
    # Update the database with the final scores.
    update_final_scores_in_db(DATABASE_FILE, scored_jobs)
    
    # Sort jobs by final score (highest first) and log top 10 results.
    scored_jobs.sort(key=lambda x: x[1], reverse=True)
    logger.info("Top 10 ranked jobs based on final similarity score:")
    for job_id, score in scored_jobs[:10]:
        logger.info("Job ID: %s, Final Score: %.4f", job_id, score)
    
    # Query the database and perform regex analysis.
    query_and_analyze(DATABASE_FILE)

if __name__ == "__main__":
    main()