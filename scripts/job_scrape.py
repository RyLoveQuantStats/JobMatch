#!/usr/bin/env python3
import os
import time
import requests
import sqlite3
import logging

from config import JSEARCH_API, DATABASE_FILE
from utils.logging import setup_logging

logger = setup_logging()

# -------------------
# JSearch API Configuration
# -------------------
API_HOST = "jsearch.p.rapidapi.com"
BASE_URL = "https://jsearch.p.rapidapi.com"
HEADERS = {
    "x-rapidapi-key": JSEARCH_API,
    "x-rapidapi-host": API_HOST
}

# -------------------
# Retry Configuration
# -------------------
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds

# -------------------
# Database Schema: Jobs Table (extended)
# -------------------
JOBS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    jsearch_job_id TEXT UNIQUE,   -- Unique job ID from JSearch
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT,
    ticker TEXT,
    posted_date TEXT,
    scraped_date TEXT DEFAULT (datetime('now')),
    similarity_score REAL,
    similarity_score_sbert REAL,
    details TEXT,               -- JSON from /job-details
    estimated_salary TEXT,      -- JSON from /estimated-salary
    company_salary TEXT         -- JSON from /company-job-salary
);
"""

def initialize_jobs_table(db_file):
    """
    Create the jobs table if it does not exist.
    """
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(JOBS_TABLE_SQL)
        conn.commit()
        logger.info("Jobs table created or already exists.")
    except sqlite3.Error as e:
        logger.error("Error creating jobs table: %s", e)
    finally:
        if conn:
            conn.close()

# -------------------
# General API Call Function
# -------------------
def call_api(endpoint, params):
    """
    Makes an API call with retry logic.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(BASE_URL + endpoint, headers=HEADERS, params=params)
            if response.status_code == 429:
                logger.warning("Rate limit hit on %s. Waiting for %s seconds...", endpoint, RETRY_DELAY)
                time.sleep(RETRY_DELAY)
                continue
            elif response.status_code != 200:
                logger.error("Error: Received status code %s for endpoint %s with params: %s", 
                             response.status_code, endpoint, params)
                return None
            return response
        except Exception as e:
            logger.exception("Exception during API call to %s: %s", endpoint, e)
            time.sleep(RETRY_DELAY)
    return None

# -------------------
# Endpoint-Specific Functions
# -------------------
def search_jobs(query, location="us", page=1, num_pages=10):
    """
    Calls the /search endpoint to search for jobs.
    Returns a list of job objects.
    num_pages=10 returns roughly 100 jobs (10 per page).
    """
    endpoint = "/search"
    params = {
        "query": query,
        "location": location,
        "page": page,
        "num_pages": num_pages
    }
    response = call_api(endpoint, params)
    if response:
        try:
            json_response = response.json()
            if json_response.get("status") != "OK":
                logger.error("API error in /search for query '%s': %s", query, json_response.get("error"))
                return []
            return json_response.get("data", [])
        except Exception as e:
            logger.exception("Error parsing JSON from /search for query '%s': %s", query, e)
    return []

def get_job_details(job_id):
    """
    Calls the /job-details endpoint for a given job_id.
    Returns a dictionary with job details.
    """
    endpoint = "/job-details"
    params = {"job_id": job_id}
    response = call_api(endpoint, params)
    if response:
        try:
            json_response = response.json()
            if json_response.get("status") != "OK":
                logger.error("API error in /job-details: %s", json_response.get("error"))
                return {}
            return json_response.get("data", {})
        except Exception as e:
            logger.exception("Error parsing JSON from /job-details: %s", e)
    return {}

def get_estimated_salary(job_title, location="us"):
    """
    Calls the /estimated-salary endpoint for a given job title and location.
    Returns a dictionary with salary info.
    """
    endpoint = "/estimated-salary"
    params = {
        "job_title": job_title,
        "location": location
    }
    response = call_api(endpoint, params)
    if response:
        try:
            json_response = response.json()
            if json_response.get("status") != "OK":
                logger.error("API error in /estimated-salary: %s", json_response.get("error"))
                return {}
            return json_response.get("data", {})
        except Exception as e:
            logger.exception("Error parsing JSON from /estimated-salary: %s", e)
    return {}

def get_company_job_salary(job_title, company, location="us"):
    """
    Calls the /company-job-salary endpoint for a given job title and company (and optional location).
    Returns a dictionary with company salary info.
    """
    endpoint = "/company-job-salary"
    params = {
        "job_title": job_title,
        "company": company,
        "location": location
    }
    response = call_api(endpoint, params)
    if response:
        try:
            json_response = response.json()
            if json_response.get("status") != "OK":
                logger.error("API error in /company-job-salary: %s", json_response.get("error"))
                return {}
            return json_response.get("data", {})
        except Exception as e:
            logger.exception("Error parsing JSON from /company-job-salary: %s", e)
    return {}

# -------------------
# Database Insertion / Update Helpers
# -------------------
def insert_job(conn, job):
    """
    Insert a job (from /search endpoint) into the jobs table.
    """
    try:
        cur = conn.cursor()
        title = job.get("job_title", "N/A")
        company = job.get("employer_name", "N/A")
        city = job.get("job_city", "")
        country = job.get("job_country", "")
        location_str = f"{city}, {country}" if city or country else "Location not provided"
        description = job.get("job_description", "N/A")
        ticker = job.get("ticker", None)
        posted_date = job.get("posted_date", None)
        jsearch_job_id = job.get("job_id")
        cur.execute("""
            INSERT OR IGNORE INTO jobs (jsearch_job_id, title, company, location, description, ticker, posted_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (jsearch_job_id, title, company, location_str, description, ticker, posted_date))
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Error inserting job: %s", e)

def update_job_with_details(conn, jsearch_job_id, details, estimated_salary, company_salary):
    """
    Update the job record with additional data from /job-details, /estimated-salary, and /company-job-salary endpoints.
    """
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE jobs 
            SET details = ?, estimated_salary = ?, company_salary = ?
            WHERE jsearch_job_id = ?
        """, (str(details), str(estimated_salary), str(company_salary), jsearch_job_id))
        conn.commit()
    except sqlite3.Error as e:
        logger.error("Error updating job with details: %s", e)

# -------------------
# Main Function
# -------------------
def main():
    logger.info("Starting job scraping using multiple JSearch queries...")

    # Initialize the jobs table.
    initialize_jobs_table(DATABASE_FILE)
    
    # Define a list of search queries for broader finance jobs.
    search_queries = [
        "quantitative trading"

        '''
        "quantitative researcher", "quantitative developer", "trading analyst",
        "trading operations", "trading associate", "finance",
        "portfolio management", "investment banking", "financial analyst", "CPA",
        "financial advisor", "financial consultant", "financial planner",
        "financial analyst", "risk management", "financial modeling",
        "financial reporting", "financial controller", "financial operations",
        "financial services", "investment analyst", "investment associate",
        "investment consultant", "investment manager", "investment advisor",
        "investment banking analyst", "investment banking associate", "CFA", "CQF"
        '''
        # Add more queries as needed...
    ]
    
    # Open a database connection.
    conn = sqlite3.connect(DATABASE_FILE)
    
    # Loop through each query, call the API, and insert the jobs.
    for query in search_queries:
        logger.info("Searching jobs with query: '%s'", query)
        jobs = search_jobs(query, num_pages=10)  # 10 pages * ~10 jobs per page = ~100 jobs per query.
        logger.info("Found %s jobs for query '%s'.", len(jobs), query)
        for job in jobs:
            insert_job(conn, job)
        # Optional: add a delay between queries to avoid rate limiting.
        time.sleep(2)
    
    # Now update each job record with additional details.
    cur = conn.cursor()
    cur.execute("SELECT jsearch_job_id, job_description, job_title, employer_name FROM jobs")
    jobs_info = cur.fetchall()
    logger.info("Updating details for %d jobs.", len(jobs_info))
    for jsearch_job_id, description, job_title, employer_name in jobs_info:
        # Only call salary endpoints if we have a non-empty job_title.
        if job_title and job_title.strip():
            details_data = get_job_details(jsearch_job_id)
            estimated_salary_data = get_estimated_salary(job_title)
            company_salary_data = get_company_job_salary(job_title, employer_name if employer_name else "")
        else:
            details_data = get_job_details(jsearch_job_id)
            estimated_salary_data = {}
            company_salary_data = {}
        update_job_with_details(conn, jsearch_job_id, details_data, estimated_salary_data, company_salary_data)

        
        conn.close()
    logger.info("Job scraping and endpoint extraction complete.")

if __name__ == "__main__":
    main()
