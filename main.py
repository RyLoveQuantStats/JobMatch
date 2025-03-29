#!/usr/bin/env python3
import os
import logging
from config import DATABASE_FILE
from utils.logging import setup_logging

# Import the modules (each script is self-contained)
from scripts.job_scrape import main as scrape_jobs_main
from scripts.tfidf_parser import parse_resume_and_match
from scripts.sbert_parser import update_sbert_similarity

# Set up logging.
logger = setup_logging()

def update_tfidf_similarity(resume_path, db_file):
    """
    Retrieves all job descriptions from the jobs table, computes TF-IDF similarity
    scores using the resume, and updates each job record with the similarity score.
    """
    import sqlite3
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        # Retrieve job_id and description for all jobs.
        cur.execute("SELECT job_id, description FROM jobs")
        jobs = cur.fetchall()
        if not jobs:
            logger.info("No job entries found to update TF-IDF similarity scores.")
            return

        # Separate job IDs and descriptions.
        job_ids = [job_id for job_id, _ in jobs]
        job_texts = [desc for _, desc in jobs]

        # Compute similarity scores using the TF-IDF parser.
        similarity_scores = parse_resume_and_match(resume_path, job_texts)
        logger.info("Computed TF-IDF similarity scores for %d jobs.", len(similarity_scores))

        # Update each job record with the TF-IDF similarity score.
        for job_id, score in zip(job_ids, similarity_scores):
            cur.execute("UPDATE jobs SET similarity_score = ? WHERE job_id = ?", (score, job_id))
        conn.commit()
        logger.info("Updated TF-IDF similarity scores for %d jobs.", len(job_ids))
    except Exception as e:
        logger.error("Error updating TF-IDF similarity scores: %s", e)
    finally:
        if conn:
            conn.close()

def main():
    logger.info("Starting the full job scraping and resume matching pipeline...")

    # STEP 1: Job Scraping
    logger.info("Running job scraping module...")
    scrape_jobs_main()  # This module scrapes jobs and stores them in the database.

    # STEP 2: Resume Matching via TF-IDF & SBERT
    # Set the resume file path.
    resume_path = os.path.join(os.getcwd(), "resume.txt")
    
    # Update TF-IDF similarity scores.
    logger.info("Updating TF-IDF similarity scores...")
    update_tfidf_similarity(resume_path, DATABASE_FILE)
    
    # Update SBERT similarity scores.
    logger.info("Updating SBERT similarity scores...")
    update_sbert_similarity(DATABASE_FILE, resume_path)
    
    # (Optional Future Steps)
    # e.g., sector classification using YFinance, historical tracking, ARIMA forecasting, Streamlit dashboard.
    logger.info("Pipeline complete.")

if __name__ == "__main__":
    main()
