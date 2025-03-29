import os
import re
import sqlite3
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

def load_resume(resume_path):
    """
    Load the resume text from a file.
    If your resume is a PDF, consider using a PDF parser (e.g., PyPDF2) to extract the text.
    """
    with open(resume_path, 'r', encoding='utf-8') as f:
        return f.read()

def preprocess_text(text):
    """
    Preprocess text by lowercasing and removing non-alphanumeric characters.
    You can expand this function to include more sophisticated preprocessing.
    """
    text = text.lower()
    # Remove punctuation and non-word characters
    text = re.sub(r'[\W_]+', ' ', text)
    return text

def build_tfidf_vectors(resume_text, job_texts):
    """
    Create TF-IDF vectors for the resume and a list of job descriptions.
    Returns the resume vector, job vectors, and the fitted vectorizer.
    """
    documents = [resume_text] + job_texts
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(documents)
    resume_vector = tfidf_matrix[0]
    job_vectors = tfidf_matrix[1:]
    return resume_vector, job_vectors, vectorizer

def compute_similarity(resume_vector, job_vectors):
    """
    Compute cosine similarity between the resume vector and each job vector.
    Returns a list of similarity scores.
    """
    similarities = cosine_similarity(resume_vector, job_vectors)
    return similarities.flatten()

def parse_resume_and_match(resume_path, job_texts):
    """
    High-level function that loads and preprocesses the resume,
    builds TF-IDF vectors for both the resume and the job texts,
    and computes similarity scores.
    
    Parameters:
      resume_path (str): Path to the resume file.
      job_texts (List[str]): List of job description texts.
    
    Returns:
      List[float]: Similarity scores for each job description.
    """
    # Load and preprocess resume
    resume_text = load_resume(resume_path)
    resume_text = preprocess_text(resume_text)
    
    # Preprocess each job description
    processed_jobs = [preprocess_text(job) for job in job_texts]
    
    # Build TF-IDF vectors and compute similarity scores
    resume_vector, job_vectors, _ = build_tfidf_vectors(resume_text, processed_jobs)
    similarity_scores = compute_similarity(resume_vector, job_vectors)
    return similarity_scores

def update_tfidf_similarity(resume_path, db_file):
    """
    Update the TF-IDF similarity scores for job descriptions stored in the database.
    
    This function retrieves all job descriptions from the database, computes
    similarity scores against the resume, and updates the database with these scores.
    
    Parameters:
      resume_path (str): Path to the resume file.
      db_file (str): Path to the SQLite database file.
    """
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute("SELECT job_id, description FROM jobs")
        jobs = cur.fetchall()
        if not jobs:
            logger.info("No job entries found to update TF-IDF scores.")
            return
        job_ids = [job_id for job_id, _ in jobs]
        job_texts = [desc for _, desc in jobs]
        similarity_scores = parse_resume_and_match(resume_path, job_texts)
        logger.info("Computed TF-IDF similarity scores for %d jobs.", len(similarity_scores))
        for job_id, score in zip(job_ids, similarity_scores):
            cur.execute("UPDATE jobs SET similarity_score = ? WHERE job_id = ?", (score, job_id))
        conn.commit()
        logger.info("Updated TF-IDF similarity scores for %d jobs.", len(job_ids))
    except Exception as e:
        logger.error("Error updating TF-IDF similarity scores: %s", e)
    finally:
        if conn:
            conn.close()

# For testing purposes, you can run this module directly.
if __name__ == '__main__':
    # Assume you have a plain text resume file named 'resume.txt' in your project root.
    resume_file = os.path.join(os.getcwd(), 'resume.txt')
    # Sample job descriptions (in reality, these would come from your job scraping pipeline)
    sample_jobs = [
        "Looking for a quantitative analyst with strong mathematical background and programming skills in Python.",
        "Software engineer required with expertise in web development and JavaScript frameworks.",
        "Financial analyst needed for portfolio management, trading strategies, and investment analysis."
    ]
    scores = parse_resume_and_match(resume_file, sample_jobs)
    for idx, score in enumerate(scores, start=1):
        print(f"Job {idx} similarity score: {score:.4f}")
