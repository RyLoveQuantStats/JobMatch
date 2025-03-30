#!/usr/bin/env python3
import re
import sqlite3
import logging
import urllib.parse
import ast

# -------------------
# Configuration
# -------------------
DATABASE_FILE = "data.db"  # Path to your SQLite database

# Regex patterns for extraction
SALARY_PATTERN = r"(?i)(?:salary|compensation|pay)[^\$]{0,20}\$\s*(\d{1,3}(?:,\d{3})+|\d{1,3})(\s*[kK])?"
LOCATION_PATTERN = r"(?i)\b((?:Colorado|Colo\.|CO|Co\.|Denver|Den\.?|Boulder|Bld\.?))\b"
EDUCATION_PATTERN = r"(?i)\b(Master(?:'s)?\s+Degree|Master(?:'s)?\s+of\s+(?:Science\s+in\s+Finance|Finance)|MSF|MSc(?:\s+Finance)?)\b"

# For posted date extraction:
# Pattern to capture the UTC datetime value.
DATETIME_UTC_PATTERN = r"'job_posted_at_datetime_utc':\s*'([^']+)'"
# Pattern to capture the days-ago value.
DAYS_AGO_PATTERN = r"'job_posted_at':\s*'([^']+)'"

# -------------------
# Logging Setup
# -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -------------------
# Schema Update Helpers
# -------------------
def add_column(conn, column_name, column_def):
    """
    Adds a column to the jobs table if it does not exist.
    """
    try:
        cur = conn.cursor()
        cur.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_def}")
        conn.commit()
        logger.info("Added column '%s' to jobs table.", column_name)
    except sqlite3.Error as e:
        if "duplicate column name" in str(e).lower():
            logger.info("Column '%s' already exists.", column_name)
        else:
            logger.error("Error adding column '%s': %s", column_name, e)

def ensure_columns(conn):
    """
    Ensures that all necessary columns exist in the jobs table.
    """
    add_column(conn, "job_apply_link_extracted", "TEXT")
    add_column(conn, "company_website", "TEXT")
    add_column(conn, "estimated_salary", "TEXT")
    add_column(conn, "location_pattern", "TEXT")
    add_column(conn, "education_pattern", "TEXT")
    add_column(conn, "posted_date", "TEXT")  # UTC datetime
    add_column(conn, "days_ago", "TEXT")       # e.g., "2 days ago"

# -------------------
# Extraction Functions
# -------------------
def extract_field_from_text(text, pattern):
    """
    Applies the regex pattern on the given text.
    If the pattern is SALARY_PATTERN, converts the salary to an integer.
    Returns the first matched group or "{}" if nothing is found.
    """
    try:
        # Attempt safe evaluation in case the text is a literal list/dict.
        data = ast.literal_eval(text)
        if isinstance(data, list) and data:
            text = str(data)
    except Exception:
        pass

    match = re.search(pattern, text)
    if match:
        if pattern == SALARY_PATTERN:
            try:
                salary_str = match.group(1).replace(",", "")
                salary = int(salary_str)
                if match.group(2) and match.group(2).strip().lower() == "k":
                    salary *= 1000
                return str(salary)
            except Exception:
                return "{}"
        return match.group(1)  # Return captured group
    return "{}"

def extract_from_both(details, description, pattern):
    """
    Combines details and description and applies the regex pattern.
    Returns the first match found or "{}" if none.
    """
    combined = " ".join(filter(None, [details, description])).strip()
    if not combined:
        return "{}"
    return extract_field_from_text(combined, pattern)

def extract_apply_link(text, company):
    """
    Extracts a job apply link from the given text.
    Tries literal evaluation, then specific and generic regex methods.
    If not found and company is provided, returns a Google search URL.
    """
    try:
        data = ast.literal_eval(text)
        if isinstance(data, list) and data:
            link = data[0].get("job_apply_link", "")
            if link:
                logger.info("Extracted job_apply_link via literal_eval.")
                return link
    except Exception:
        pass

    regex_specific = r"'job_apply_link':\s*'([^']+)'"
    match = re.search(regex_specific, text)
    if match:
        logger.info("Extracted job_apply_link via specific regex.")
        return match.group(1)

    regex_generic = r"(https?://[^\s']+)"
    matches = re.findall(regex_generic, text)
    if matches:
        logger.info("Extracted a generic URL for apply link: %s", matches[0])
        return matches[0]

    if company:
        query = urllib.parse.quote(f"{company} careers")
        fallback = f"https://www.google.com/search?q={query}"
        logger.info("No apply link found; using fallback URL: %s", fallback)
        return fallback
    return "{}"

def extract_apply_link_from_both(details, description, company):
    """
    Attempts to extract the job apply link from details first, then description.
    """
    combined = " ".join(filter(None, [details, description])).strip()
    if not combined:
        return "{}"
    return extract_apply_link(combined, company)

def extract_company_website(text, company):
    """
    Extracts the employer website from the given text.
    Tries literal evaluation then specific and generic regex methods.
    If not found and company is provided, returns a fallback Google search URL.
    """
    try:
        data = ast.literal_eval(text)
        if isinstance(data, list) and data:
            website = data[0].get("employer_website", "")
            if website:
                logger.info("Extracted employer_website via literal_eval.")
                return website
    except Exception:
        pass

    regex_specific = r"'employer_website':\s*'([^']+)'"
    match = re.search(regex_specific, text)
    if match:
        logger.info("Extracted employer_website via specific regex.")
        return match.group(1)

    regex_generic = r"(https?://[^\s']+)"
    matches = re.findall(regex_generic, text)
    if matches:
        logger.info("Extracted a generic URL for employer website: %s", matches[0])
        return matches[0]

    if company:
        query = urllib.parse.quote(f"{company} official website")
        fallback = f"https://www.google.com/search?q={query}"
        logger.info("No employer website found; using fallback URL: %s", fallback)
        return fallback
    return "{}"

def extract_company_website_from_both(details, description, company):
    """
    Attempts to extract the company website from details first, then description.
    """
    combined = " ".join(filter(None, [details, description])).strip()
    if not combined:
        return "{}"
    return extract_company_website(combined, company)

def extract_salary_value(details, description):
    """
    Extracts a salary value from the combined details and description text.
    """
    return extract_from_both(details, description, SALARY_PATTERN)

def extract_location(details, description):
    """
    Extracts a location pattern from the combined text.
    """
    return extract_from_both(details, description, LOCATION_PATTERN)

def extract_education(details, description):
    """
    Extracts an education pattern from the combined text.
    """
    return extract_from_both(details, description, EDUCATION_PATTERN)

def extract_posted_date(details, description):
    """
    Extracts the posted date (UTC datetime) from the combined details and description.
    
    1. Attempts to safely evaluate the text as a Python literal. If the structure is a list 
       with a dictionary, returns the value for 'job_posted_at_datetime_utc'.
    2. If that fails, applies a regex to extract the value for 'job_posted_at_datetime_utc'.
    """
    combined = " ".join(filter(None, [details, description])).strip()
    if not combined:
        return "{}"
    
    try:
        data = ast.literal_eval(combined)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            utc_val = data[0].get("job_posted_at_datetime_utc", None)
            if utc_val:
                logger.info("Extracted posted_date via literal_eval using job_posted_at_datetime_utc.")
                return utc_val
    except Exception:
        pass
    
    match = re.search(DATETIME_UTC_PATTERN, combined)
    if match:
        logger.info("Extracted posted_date via regex using job_posted_at_datetime_utc.")
        return match.group(1)
    
    return "{}"

def extract_days_ago(details, description):
    """
    Extracts the days-ago value from the combined details and description using regex.
    Looks for the pattern 'job_posted_at': '...'
    """
    combined = " ".join(filter(None, [details, description])).strip()
    if not combined:
        return "{}"
    
    match = re.search(DAYS_AGO_PATTERN, combined)
    if match:
        logger.info("Extracted days_ago via regex using job_posted_at.")
        return match.group(1)
    
    return "{}"

# -------------------
# Database Update Helper
# -------------------
def update_field(conn, job_id, column, value):
    """
    Updates a given column for the job identified by job_id with the provided value.
    """
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE jobs SET {column} = ? WHERE job_id = ?", (value, job_id))
        conn.commit()
        logger.info("Updated job %s: %s = %s", job_id, column, value)
    except sqlite3.Error as e:
        logger.error("Error updating job %s for column %s: %s", job_id, column, e)

# -------------------
# Main Function
# -------------------
def main():
    logger.info("Starting extraction on job records...")
    conn = sqlite3.connect(DATABASE_FILE)
    
    # Ensure the jobs table has all necessary columns.
    ensure_columns(conn)
    
    cur = conn.cursor()
    # Assumes the table has the columns: job_id, company, details, and description.
    cur.execute("SELECT job_id, company, details, description FROM jobs")
    rows = cur.fetchall()
    logger.info("Found %d job records to process.", len(rows))
    
    for job_id, company, details, description in rows:
        if not (details or description):
            logger.warning("No details or description for job %s", job_id)
            continue
        
        # Extract all fields.
        apply_link = extract_apply_link_from_both(details, description, company)
        website = extract_company_website_from_both(details, description, company)
        salary = extract_salary_value(details, description)
        location_val = extract_location(details, description)
        education_val = extract_education(details, description)
        posted_date = extract_posted_date(details, description)
        days_ago = extract_days_ago(details, description)
        
        # Update the record with all extracted data.
        update_field(conn, job_id, "job_apply_link_extracted", apply_link)
        update_field(conn, job_id, "company_website", website)
        update_field(conn, job_id, "estimated_salary", salary)
        update_field(conn, job_id, "location_pattern", location_val)
        update_field(conn, job_id, "education_pattern", education_val)
        update_field(conn, job_id, "posted_date", posted_date)
        update_field(conn, job_id, "days_ago", days_ago)
    
    conn.close()
    logger.info("Field extraction complete.")

if __name__ == "__main__":
    main()
