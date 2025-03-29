#!/usr/bin/env python3
import logging
import sqlite3

from config import DATABASE_FILE
from scripts.job_scrape import main as scrape_jobs_main
from scripts.resume_parser import parse_resume_and_match
from utils.logging import setup_logging

# Set up logging.
logger = setup_logging()

def update_similarity_scores(resume_path, db_file):
    """
    Retrieves all job descriptions from the database, computes similarity
    scores against the resume, and updates each job record with the similarity score.
    """
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        # Retrieve job_id and description for all jobs.
        cur.execute("SELECT job_id, description FROM jobs")
        jobs = cur.fetchall()
        if not jobs:
            logger.info("No job entries found to update similarity scores.")
            return

        # Separate job IDs and descriptions.
        job_ids = [job_id for job_id, _ in jobs]
        job_texts = [desc for _, desc in jobs]

        # Compute similarity scores using the resume_parser module.
        similarity_scores = parse_resume_and_match(resume_path, job_texts)
        logger.info("Computed similarity scores for %d jobs.", len(similarity_scores))

        # Update each job record with the corresponding similarity score.
        for job_id, score in zip(job_ids, similarity_scores):
            cur.execute("UPDATE jobs SET similarity_score = ? WHERE job_id = ?", (score, job_id))
        conn.commit()
        logger.info("Updated similarity scores for %d jobs.", len(job_ids))
    except sqlite3.Error as e:
        logger.error("Error updating similarity scores: %s", e)
    finally:
        if conn:
            conn.close()

def main():
    logger.info("Starting the full job scraping and resume matching pipeline...")
    
    # Step 1: Run the job scraping module (inserts jobs into the database).
    scrape_jobs_main()
    
    # Step 2: Run resume parsing & keyword matching.
    # Adjust the resume_path to the correct path to your resume file.
    resume_path = "resume.txt"
    update_similarity_scores(resume_path, DATABASE_FILE)
    
    logger.info("Pipeline complete.")

if __name__ == "__main__":
    main()
