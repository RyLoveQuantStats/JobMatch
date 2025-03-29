#!/usr/bin/env python3
import os
from config import DATABASE_FILE
from scripts.job_scrape import main as scrape_jobs_main
from scripts.tfidf_parser import update_tfidf_similarity
from scripts.sbert_parser import update_sbert_similarity
from scripts.analyze_parsers import run_analysis

def run_pipeline():
    # Step 1: Scrape job postings and save to database
    # Uncomment the following line to scrape jobs but only do this when necessary as all jobs are stored in the database that have been pulled previously
    '''scrape_jobs_main()'''

    # Step 2: Update similarity scores using resume.txt
    resume_path = os.path.join(os.getcwd(), "resume.txt")
    update_tfidf_similarity(resume_path, DATABASE_FILE)
    update_sbert_similarity(DATABASE_FILE, resume_path)

    # Step 3: Run analysis/validation on the updated job data
    run_analysis()

if __name__ == "__main__":
    run_pipeline()
