#!/usr/bin/env python3
import os
import sqlite3
import logging
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config import DATABASE_FILE  # Adjust the path if necessary
from utils.logging import setup_logging

logger = setup_logging()

def load_resume_text(resume_path):
    """
    Load the resume text from a file.
    """
    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.exception("Error loading resume text: %s", e)
        raise

def compute_finbert_similarity(resume_text, job_texts, model_name="yiyanghkust/finbert-tone"):
    """
    Compute cosine similarity scores between the resume and job texts using FinBERT.
    Returns a 1D numpy array of similarity scores.
    
    Note: FinBERT is primarily designed for sentiment analysis. When used for embeddings,
    performance might differ compared to models optimized for sentence embeddings.
    """
    model = SentenceTransformer(model_name)
    # Encode returns numpy arrays
    resume_embedding = model.encode([resume_text])   # shape: (1, embedding_dim)
    job_embeddings = model.encode(job_texts)           # shape: (num_jobs, embedding_dim)

    # Compute cosine similarities (resume vs. each job)
    similarities = cosine_similarity(resume_embedding, job_embeddings)
    # Flatten from shape (1, num_jobs) to (num_jobs,)
    return similarities.flatten()

def add_finbert_column_if_needed(conn):
    """
    Add a new column 'similarity_score_fbert' to the jobs table if it does not exist.
    SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so we try and catch the error.
    """
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN similarity_score_fbert REAL")
        conn.commit()
        logger.info("Added column similarity_score_fbert to jobs table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logger.info("Column similarity_score_fbert already exists.")
        else:
            logger.error("Error adding new column: %s", e)
            raise

def update_finbert_similarity(db_file, resume_path):
    """
    Retrieves all job descriptions from the jobs table, computes similarity scores
    with FinBERT, and updates each record with the FinBERT-based similarity score.
    """
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()

        # Ensure the new column exists.
        add_finbert_column_if_needed(conn)

        # Retrieve job_id and description from the jobs table.
        cur.execute("SELECT job_id, description FROM jobs")
        jobs = cur.fetchall()
        if not jobs:
            logger.info("No jobs found in database to update.")
            return

        job_ids = [job_id for job_id, _ in jobs]
        job_descriptions = [desc for _, desc in jobs]

        # Load and preprocess the resume text.
        resume_text = load_resume_text(resume_path)

        # Compute FinBERT similarity scores.
        scores = compute_finbert_similarity(resume_text, job_descriptions)
        logger.info("Computed FinBERT similarity scores for %d jobs.", len(scores))

        # Update each job record with the FinBERT similarity score.
        for job_id, score in zip(job_ids, scores):
            float_score = float(score)  # Ensure it's a plain Python float
            logger.debug("Updating job_id=%s with FinBERT similarity=%f (type=%s)",
                         job_id, float_score, type(float_score))
            cur.execute("UPDATE jobs SET similarity_score_fbert = ? WHERE job_id = ?",
                        (float_score, job_id))
        conn.commit()
        logger.info("Updated FinBERT similarity scores for %d jobs.", len(job_ids))
    except Exception as e:
        logger.exception("Error updating FinBERT similarity scores: %s", e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Adjust the path to your resume if necessary.
    resume_path = os.path.join(os.getcwd(), "resume.txt")
    update_finbert_similarity(DATABASE_FILE, resume_path)
