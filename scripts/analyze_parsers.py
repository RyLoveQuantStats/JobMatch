#!/usr/bin/env python3
import os
import re
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import nltk
nltk.download('punkt', quiet=True)
from nltk.tokenize import word_tokenize

from config import DATABASE_FILE
from utils.logging import setup_logging

logger = setup_logging()

# ---------------------
# TABLE CREATION FOR PARSER RESULTS
# ---------------------
PARSER_RESULTS_SQL = """
CREATE TABLE IF NOT EXISTS parser_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    parser_type TEXT,         -- 'TF-IDF' or 'SBERT'
    keyword TEXT,
    ranking INTEGER,          -- 1 to 10
    score REAL,
    overall_similarity REAL,  -- overall similarity score for the job
    analysis_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

def create_parser_results_table(db_file):
    """Create the parser_results table if it does not exist."""
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(PARSER_RESULTS_SQL)
        conn.commit()
        logger.info("Table 'parser_results' created or already exists.")
    except sqlite3.Error as e:
        logger.error("Error creating parser_results table: %s", e)
    finally:
        conn.close()

def save_parser_results(db_file, job_id, parser_type, overall_similarity, results):
    """
    Save parser analysis results into the parser_results table.
    'results' is a list of tuples (keyword, score), sorted by ranking.
    Convert the score to float to ensure it's stored as a numeric value.
    """
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        for ranking, (keyword, score) in enumerate(results, start=1):
            float_score = float(score)  # Make sure we store a numeric float
            query = """
                INSERT INTO parser_results (job_id, parser_type, keyword, ranking, score, overall_similarity)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            cur.execute(query, (job_id, parser_type, keyword, ranking, float_score, overall_similarity))
        conn.commit()
        logger.info("Saved %d %s parser results for job_id %s.", len(results), parser_type, job_id)
    except sqlite3.Error as e:
        logger.error("Error saving parser results: %s", e)
    finally:
        conn.close()

# ---------------------
# Data Loading and Preprocessing
# ---------------------
def load_job_data(db_file):
    """Load job data (including similarity scores) into a DataFrame."""
    conn = sqlite3.connect(db_file)
    try:
        query = """
            SELECT job_id, title, company, description, similarity_score, similarity_score_sbert
            FROM jobs
        """
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        logger.error("Error loading job data: %s", e)
        return pd.DataFrame()
    finally:
        conn.close()

def preprocess(text):
    """Simple text preprocessing."""
    text = text.lower()
    return re.sub(r'[\W_]+', ' ', text)

# ---------------------
# TF-IDF Analysis
# ---------------------
def compute_tfidf_details(resume_text, job_text):
    """
    Compute TF‑IDF vectors for two texts and return the cosine similarity
    and top 10 unique keyword contributions.
    """
    docs = [preprocess(resume_text), preprocess(job_text)]
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf = vectorizer.fit_transform(docs)
    resume_vec = tfidf[0].toarray().flatten()
    job_vec = tfidf[1].toarray().flatten()
    similarity = cosine_similarity(tfidf[0], tfidf[1])[0, 0]
    contributions = resume_vec * job_vec
    features = vectorizer.get_feature_names_out()
    sorted_idx = np.argsort(contributions)[::-1]
    # Collect unique keywords (they will be unique since features are unique)
    top_keywords = [(features[i], contributions[i]) for i in sorted_idx if contributions[i] > 0][:10]
    return similarity, top_keywords

# ---------------------
# SBERT Analysis (Unique Tokens)
# ---------------------
def analyze_sbert_contributions(resume_text, job_text, model_name="all-MiniLM-L6-v2"):
    """
    Approximate SBERT interpretability by tokenizing the resume,
    encoding each token with SBERT, and computing the cosine similarity
    between each token and the job description embedding.
    Returns the top 10 unique tokens (lowercase) with highest similarity scores.
    """
    tokens = word_tokenize(resume_text)
    tokens = [t.lower() for t in tokens if len(t) > 1]
    model = SentenceTransformer(model_name)
    job_embedding = model.encode([job_text])[0]
    token_embeddings = model.encode(tokens)
    similarities = cosine_similarity(token_embeddings, [job_embedding]).flatten()
    unique_tokens = {}
    for token, sim in zip(tokens, similarities):
        # Keep highest similarity for each unique token
        if token in unique_tokens:
            if sim > unique_tokens[token]:
                unique_tokens[token] = sim
        else:
            unique_tokens[token] = sim
    sorted_tokens = sorted(unique_tokens.items(), key=lambda x: x[1], reverse=True)
    return sorted_tokens[:10]

# ---------------------
# Visualization Functions
# ---------------------
def plot_histograms(df):
    """Generate histograms for the TF-IDF and SBERT similarity scores."""
    print("Basic Statistics:")
    print(df[['similarity_score', 'similarity_score_sbert']].describe())

    plt.figure(figsize=(12,5))
    plt.subplot(1,2,1)
    sns.histplot(df['similarity_score'].dropna(), kde=True, color='blue')
    plt.title("TF‑IDF Score Distribution")
    plt.xlabel("TF‑IDF Score")

    plt.subplot(1,2,2)
    sns.histplot(df['similarity_score_sbert'].dropna(), kde=True, color='green')
    plt.title("SBERT Score Distribution")
    plt.xlabel("SBERT Score")
    plt.tight_layout()
    plt.savefig("output/similarity_histograms.png")
    plt.show()

# ---------------------
# Baseline Calculation
# ---------------------
def compute_baselines(df):
    """Compute recommended baseline thresholds (75th percentile) for both models."""
    tfidf_base = np.percentile(df['similarity_score'].dropna(), 75)
    sbert_base = np.percentile(df['similarity_score_sbert'].dropna(), 75)
    print("\nRecommended Baseline Thresholds:")
    print(f" - TF‑IDF: {tfidf_base:.4f}")
    print(f" - SBERT:  {sbert_base:.4f}")
    return tfidf_base, sbert_base

# ---------------------
# Bar Chart of Top 10 Words from Each Model
# ---------------------
def plot_top10_keywords(tfidf_keywords, sbert_tokens):
    """
    Show all top 10 words from TF-IDF and top 10 tokens from SBERT in a single bar chart.
    We'll do an outer merge on the 'word' to compare their scores side by side.
    """
    df_tfidf = pd.DataFrame(tfidf_keywords, columns=['word', 'tfidf_score'])
    df_sbert = pd.DataFrame(sbert_tokens, columns=['word', 'sbert_score'])

    # Merge outer on 'word'
    df_merge = pd.merge(df_tfidf, df_sbert, on='word', how='outer')
    df_merge.set_index('word', inplace=True)

    # Sort by highest TF-IDF or SBERT (just for a consistent display)
    df_merge.sort_values(by=['tfidf_score','sbert_score'], ascending=False, inplace=True, na_position='last')

    # Plot as bar chart
    df_merge.plot(kind='bar', figsize=(10,6))
    plt.title("Top 10 TF‑IDF vs SBERT Keywords")
    plt.ylabel("Score")
    plt.tight_layout()
    plt.savefig("output/top10_keywords_barchart.png")
    plt.show()

# ---------------------
# Deep Dive Analysis and Saving Results
# ---------------------
def deep_dive(df, resume_path):
    """Perform deep dive analysis on the top matching job for each model."""
    with open(resume_path, 'r', encoding='utf-8') as f:
        resume_text = f.read()
    
    # Deep dive for TF-IDF
    top_tfidf = df.sort_values("similarity_score", ascending=False).iloc[0]
    print("\n--- Deep Dive: Top TF‑IDF Matching Job ---")
    print(f"Job ID: {top_tfidf['job_id']}, Title: {top_tfidf['title']}, Company: {top_tfidf['company']}")
    print("Description (first 500 chars):")
    print(top_tfidf['description'][:500] + "...")
    tfidf_sim, tfidf_keywords = compute_tfidf_details(resume_text, top_tfidf['description'])
    print(f"Recomputed TF‑IDF Cosine Similarity: {tfidf_sim:.4f}")
    print("Top contributing keywords (TF‑IDF):")
    for word, contrib in tfidf_keywords:
        print(f"  {word}: {contrib:.4f}")
    
    # Save TF-IDF results into database.
    save_parser_results(DATABASE_FILE, top_tfidf['job_id'], "TF-IDF", tfidf_sim, tfidf_keywords)
    
    # Deep dive for SBERT
    top_sbert = df.sort_values("similarity_score_sbert", ascending=False).iloc[0]
    print("\n--- Deep Dive: Top SBERT Matching Job ---")
    print(f"Job ID: {top_sbert['job_id']}, Title: {top_sbert['title']}, Company: {top_sbert['company']}")
    print("Description (first 500 chars):")
    print(top_sbert['description'][:500] + "...")
    sbert_tokens = analyze_sbert_contributions(resume_text, top_sbert['description'])
    print("Top contributing tokens from resume (SBERT, unique):")
    for token, score in sbert_tokens:
        print(f"  {token}: {score:.4f}")
    
    # Save SBERT results into database.
    overall_sbert = top_sbert['similarity_score_sbert']
    save_parser_results(DATABASE_FILE, top_sbert['job_id'], "SBERT", overall_sbert, sbert_tokens)

    # Plot bar chart with all top 10 keywords from both methods
    plot_top10_keywords(tfidf_keywords, sbert_tokens)

def deep_dive_and_save(df, resume_path):
    """Wrapper for deep dive analysis that also saves parser results."""
    deep_dive(df, resume_path)

# ---------------------
# Validation Function
# ---------------------
def run_validation():
    """Run full validation, deep dive analysis, and baseline calculation."""
    df = load_job_data(DATABASE_FILE)
    if df.empty:
        logger.error("No job data found for validation.")
        return
    resume_path = os.path.join(os.getcwd(), "resume.txt")

    # Plot only histograms (scatter plot removed)
    plot_histograms(df)

    # Perform deep dive and save results
    deep_dive_and_save(df, resume_path)

    # Compute baseline thresholds
    compute_baselines(df)

    logger.info("Validation complete.")

def run_analysis():
    create_parser_results_table(DATABASE_FILE)
    run_validation()

if __name__ == "__main__":
    run_analysis()
