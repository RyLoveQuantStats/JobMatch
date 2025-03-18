-- schema.sql

-- Table for storing job postings
CREATE TABLE IF NOT EXISTS jobs (
    job_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT,
    ticker TEXT,
    posted_date TEXT,  -- Can store ISO date strings (YYYY-MM-DD)
    scraped_date TEXT DEFAULT (datetime('now')),  -- Defaults to current timestamp
    similarity_score REAL  -- Optional score for resume-job matching
);

-- Table for storing company details (from YFinance classification)
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    ticker TEXT UNIQUE,
    sector TEXT,
    industry TEXT
);
