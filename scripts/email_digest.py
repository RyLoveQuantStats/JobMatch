#!/usr/bin/env python3
import sqlite3
import logging
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# SendGrid API configuration
SENDGRID_API_KEY = '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'
EMAIL_SENDER = 'rylo5252@colorado.edu'    
EMAIL_RECIPIENT = 'jobscrape@yahoo.com'

# ---------------------------
# Configuration Settings
# ---------------------------
# Database file location
DB_FILE = 'data.db'

# Logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# ---------------------------
# Database Utility Functions
# ---------------------------
def ensure_emailed_date_column(db_file):
    """
    Ensure that the jobs table has an 'emailed_date' column.
    If the column already exists, this function will catch the error.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE jobs ADD COLUMN emailed_date TEXT")
        conn.commit()
        logging.info("Added 'emailed_date' column to jobs table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            logging.info("'emailed_date' column already exists.")
        else:
            logging.error("Error altering jobs table: %s", e)
    finally:
        conn.close()

def get_top_unemailed_jobs(db_file, limit=10):
    """
    Retrieve the top 'limit' unemailed jobs sorted by the SBERT similarity score.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    query = """
        SELECT job_id, title, company, location, description, similarity_score_sbert
        FROM jobs
        WHERE emailed_date IS NULL
        ORDER BY similarity_score_sbert DESC
        LIMIT ?
    """
    cur.execute(query, (limit,))
    jobs = cur.fetchall()
    conn.close()
    return jobs

def mark_jobs_as_emailed(db_file, job_ids):
    """
    Update the 'emailed_date' for the given job IDs to mark them as emailed.
    """
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    now = datetime.now().isoformat()
    for job_id in job_ids:
        cur.execute("UPDATE jobs SET emailed_date = ? WHERE job_id = ?", (now, job_id))
    conn.commit()
    conn.close()
    logging.info("Marked %d jobs as emailed.", len(job_ids))

# ---------------------------
# Email Functions using SendGrid
# ---------------------------
def compose_email_body(jobs):
    """
    Build an HTML email body that contains a table listing each job's details.
    """
    html = "<html><body>"
    html += "<h2>Top 10 New Jobs for Today</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += ("<tr><th>Job ID</th><th>Title</th><th>Company</th>"
             "<th>Location</th><th>Similarity Score</th><th>Description</th></tr>")
    for job in jobs:
        job_id, title, company, location, description, similarity = job
        snippet = (description[:200] + '...') if description and len(description) > 200 else description
        html += f"<tr><td>{job_id}</td><td>{title}</td><td>{company}</td>"
        html += f"<td>{location}</td><td>{similarity:.4f}</td><td>{snippet}</td></tr>"
    html += "</table>"
    html += "</body></html>"
    return html

def send_email_sendgrid(subject, body, sender, recipient, api_key):
    """
    Send an email with the given subject and HTML body using SendGrid.
    """
    message = Mail(
        from_email=sender,
        to_emails=recipient,
        subject=subject,
        html_content=body
    )
    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        logging.info("Email sent successfully. Status Code: %s", response.status_code)
    except Exception as e:
        logging.error("Error sending email with SendGrid: %s", e)
        raise

# ---------------------------
# Main Process
# ---------------------------
def main():
    logging.info("Starting daily email digest process.")
    
    # Ensure the database has the necessary column to track emailed jobs.
    ensure_emailed_date_column(DB_FILE)
    
    # Query the top 10 unemailed jobs based on SBERT similarity scores.
    jobs = get_top_unemailed_jobs(DB_FILE, limit=10)
    if not jobs:
        logging.info("No new jobs to email today.")
        return
    
    # Compose the email content.
    email_body = compose_email_body(jobs)
    subject = "Daily Job Digest: Top 10 New Jobs"
    
    # Send the email via SendGrid.
    send_email_sendgrid(subject, email_body, EMAIL_SENDER, EMAIL_RECIPIENT, SENDGRID_API_KEY)
    
    # Mark the emailed jobs so they won't be emailed again.
    job_ids = [job[0] for job in jobs]
    mark_jobs_as_emailed(DB_FILE, job_ids)
    
    logging.info("Daily email digest process completed.")

if __name__ == '__main__':
    main()
